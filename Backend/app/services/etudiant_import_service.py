"""
Service d'import massif d'etudiants.

Principes :

- **Deux temps.** ``analyse`` ne fait aucune ecriture metier ; ``valider``
  n'ecrit que les lignes reussies a l'analyse.  L'admin voit toujours le
  rapport avant de valider, et peut annuler apres coup.
- **Aucune invention.** Une filiere, une session, une classe ou un niveau
  inconnu produit une erreur de ligne.  Le module ne cree aucun referentiel.
- **Idempotence.** Un lot ne peut etre valide qu'une fois.  Rejouer la meme
  validation ne duplique rien.
- **Transaction.** ``valider`` n'effectue aucun commit implicite : il
  s'execute dans la transaction de l'endpoint appelant, comme les autres
  services metier du projet.
"""

import csv
import io
import re
import unicodedata
import uuid
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from sqlalchemy import Date, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Classe, Niveau
from app.models.etudiant import Etudiant
from app.models.etudiant_import import (
    ACTION_CREER,
    ACTION_MAJ,
    ACTION_RIEN,
    LIGNE_ERREUR,
    LIGNE_IGNORE,
    LIGNE_IMPORTEE,
    LIGNE_MISE_A_JOUR,
    LIGNE_VALIDE,
    STATUT_ANALYSE,
    STATUT_ANNULE,
    STATUT_ERREUR,
    STATUT_TERMINE,
    STATUT_VALIDE,
    EtudiantImportBatch,
    EtudiantImportRow,
)
from app.models.session_academique import SessionAcademique
from app.models.structure import Filiere
from app.services.academic_service import class_projections, sync_active_inscription

# ---------------------------------------------------------------------------
# Contrat de colonnes
# ---------------------------------------------------------------------------
#: En-tetes acceptes, vers le champ metier. Les en-tetes sont normalises
#: (minuscules, sans accent, ``_``) avant comparaison, ce qui rend le fichier
#: tolerant aux libelles francais comme anglais.
COLUMN_ALIASES: Dict[str, str] = {
    "nom": "nom",
    "nom_de_famille": "nom",
    "nom_famille": "nom",
    "lastname": "nom",
    "last_name": "nom",
    "prenom": "prenom",
    "prenoms": "prenom",
    "firstname": "prenom",
    "first_name": "prenom",
    "matricule": "matricule",
    "code_etudiant": "matricule",
    "code": "matricule",
    "sexe": "sexe",
    "genre": "sexe",
    "date_de_naissance": "date_naissance",
    "date_naissance": "date_naissance",
    "naissance": "date_naissance",
    "birthdate": "date_naissance",
    "email": "email",
    "e_mail": "email",
    "mail": "email",
    "courriel": "email",
    "telephone": "telephone",
    "tel": "telephone",
    "phone": "telephone",
    "portable": "telephone",
    "adresse": "adresse",
    "address": "adresse",
    "filiere": "filiere",
    "filiere_nom": "filiere",
    "intitule_filiere": "filiere",
    "filiere_code": "filiere_code",
    "code_filiere": "filiere_code",
    "niveau": "niveau",
    "niveau_code": "niveau",
    "niveau_nom": "niveau",
    "classe": "classe",
    "classe_code": "classe",
    "code_classe": "classe",
    "session": "session",
    "session_code": "session",
    "code_session": "session",
    "annee_academique": "session",
    "statut": "statut",
    "date_inscription": "date_inscription",
    "date_d_inscription": "date_inscription",
    "inscription_le": "date_inscription",
}

#: Champs obligatoires pour qu'une ligne soit importable.
CHAMPS_OBLIGATOIRES = ("nom", "prenom")

#: Longueur maximale d'un fichier analyse. Au-dela, l'admin doit passer par un
#: nettoyage prealable : on refuse plutot que de bloquer la requete.
TAILLE_MAX_OCTETS = 8 * 1024 * 1024
LIGNES_MAX = 5000

SEPARATEURS_CSV = (",", ";", "\t")

DATE_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%m-%y",
)

#: Valeurs acceptees pour la colonne ``sexe``, normalisees.
SEXES = {
    "m": "M",
    "h": "M",
    "homme": "M",
    "masculin": "M",
    "male": "M",
    "f": "F",
    "femme": "F",
    "feminin": "F",
    "female": "F",
}


class ImportFormatInvalide(ValueError):
    """Le fichier envoye n'est pas exploitable (format, encodage, en-tetes)."""


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def normalize_header(value: Any) -> str:
    """Normalise un en-tete : minuscules, sans accent, separateurs en ``_``."""

    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_cell(value: Any) -> str:
    """Nettoie une valeur de cellule ; ``None`` devient la chaine vide."""

    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_date(value: Any) -> Tuple[Optional[date], bool]:
    """Parse une date. Retourne ``(date, ok)`` sans jamais lever d'exception."""

    if isinstance(value, datetime):
        return value.date(), True
    if isinstance(value, date):
        return value, True
    text = normalize_cell(value)
    if not text:
        return None, True
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(text, pattern).date(), True
        except ValueError:
            continue
    return None, False


def normalize_sexe(value: Any) -> Tuple[Optional[str], bool]:
    """Normalise le sexe ; retourne ``(valeur, ok)``."""

    text = normalize_cell(value).lower()
    if not text:
        return None, True
    if text in SEXES:
        return SEXES[text], True
    return text[:10], False


def normalize_email(value: Any) -> Tuple[Optional[str], bool]:
    """Valide une adresse email de façon volontairement simple et stricte."""

    text = normalize_cell(value).lower()
    if not text:
        return None, True
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]{2,}", text):
        return text, True
    return None, False


# ---------------------------------------------------------------------------
# Lecture du fichier
# ---------------------------------------------------------------------------
def _decode_csv(raw: bytes) -> str:
    """Decode un CSV en tolérant BOM et les accents."""

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportFormatInvalide(
        "Encodage du fichier non reconnu. Enregistrez le CSV en UTF-8."
    )


def _read_csv(raw: bytes) -> Tuple[List[str], List[List[str]], str]:
    text = _decode_csv(raw)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(SEPARATEURS_CSV))
    except csv.Error:
        dialect = csv.excel  # virgule par défaut
        if ";" in sample and "," not in sample:
            dialect = csv.excel
            dialect.delimiter = ";"
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [row for row in reader]
    if not rows:
        raise ImportFormatInvalide("Le fichier est vide.")
    return rows[0], rows[1:], dialect.delimiter


def _read_xlsx(raw: bytes) -> Tuple[List[str], List[List[str]], str]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - dependance optionnelle
        raise ImportFormatInvalide(
            "La lecture des fichiers .xlsx nécessite la dépendance openpyxl. "
            "Enregistrez le fichier au format CSV (UTF-8) pour continuer."
        ) from exc

    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        sheet = workbook[workbook.sheetnames[0]]
        rows = [[cell for cell in row] for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()
    if not rows:
        raise ImportFormatInvalide("La première feuille du classeur est vide.")
    header = [normalize_cell(value) for value in rows[0]]
    body = [[normalize_cell(value) for value in row] for row in rows[1:]]
    return header, body, "xlsx"


def read_table(filename: str, raw: bytes) -> Tuple[List[str], List[List[str]], str, str]:
    """Lit un CSV ou un XLSX. Retourne ``(en-tetes, lignes, format, separateur)``."""

    if len(raw) > TAILLE_MAX_OCTETS:
        raise ImportFormatInvalide(
            "Fichier trop volumineux pour l'analyse en ligne "
            f"(maximum {TAILLE_MAX_OCTETS // (1024 * 1024)} Mo). "
            "Découpez le fichier par promotions."
        )
    extension = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if extension in ("xlsx", "xlsm"):
        header, body, separator = _read_xlsx(raw)
        return header, body, "xlsx", separator
    if extension == "csv" or not extension:
        header, body, separator = _read_csv(raw)
        return header, body, "csv", separator
    raise ImportFormatInvalide(
        "Format non pris en charge. Utilisez un fichier .csv (UTF-8) ou .xlsx."
    )


# ---------------------------------------------------------------------------
# Resolution des referentiels
# ---------------------------------------------------------------------------
class Referentiels:
    """Index de resolution des referentiels, charges en une fois par lot."""

    def __init__(self) -> None:
        self.filieres_par_code: Dict[str, Filiere] = {}
        self.filieres_par_nom: Dict[str, Filiere] = {}
        self.sessions_par_code: Dict[str, SessionAcademique] = {}
        self.sessions_par_nom: Dict[str, SessionAcademique] = {}
        self.classes_par_code: Dict[str, Classe] = {}
        self.niveaux_par_code: Dict[str, Niveau] = {}

    def filiere(self, *, nom: str = "", code: str = "") -> Optional[Filiere]:
        if code:
            found = self.filieres_par_code.get(code.upper())
            if found:
                return found
        if nom:
            return self.filieres_par_nom.get(nom.lower())
        return None

    def session(self, *, nom: str = "", code: str = "") -> Optional[SessionAcademique]:
        if code:
            found = self.sessions_par_code.get(code.upper())
            if found:
                return found
        if nom:
            return self.sessions_par_nom.get(nom.lower())
        return None

    def classe(self, value: str) -> Optional[Classe]:
        return self.classes_par_code.get(value.upper())

    def niveau(self, code: str) -> Optional[Niveau]:
        return self.niveaux_par_code.get(code.upper())


async def load_referentiels(db: AsyncSession) -> Referentiels:
    """Charge les referentiels de resolution. Aucune creation."""

    refs = Referentiels()

    for filiere in (await db.execute(select(Filiere))).scalars().all():
        refs.filieres_par_code[(filiere.code or "").upper()] = filiere
        refs.filieres_par_nom[(filiere.nom or "").strip().lower()] = filiere

    for session in (await db.execute(select(SessionAcademique))).scalars().all():
        refs.sessions_par_code[(session.code or "").upper()] = session
        refs.sessions_par_nom[(session.nom or "").strip().lower()] = session

    for classe in (await db.execute(select(Classe))).scalars().all():
        refs.classes_par_code[(classe.code or "").upper()] = classe

    for niveau in (await db.execute(select(Niveau))).scalars().all():
        refs.niveaux_par_code[(niveau.code or "").upper()] = niveau

    return refs


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------
def _map_columns(header: Sequence[str]) -> Tuple[Dict[int, str], List[str], List[str]]:
    """Associe chaque index de colonne a un champ metier.

    Retourne ``(mapping, colonnes_reconnues, colonnes_ignorees)``.
    """

    mapping: Dict[int, str] = {}
    reconnues: List[str] = []
    ignorees: List[str] = []
    for index, raw in enumerate(header):
        key = normalize_header(raw)
        if not key:
            continue
        target = COLUMN_ALIASES.get(key)
        if target is None:
            if raw.strip():
                ignorees.append(raw.strip())
            continue
        # ``filiere`` explicite prime sur ``filiere_code`` et ``classe``.
        if target in mapping.values() and target in ("filiere", "session", "niveau", "classe"):
            continue
        mapping[index] = target
        reconnues.append(f"{raw.strip()} → {target}")
    return mapping, reconnues, ignorees


def _row_values(cells: Sequence[str], mapping: Dict[int, str]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for index, target in mapping.items():
        if index < len(cells):
            values[target] = normalize_cell(cells[index])
    return values


async def _existing_identities(
    db: AsyncSession, keys: Sequence[Tuple[str, str, str]]
) -> Dict[str, Etudiant]:
    """Charge les etudiants existants par matricule, email ou identite."""

    result: Dict[str, Etudiant] = {}
    matricules = {k[0] for k in keys if k[0]}
    emails = {k[1] for k in keys if k[1]}
    if matricules:
        for etudiant in (
            await db.execute(select(Etudiant).where(Etudiant.matricule.in_(sorted(matricules))))
        ).scalars().all():
            result[f"m:{etudiant.matricule}"] = etudiant
    if emails:
        for etudiant in (
            await db.execute(select(Etudiant).where(Etudiant.email.in_(sorted(emails))))
        ).scalars().all():
            result[f"e:{etudiant.email}"] = etudiant

    # Identite : nom + prenom + date de naissance. On borne la requete aux
    # noms et prenoms presents dans le fichier : jamais un chargement complet.
    triplets = [k[2] for k in keys if k[2] and k[2] != "||"]
    if triplets:
        noms = {t.split("|")[0] for t in triplets if t.split("|")[0]}
        prenoms = {t.split("|")[1] for t in triplets if t.split("|")[1]}
        for etudiant in (
            await db.execute(
                select(Etudiant).where(
                    Etudiant.nom.in_(sorted(noms)),
                    Etudiant.prenom.in_(sorted(prenoms)),
                )
            )
        ).scalars().all():
            cle = (
                f"{etudiant.nom.strip().lower()}|{etudiant.prenom.strip().lower()}|"
                f"{etudiant.date_naissance.isoformat() if etudiant.date_naissance else ''}"
            )
            result[f"i:{cle}"] = etudiant
    return result


async def analyse(
    db: AsyncSession,
    *,
    filename: str,
    raw: bytes,
    mode: str = "creation",
    created_by_id: Optional[int] = None,
) -> Tuple[EtudiantImportBatch, List[EtudiantImportRow]]:
    """Analyse un fichier et persiste son rapport, sans ecrire de donnee metier."""

    header, body, fmt, _separator = read_table(filename, raw)
    mapping, reconnues, ignorees = _map_columns(header)

    if not mapping:
        raise ImportFormatInvalide(
            "Aucune colonne reconnue. Vérifiez que le fichier contient au moins "
            "les colonnes « nom » et « prénom »."
        )
    missing_fields = [f for f in CHAMPS_OBLIGATOIRES if f not in mapping.values()]
    if missing_fields:
        raise ImportFormatInvalide(
            "Colonnes obligatoires absentes du fichier : "
            + ", ".join(f"« {field} »" for field in missing_fields)
            + "."
        )

    if len(body) > LIGNES_MAX:
        raise ImportFormatInvalide(
            f"Fichier trop volumineux : {len(body)} lignes pour un maximum de {LIGNES_MAX}."
        )

    batch = EtudiantImportBatch(
        id=str(uuid.uuid4()),
        nom_fichier=filename[:255],
        format_source=fmt,
        statut=STATUT_ANALYSE,
        mode=mode,
        nb_lignes=len(body),
        colonnes={
            "reconnues": reconnues,
            "ignorees": ignorees,
        },
        cree_par_id=created_by_id,
    )
    db.add(batch)
    await db.flush()

    refs = await load_referentiels(db)

    # Pre-chargement des identites existantes, en deux requetes seulement.
    raw_rows: List[Tuple[int, Dict[str, str], Dict[str, str]]] = []
    lookup_keys: List[Tuple[str, str, str]] = []
    for offset, cells in enumerate(body):
        line_no = offset + 1
        values = _row_values(cells, mapping)
        raw_rows.append((line_no, values, {str(i): normalize_cell(c) for i, c in enumerate(cells)}))
        lookup_keys.append(
            (
                values.get("matricule", "").upper(),
                values.get("email", "").lower(),
                f"{(values.get('nom','') or '').strip().lower()}|{(values.get('prenom','') or '').strip().lower()}|{values.get('date_naissance','')}",
            )
        )
    existing = await _existing_identities(db, lookup_keys)

    rows: List[EtudiantImportRow] = []
    counts = {"creer": 0, "maj": 0, "erreurs": 0, "avertissements": 0, "ignorees": 0}
    seen_in_file: Dict[str, int] = {}

    for (line_no, values, brut), (matricule_key, email_key, identity_key) in zip(
        raw_rows, lookup_keys
    ):
        erreurs: List[str] = []
        avertissements: List[str] = []
        resolues: Dict[str, Any] = {}
        statut = LIGNE_VALIDE
        action = ACTION_RIEN
        etudiant_existant: Optional[Etudiant] = None

        # -- Doublons a l'interieur du fichier -----------------------------
        for cle, libelle in (
            (f"m:{matricule_key}" if matricule_key else "", "matricule"),
            (f"e:{email_key}" if email_key else "", "email"),
            (f"i:{identity_key}" if values.get("nom") and values.get("prenom") else "", "identité"),
        ):
            if not cle:
                continue
            if cle in seen_in_file:
                erreurs.append(
                    f"Doublon dans le fichier : {libelle} déjà présent ligne {seen_in_file[cle]}."
                )
            else:
                seen_in_file[cle] = line_no

        # -- Champs obligatoires -------------------------------------------
        for champ in CHAMPS_OBLIGATOIRES:
            if not values.get(champ):
                erreurs.append(f"Colonne « {champ} » obligatoire et vide.")

        # -- Ligne entierement vide : ignore silencieuseux ---------------
        if not any(values.values()):
            rows.append(
                EtudiantImportRow(
                    batch_id=batch.id,
                    ligne=line_no,
                    statut=LIGNE_IGNORE,
                    action=ACTION_RIEN,
                    donnees={},
                    brut=brut,
                    erreurs=[],
                    avertissements=[],
                )
            )
            counts["ignorees"] += 1
            continue

        # -- Dates ----------------------------------------------------------
        for champ in ("date_naissance", "date_inscription"):
            if champ in values:
                parsed, ok = parse_date(values[champ])
                if not ok:
                    erreurs.append(
                        f"Date « {champ} » illisible : {values[champ]!r}. "
                        "Formats acceptés : JJ/MM/AAAA ou AAAA-MM-JJ."
                    )
                elif parsed is not None:
                    resolues[champ] = parsed.isoformat()

        # -- Sexe ------------------------------------------------------------
        if values.get("sexe"):
            sexe, ok = normalize_sexe(values["sexe"])
            if not ok:
                avertissements.append(
                    f"Valeur de sexe non standard : {values['sexe']!r} (conservée telle quelle)."
                )
            if sexe:
                resolues["sexe"] = sexe

        # -- Email -----------------------------------------------------------
        if values.get("email"):
            email, ok = normalize_email(values["email"])
            if not ok:
                erreurs.append(f"Adresse email invalide : {values['email']!r}.")
            else:
                resolues["email"] = email

        # -- Filiere ---------------------------------------------------------
        filiere = refs.filiere(nom=values.get("filiere", ""), code=values.get("filiere_code", ""))
        if filiere is not None:
            resolues["filiere_id"] = filiere.id
            resolues["filiere"] = filiere.nom
        elif values.get("filiere") or values.get("filiere_code"):
            libelle = values.get("filiere_code") or values.get("filiere")
            erreurs.append(
                f"Filière inconnue : « {libelle} ». Créez-la au préalable "
                "(Cycles, Niveaux & Classes ou Filières) puis relancez l'analyse."
            )

        # -- Niveau ------------------------------------------------------------
        if values.get("niveau"):
            niveau = refs.niveau(values["niveau"])
            if niveau is not None:
                resolues["niveau"] = niveau.nom or niveau.code
            else:
                resolues["niveau"] = values["niveau"]
                avertissements.append(
                    f"Niveau « {values['niveau']} » absent du référentiel : conservé tel quel."
                )

        # -- Session -----------------------------------------------------------
        session = refs.session(nom=values.get("session", ""), code=values.get("session", ""))
        if session is not None:
            resolues["session_id"] = session.id
        elif values.get("session"):
            erreurs.append(
                f"Session inconnue : « {values['session']} ». Créez-la au préalable "
                "(Sessions Académiques) puis relancez l'analyse."
            )

        # -- Classe -------------------------------------------------------------
        if values.get("classe"):
            classe = refs.classe(values["classe"])
            if classe is None:
                erreurs.append(
                    f"Classe inconnue : « {values['classe']} ». Créez-la au préalable "
                    "(Cycles, Niveaux & Classes) puis relancez l'analyse."
                )
            elif session is None:
                erreurs.append(
                    "Une classe exige une session dans la même ligne "
                    "(colonne « session »)."
                )
            else:
                resolues["classe_id"] = classe.id
                projections = class_projections(classe)
                resolues["filiere_id"] = projections["filiere_id"]
                resolues["filiere"] = projections["filiere"]
                resolues["niveau"] = projections["niveau"]
                resolues["session_id"] = session.id

        # -- Champs simples ------------------------------------------------------
        for champ in ("nom", "prenom", "matricule", "telephone", "adresse"):
            if values.get(champ):
                resolues[champ] = values[champ]
        if values.get("statut"):
            resolues["statut"] = values["statut"]
        else:
            resolues["statut"] = "Inscrit"

        # -- Rapprochement avec l'existant ------------------------------------------
        if matricule_key and f"m:{matricule_key}" in existing:
            etudiant_existant = existing[f"m:{matricule_key}"]
        elif email_key and f"e:{email_key}" in existing:
            etudiant_existant = existing[f"e:{email_key}"]

        if etudiant_existant is not None:
            if mode == "mise_a_jour":
                action = ACTION_MAJ
                resolues["matricule"] = etudiant_existant.matricule
            else:
                action = ACTION_RIEN
                erreurs.append(
                    f"Un dossier existe déjà (matricule {etudiant_existant.matricule}). "
                    "Relancez l'analyse en mode « mise à jour » pour le mettre à jour, "
                    "ou retirez la ligne du fichier."
                )
        elif action == ACTION_RIEN and not erreurs:
            action = ACTION_CREER

        # -- Doublon probable non bloquant -----------------------------------------
        # Un dossier existant porte la meme identite, mais ni le meme matricule
        # ni le meme email : on avertit sans bloquer, l'import reste possible.
        if etudiant_existant is None and identity_key and identity_key != "||":
            if f"i:{identity_key}" in existing:
                jumeau = existing[f"i:{identity_key}"]
                avertissements.append(
                    f"Doublon probable : un dossier ({jumeau.matricule}) porte la meme "
                    "identite. Verifiez qu'il ne s'agit pas de la meme personne."
                )

        if erreurs:
            statut = LIGNE_ERREUR
            counts["erreurs"] += 1
        else:
            counts["avertissements"] += 1 if avertissements else 0
            if action == ACTION_CREER:
                counts["creer"] += 1
            elif action == ACTION_MAJ:
                counts["maj"] += 1

        rows.append(
            EtudiantImportRow(
                batch_id=batch.id,
                ligne=line_no,
                statut=statut,
                action=action,
                matricule=resolues.get("matricule"),
                donnees=resolues,
                brut=brut,
                erreurs=erreurs,
                avertissements=avertissements,
            )
        )

    batch.nb_creer = counts["creer"]
    batch.nb_mettre_a_jour = counts["maj"]
    batch.nb_erreurs = counts["erreurs"]
    batch.nb_avertissements = counts["avertissements"]
    batch.nb_ignorees = counts["ignorees"]
    for row in rows:
        db.add(row)
    await db.flush()
    return batch, rows


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _next_matricules(existing: Set[str], prefix: str, count: int, annee: int) -> List[str]:
    """Reserve ``count`` matricules consecutifs, sans lecture par ligne."""

    sequence = 1
    reserved: List[str] = []
    while len(reserved) < count:
        candidate = f"{annee}-{prefix}-{sequence:04d}"
        if candidate not in existing:
            reserved.append(candidate)
            existing.add(candidate)
        sequence += 1
    return reserved


def _derive_filiere_code(filiere: Optional[Filiere], texte: str) -> str:
    if filiere is not None and filiere.code:
        return filiere.code
    return "".join(word[0] for word in (texte or "").split() if word).upper()[:4]


async def valider(
    db: AsyncSession,
    batch: EtudiantImportBatch,
    rows: Iterable[EtudiantImportRow],
) -> Dict[str, Any]:
    """Ecrit les lignes valides du lot. Ne commit pas : l'endpoint le fait."""

    candidates = [row for row in rows if row.statut == LIGNE_VALIDE and row.action in (ACTION_CREER, ACTION_MAJ)]
    if not candidates:
        batch.statut = STATUT_TERMINE
        batch.nb_importes = 0
        return {"importes": 0, "mises_a_jour": 0, "resultats": []}

    annee = datetime.now().year
    refs = await load_referentiels(db)

    # 1. Regroupement par prefixe pour generer les matricules sans N requetes.
    groupes: Dict[str, List[EtudiantImportRow]] = {}
    filieres_cache: Dict[str, Optional[Filiere]] = {}
    for row in candidates:
        filiere_id = row.donnees.get("filiere_id")
        filiere = None
        if filiere_id:
            if filiere_id not in filieres_cache:
                filieres_cache[filiere_id] = await db.get(Filiere, filiere_id)
            filiere = filieres_cache[filiere_id]
        prefix = _derive_filiere_code(filiere, row.donnees.get("filiere", ""))
        row.donnees["_prefixe"] = prefix
        groupes.setdefault(prefix, []).append(row)

    # Une seule requete pour recuperer tous les matricules deja pris.
    prefixes = [p for p in groupes if p]
    if prefixes:
        stmt = select(Etudiant.matricule)
        conditions = [Etudiant.matricule.like(f"{annee}-{p}-%") for p in prefixes]
        stmt = stmt.where(or_(*conditions))
        deja_pris: Set[str] = {str(value) for value in (await db.execute(stmt)).scalars().all()}
    else:
        deja_pris = set()

    for prefix, lignes in groupes.items():
        if prefix:
            reserved = _next_matricules(deja_pris, prefix, len(lignes), annee)
            for row, matricule in zip(lignes, reserved):
                if not row.donnees.get("matricule"):
                    row.donnees["matricule"] = matricule
                    row.matricule = matricule

    resultats: List[Dict[str, Any]] = []
    importes = 0
    mises_a_jour = 0

    #: Colonnes ``Date`` de l'etudiant : stockees en ISO dans le JSON de la
    #: ligne, reconverties ici car SQLAlchemy attend des objets ``date``.
    colonnes_date = {
        column.name
        for column in Etudiant.__table__.columns
        if isinstance(column.type, Date)
    }

    for row in candidates:
        donnees = dict(row.donnees)
        for champ in colonnes_date & set(donnees):
            if isinstance(donnees[champ], str):
                converti, ok = parse_date(donnees[champ])
                donnees[champ] = converti if ok else None
        matricule = donnees.pop("matricule", None) or row.matricule
        filiere_id = donnees.pop("filiere_id", None)
        classe_id = donnees.pop("classe_id", None)
        session_id = donnees.pop("session_id", None)
        donnees.pop("_prefixe", None)

        try:
            if row.action == ACTION_MAJ and row.matricule:
                etudiant = await db.get(Etudiant, row.etudiant_id) if row.etudiant_id else None
                if etudiant is None:
                    stmt = select(Etudiant).where(Etudiant.matricule == row.matricule)
                    etudiant = (await db.execute(stmt)).scalar_one_or_none()
                if etudiant is None:
                    row.statut = LIGNE_ERREUR
                    row.erreurs = list(row.erreurs) + [
                        "Dossier introuvable au moment de la mise à jour."
                    ]
                    resultats.append(
                        {
                            "ligne": row.ligne,
                            "statut": row.statut,
                            "action": row.action,
                            "matricule": row.matricule,
                            "etudiant_id": None,
                            "erreurs": row.erreurs,
                        }
                    )
                    continue
                for champ, valeur in donnees.items():
                    if hasattr(etudiant, champ) and valeur is not None:
                        setattr(etudiant, champ, valeur)
                if filiere_id:
                    etudiant.filiere_id = filiere_id
                if classe_id:
                    etudiant.classe_id = classe_id
                if session_id:
                    etudiant.session_id = session_id
                row.etudiant_id = etudiant.id
                row.statut = LIGNE_MISE_A_JOUR
                row.matricule = etudiant.matricule
                mises_a_jour += 1
                resultats.append(
                    {
                        "ligne": row.ligne,
                        "statut": row.statut,
                        "action": row.action,
                        "matricule": etudiant.matricule,
                        "etudiant_id": etudiant.id,
                        "erreurs": [],
                    }
                )
                continue

            if not matricule:
                row.statut = LIGNE_ERREUR
                row.erreurs = list(row.erreurs) + [
                    "Matricule absent et filière inexistante : génération impossible."
                ]
                resultats.append(
                    {
                        "ligne": row.ligne,
                        "statut": row.statut,
                        "action": row.action,
                        "matricule": None,
                        "etudiant_id": None,
                        "erreurs": row.erreurs,
                    }
                )
                continue

            if filiere_id is None and not (donnees.get("filiere") or "").strip():
                row.statut = LIGNE_ERREUR
                row.erreurs = list(row.erreurs) + [
                    "Filière absente : impossible d'enregistrer le dossier."
                ]
                resultats.append(
                    {
                        "ligne": row.ligne,
                        "statut": row.statut,
                        "action": row.action,
                        "matricule": matricule,
                        "etudiant_id": None,
                        "erreurs": row.erreurs,
                    }
                )
                continue

            doublon = (
                await db.execute(select(Etudiant).where(Etudiant.matricule == matricule))
            ).scalar_one_or_none()
            if doublon is not None:
                row.statut = LIGNE_ERREUR
                row.erreurs = list(row.erreurs) + [
                    f"Un étudiant avec le matricule « {matricule} » existe déjà."
                ]
                resultats.append(
                    {
                        "ligne": row.ligne,
                        "statut": row.statut,
                        "action": row.action,
                        "matricule": matricule,
                        "etudiant_id": None,
                        "erreurs": row.erreurs,
                    }
                )
                continue

            valeurs = {
                champ: valeur
                for champ, valeur in donnees.items()
                if champ in Etudiant.__table__.columns and valeur is not None
            }
            # La date d'inscription est valorisee une seule fois : la valeur
            # du fichier si elle existe, sinon la date du jour.
            valeurs.setdefault("date_inscription", date.today())
            etudiant = Etudiant(
                id=str(uuid.uuid4()),
                matricule=matricule,
                **valeurs,
            )
            etudiant.filiere_id = filiere_id
            etudiant.classe_id = classe_id
            etudiant.session_id = session_id
            db.add(etudiant)
            await db.flush()

            if classe_id and session_id:
                await sync_active_inscription(
                    db,
                    etudiant_id=etudiant.id,
                    classe_id=classe_id,
                    session_id=session_id,
                    date_inscription=etudiant.date_inscription,
                )

            row.etudiant_id = etudiant.id
            row.statut = LIGNE_IMPORTEE
            row.matricule = etudiant.matricule
            importes += 1
            resultats.append(
                {
                    "ligne": row.ligne,
                    "statut": row.statut,
                    "action": row.action,
                    "matricule": etudiant.matricule,
                    "etudiant_id": etudiant.id,
                    "erreurs": [],
                }
            )
        except Exception as exc:  # pragma: no cover - filet de securite
            row.statut = LIGNE_ERREUR
            row.erreurs = list(row.erreurs) + [f"Échec de l'écriture : {exc}"]
            resultats.append(
                {
                    "ligne": row.ligne,
                    "statut": row.statut,
                    "action": row.action,
                    "matricule": matricule,
                    "etudiant_id": None,
                    "erreurs": row.erreurs,
                }
            )

    batch.statut = STATUT_TERMINE
    batch.nb_importes = importes
    batch.nb_erreurs = sum(1 for row in rows if row.statut == LIGNE_ERREUR)
    return {"importes": importes, "mises_a_jour": mises_a_jour, "resultats": resultats}


# ---------------------------------------------------------------------------
# Modele de fichier
# ---------------------------------------------------------------------------
#: En-tetes du fichier attendu, dans l'ordre recommande.
COLONNES_MODELE = (
    ("nom", "nom", True, "Nom de famille de l'étudiant.", ["KOUASSI", "TANOH"]),
    ("prenom", "prenom", True, "Prénom(s) de l'étudiant.", ["Adjoa", "Aya"]),
    ("matricule", "matricule", False, "Laisser vide pour générer automatiquement.", []),
    ("sexe", "sexe", False, "M, F, Homme, Femme, Masculin, Féminin.", ["F"]),
    ("date_naissance", "date_naissance", False, "JJ/MM/AAAA ou AAAA-MM-JJ.", ["14/07/2004"]),
    ("email", "email", False, "Adresse email unique si connue.", []),
    ("telephone", "telephone", False, "Numéro de téléphone.", []),
    ("adresse", "adresse", False, "Adresse postale.", []),
    ("filiere", "filiere", False, "Nom exact d'une filière existante.", []),
    ("filiere_code", "filiere_code", False, "Code de filière (prioritaire sur le nom).", []),
    ("niveau", "niveau", False, "Code de niveau (L1, L2, M1...) ou libellé.", ["L1"]),
    ("classe", "classe", False, "Code de classe existante. Exige une session.", []),
    ("session", "session", False, "Code ou nom exact d'une session existante.", []),
    ("statut", "statut", False, "Sauf indication, la valeur « Inscrit » est utilisée.", []),
    ("date_inscription", "date_inscription", False, "JJ/MM/AAAA ou AAAA-MM-JJ.", []),
)


def modele_colonnes() -> List[Dict[str, Any]]:
    """Documentation des colonnes, sans aucune donnee d'etudiant."""

    return [
        {
            "colonne": colonne,
            "champ": champ,
            "obligatoire": obligatoire,
            "description": description,
            "exemples": exemples,
        }
        for colonne, champ, obligatoire, description, exemples in COLONNES_MODELE
    ]


__all__ = [
    "CHAMPS_OBLIGATOIRES",
    "COLONNES_MODELE",
    "COLUMN_ALIASES",
    "ImportFormatInvalide",
    "LIGNES_MAX",
    "Referentiels",
    "TAILLE_MAX_OCTETS",
    "analyse",
    "load_referentiels",
    "modele_colonnes",
    "normalize_cell",
    "normalize_email",
    "normalize_header",
    "normalize_sexe",
    "parse_date",
    "read_table",
    "valider",
]
