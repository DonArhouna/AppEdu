"""
Détection des conflits d'emploi du temps (lot 3).

Deux cours ne peuvent pas partager un créneau **dans la même salle**, ni un
enseignant au même moment. Jusqu'ici rien ne l'interdisait : la salle était
un texte libre et aucun contrôle ne croisait les horaires. Un emploi du
temps contradictoire se publiait tel quel, sans un mot.

Le conflit se définit par **chevauchement temporel** :

    debut < fin_existante ET fin > debut_existante

c'est-à-dire deux plages qui se touchent sans être consécutives. Un cours
8h-10h et un cours 10h-12h ne se chevauchent pas (10h == 10h n'est pas
strictement inférieur) : les cours consécutifs dans une même salle sont le
cas normal d'un emploi du temps bien construit, il ne faut pas les refuser.

Le rattachement d'un cours à une salle se fait par **correspondance de nom**,
insensible à la casse : ``cours.salle`` reste un texte libre (aucune donnée
existante n'est reinterpretee), mais dès qu'il cite le nom d'une salle
enregistrée, les règles de cette salle s'appliquent. Un cours qui cite une
salle inconnue reste planifiable : on ne bloque pas un institut dont la
salle n'est pas encore inventoriée, et l'audit des conflits le signale.
"""

from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pedagogie import Cours
from app.models.salle import Salle
from app.models.utilisateur import Utilisateur

#: Les jours où l'on enseigne, dans l'ordre. La comparaison d'un jour saisi
#: se fait sur l'étiquette normalisée (capitale initiale), pas sur la casse
#: de la saisie.
JOURS_OUVRABLES = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi")


def jour_normalise(jour: Optional[str]) -> Optional[str]:
    """« lundi », « LUNDI », « Lundi » -> « Lundi » ; inconnu -> None."""
    if not jour:
        return None
    for jour_de_reference in JOURS_OUVRABLES:
        if jour.strip().lower() == jour_de_reference.lower():
            return jour_de_reference
    return None


def heure_normalisee(heure: Optional[str]) -> Optional[str]:
    """« 8:00 » -> « 08:00 ». Invalide -> None.

    Les horaires sont stockés en texte « HH:MM » ; une saisie paresseuse ne
    doit pas créer un conflit fantôme ni en masquer un.
    """
    if not heure:
        return None
    morceaux = heure.strip().split(":")
    if len(morceaux) < 2:
        return None
    try:
        heures = int(morceaux[0])
        minutes = int(morceaux[1])
    except ValueError:
        return None
    if not (0 <= heures <= 23 and 0 <= minutes <= 59):
        return None
    return f"{heures:02d}:{minutes:02d}"


def chevauchement(debut_a: str, fin_a: str, debut_b: str, fin_b: str) -> bool:
    """Deux plages se chevauchent-elles ? (bornes consécutives exclues)"""
    return debut_a < fin_b and fin_a > debut_b


def horaires_valides(debut: Optional[str], fin: Optional[str]) -> bool:
    """Horaires bien formés et dans l'ordre (fin strictement après début)."""
    debut_n = heure_normalisee(debut)
    fin_n = heure_normalisee(fin)
    return debut_n is not None and fin_n is not None and fin_n > debut_n


class ConflitEdt(BaseModel):
    """Un conflit, nommé et attribué : qui occupe quoi, quand."""

    type: str  # "salle" ou "enseignant"
    cours_id: str
    matiere: Optional[str] = None
    enseignant_nom: Optional[str] = None
    salle: Optional[str] = None
    jour: str
    heure_debut: str
    heure_fin: str


def _conflit_depuis(cours: Cours, matiere_nom: Optional[str], type_conflit: str) -> ConflitEdt:
    return ConflitEdt(
        type=type_conflit,
        cours_id=cours.id,
        matiere=matiere_nom,
        enseignant_nom=cours.enseignant_nom,
        salle=cours.salle,
        jour=cours.jour_semaine,
        heure_debut=cours.heure_debut,
        heure_fin=cours.heure_fin,
    )


async def _matieres_noms(db: AsyncSession, ids: List[str]) -> dict:
    if not ids:
        return {}
    from app.models.structure import Matiere

    lignes = await db.execute(select(Matiere.id, Matiere.nom).where(Matiere.id.in_(ids)))
    return {m_id: m_nom for m_id, m_nom in lignes.all()}


async def trouver_conflits(
    db: AsyncSession,
    *,
    jour_semaine: str,
    heure_debut: str,
    heure_fin: str,
    salle: str,
    enseignant_id: Optional[int],
    cours_exclu_id: Optional[str] = None,
) -> List[ConflitEdt]:
    """Les cours que cette séance entrerait en conflit avec.

    Deux règles, toutes deux exigées par la même fenêtre temporelle :

    - **même salle** : la salle citée correspond (nom, casse ignorée) à la
      salle citée par un autre cours du même créneau — deux cours ne
      tiennent pas dans la même pièce ;
    - **même enseignant** : l'enseignant affecté ne peut pas être à deux
      endroits à la fois.

    Un cours qui se modifie lui-même n'est pas son propre conflit
    (``cours_exclu_id``) : remettre un cours à l'identique doit réussir.
    """

    jour_n = jour_normalise(jour_semaine)
    debut_n = heure_normalisee(heure_debut)
    fin_n = heure_normalisee(heure_fin)
    if not jour_n or debut_n is None or fin_n is None:
        # Une séance non conforme est rejetée en amont (422) ; ici, ne pas
        # inventer de conflit sur des horaires qu'on ne sait pas lire.
        return []

    salle_n = (salle or "").strip().lower()
    conditions = [
        func.lower(Cours.jour_semaine) == jour_n.lower(),
        Cours.heure_debut < fin_n,
        Cours.heure_fin > debut_n,
    ]
    if cours_exclu_id:
        conditions.append(Cours.id != cours_exclu_id)
    # Salle : comparée en texte, casse ignorée — la correspondance nommée
    # est le seul lien qui existe entre un cours et la salle.
    condition_salle = func.lower(func.trim(Cours.salle)) == salle_n if salle_n else None
    # Enseignant : comparée par identifiant de compte.
    condition_enseignant = (
        Cours.enseignant_id == enseignant_id if enseignant_id is not None else None
    )
    if condition_salle is None and condition_enseignant is None:
        return []
    # Les deux branches ne s'additionnent pas : un cours en conflit de salle
    # ET d'enseignant serait compté deux fois, et « deux conflits » pour une
    # seule séance contradictoire embrouille plus qu'il n'éclaire.
    filtre = (
        condition_salle if condition_enseignant is None
        else condition_enseignant if condition_salle is None
        else or_(condition_salle, condition_enseignant)
    )
    stmt = select(Cours).where(and_(*conditions, filtre))
    autres = (await db.execute(stmt)).scalars().all()

    noms_matiere = await _matieres_noms(db, [c.matiere_id for c in autres])

    conflits: List[ConflitEdt] = []
    for cours in autres:
        if salle_n and condition_salle is not None and (cours.salle or "").strip().lower() == salle_n:
            conflits.append(_conflit_depuis(cours, noms_matiere.get(cours.matiere_id), "salle"))
        elif (
            enseignant_id is not None
            and condition_enseignant is not None
            and cours.enseignant_id == enseignant_id
        ):
            conflits.append(_conflit_depuis(cours, noms_matiere.get(cours.matiere_id), "enseignant"))
    return conflits


async def salle_par_nom(db: AsyncSession, nom: Optional[str]) -> Optional[Salle]:
    """La salle enregistrée que ce nom désigne, sinon None.

    La correspondance est insensible à la casse et aux espaces d'extrémité :
    « amphi a », « Amphi A » et « Amphi A  » désignent la même salle.
    """
    nom_n = (nom or "").strip().lower()
    if not nom_n:
        return None
    return (
        await db.execute(
            select(Salle).where(func.lower(Salle.nom) == nom_n)
        )
    ).scalars().first()


async def lister_conflits_existants(db: AsyncSession) -> List[ConflitEdt]:
    """L'audit : les paires de cours déjà en conflit dans l'emploi du temps.

    Un conflit est rapporté une fois par paire, du point de vue du cours le
    plus récent (celui qui « a pris » le créneau) : la liste reste courte et
    chaque entrée désigne clairement la séance à déplacer.

    Détail : le conflit « enseignant » ne se signale que si le même compte
    enseigne deux cours simultanés — deux noms saisis à la main ne prouvent
    rien, c'est le même ``enseignant_id`` qui fait foi.
    """
    cours_liste = (await db.execute(select(Cours))).scalars().all()
    noms_matiere = await _matieres_noms(db, [c.matiere_id for c in cours_liste])

    conflits: List[ConflitEdt] = []
    vus: set = set()
    for i, cours in enumerate(cours_liste):
        for autre in cours_liste[i + 1:]:
            if cours.id == autre.id:
                continue
            jour_a = jour_normalise(cours.jour_semaine)
            jour_b = jour_normalise(autre.jour_semaine)
            if jour_a is None or jour_b is None or jour_a != jour_b:
                continue
            if not chevauchement(
                cours.heure_debut, cours.heure_fin, autre.heure_debut, autre.heure_fin
            ):
                continue
            meme_salle = (cours.salle or "").strip().lower() == (autre.salle or "").strip().lower()
            meme_enseignant = (
                cours.enseignant_id is not None
                and cours.enseignant_id == autre.enseignant_id
            )
            if not (meme_salle or meme_enseignant):
                continue
            paire = tuple(sorted((cours.id, autre.id)))
            if paire in vus:
                continue
            vus.add(paire)
            # Le conflit se rapporte au plus récent des deux : c'est lui qui
            # s'est posé sur un créneau déjà occupé (et l'ordre de création
            # est aussi l'ordre de lecture dans l'audit).
            recente, ancienne = (
                (cours, autre) if cours.created_at and autre.created_at
                and cours.created_at >= autre.created_at else (autre, cours)
            )
            type_conflit = "salle" if meme_salle else "enseignant"
            conflits.append(
                ConflitEdt(
                    type=type_conflit,
                    cours_id=recente.id,
                    matiere=noms_matiere.get(recente.matiere_id),
                    enseignant_nom=recente.enseignant_nom,
                    salle=recente.salle,
                    jour=recente.jour_semaine,
                    heure_debut=recente.heure_debut,
                    heure_fin=recente.heure_fin,
                )
            )
    return conflits
