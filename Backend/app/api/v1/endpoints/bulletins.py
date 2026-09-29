"""Genere le bulletin de notes d'un etudiant pour un semestre.

Deux routes, volontairement separees :

- une qui rend le PDF ;
- une qui rend le **contenu** en JSON, pour l'ecran.

La seconde n'est pas un luxe : c'est elle qui permet de verifier le contenu du
bulletin sans passer par le PDF, donc de controler ce que le document affirme
avant qu'il ne parte a l'imprimante. Le PDF et le JSON sont produits par le
meme appel a ``semestre_service`` et le meme ``composer_bulletin`` — ils ne
peuvent donc pas diverger sur les chiffres.

Aucun journal d'emission n'est ecrit. Le bulletin n'est pas un document
delivre par le systeme : il sort de l'imprimante et se signe a la main. Le
dire dans un registre d'emission reviendrait a inscrire un document officiel
que personne n'a emis.
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_pedagogy_grades_read
from app.models.academic import Classe
from app.models.deliberation import Deliberation, DeliberationDecision
from app.models.etablissement import Etablissement
from app.models.etudiant import Etudiant
from app.models.session_academique import SessionAcademique
from app.models.structure import Semestre
from app.services.bulletin_pdf import rendre_bulletin_pour
from app.services import deliberation_service as service
from app.services.bulletin_service import Bulletin, composer_bulletin
from app.services.deliberation_service import BAREME_REPLI
from app.services.semestre_service import bilan_semestre, recap_annuel

router = APIRouter()


#: La recherche de la derniere decision appartient au service : l'endpoint et
#: la liste de rattrapage en ont tous les deux besoin. Un service qui
#: importerait un endpoint formerait une boucle d'import.
_derniere_decision = service.derniere_decision


async def _contexte(
    db: AsyncSession, etudiant_id: str, semestre_id: str
):
    """Charge ce qu'il faut, et dit ce qui manque.

    Les 404 sont nommes : « etudiant inconnu » et « semestre inconnu » ne
    donnent pas le meme travail a l'agent, et un message generique le renverrait
    a tout revérifier.
    """

    etudiant = await db.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet étudiant n'existe pas.",
        )

    semestre = await db.get(Semestre, semestre_id)
    if semestre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce semestre n'existe pas. Créez-le depuis Paramètres ▸ "
                   "Structure ▸ Semestres.",
        )

    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    session = await db.get(SessionAcademique, semestre.session_id)
    decision = await service.derniere_decision(
        db, etudiant_id=etudiant_id, session_id=semestre.session_id
    )

    return etudiant, semestre, etablissement, session, decision


async def _composer(db: AsyncSession, etudiant_id: str, semestre_id: str):
    etudiant, semestre, etablissement, session, decision = await _contexte(
        db, etudiant_id, semestre_id
    )

    decisions: Dict[str, Dict[str, Any]] = {}
    bilan = await bilan_semestre(
        db,
        etudiant_id=etudiant_id,
        session_id=semestre.session_id,
        semestre_id=semestre_id,
        decisions=decisions,
    )
    recap = await recap_annuel(
        db,
        etudiant_id=etudiant_id,
        session_id=semestre.session_id,
        semestre_id=semestre_id,
        decisions=decisions,
    )

    bareme: Sequence[Dict[str, Any]] = list(BAREME_REPLI["bareme_mentions"])
    if decision is not None:
        regles = getattr(decision, "regles", None) or {}
        if regles.get("bareme_mentions"):
            bareme = list(regles["bareme_mentions"])

    bulletin = composer_bulletin(
        bilan,
        infos={
            "etablissement": {
                "nom": getattr(etablissement, "nom", None),
                "sigle": getattr(etablissement, "sigle", None),
                "adresse": getattr(etablissement, "adresse", None),
                "telephone": getattr(etablissement, "telephone", None),
                "email": getattr(etablissement, "email", None),
                "pays": getattr(etablissement, "pays", None),
            },
            "etudiant": {
                "nom": getattr(etudiant, "nom", None),
                "prenom": getattr(etudiant, "prenom", None),
                "matricule": getattr(etudiant, "matricule", None),
                "filiere": getattr(etudiant, "filiere", None),
                "niveau": getattr(etudiant, "niveau", None),
                "classe": getattr(getattr(etudiant, "classe", None), "nom", None),
            },
            "session": {
                "nom": getattr(session, "nom", None),
                "annee_academique": getattr(session, "annee_academique", None),
            },
            "bareme_mentions": bareme,
        },
        recap=recap,
    )
    bulletin.deliberation_absente = decision is None
    return bulletin


def _en_json(bulletin: Bulletin) -> Dict[str, Any]:
    """Le contenu du bulletin, en JSON, tel qu'il sera imprime."""

    return {
        "etudiant": {
            "nom": bulletin.etudiant_nom,
            "prenom": bulletin.etudiant_prenom,
            "matricule": bulletin.matricule,
            "filiere": bulletin.filiere,
            "niveau": bulletin.niveau,
            "classe": bulletin.classe,
        },
        "etablissement": {
            "nom": bulletin.etablissement_nom,
            "sigle": bulletin.etablissement_sigle,
            "adresse": bulletin.etablissement_adresse,
            "pays": bulletin.etablissement_pays,
        },
        "session": {
            "nom": bulletin.session_nom,
            "annee_academique": bulletin.session_annee,
            "semestre_numero": bulletin.semestre_numero,
            "semestre_libelle": bulletin.semestre_libelle,
        },
        "unites": [
            {
                "code": bloc.code,
                "nom": bloc.nom,
                "cue": bloc.cue,
                "annuelle": bloc.annuelle,
                "mue": bloc.mue,
                "mention": bloc.mention,
                # Ce que le jury a decide, ou ``None`` tant qu'il n'a pas
                # tranche. Et ce que le moteur avait propose, que l'ecran
                # affiche **comme une proposition** : sans elle, l'agent ne
                # verrait qu'un trou la ou le jury doit statuer.
                "validation": bloc.validation,
                "proposition_validation": bloc.proposition_validation,
                "credits_obtenus": bloc.credits_obtenus,
                "matieres": [
                    {
                        "code": matiere.code,
                        "nom": matiere.nom,
                        "mcc": matiere.mcc,
                        "exam": matiere.exam,
                        "cec": matiere.cec,
                        "mec": matiere.mec,
                    }
                    for matiere in bloc.matieres
                ],
            }
            for bloc in bulletin.blocs
        ],
        "totaux": {
            "credits_prevus": bulletin.credits_prevus,
            "credits_obtenus": bulletin.credits_obtenus,
            "moyenne": bulletin.moyenne_semestre,
            "mention": bulletin.mention_semestre,
        },
        "recapitulatif": {
            "lignes": [
                {
                    "libelle": ligne.libelle,
                    "credits": ligne.credits,
                    "moyenne": ligne.moyenne,
                }
                for ligne in bulletin.recapitulatif
            ],
            "moyenne_annuelle": bulletin.moyenne_annuelle,
            "mention_annuelle": bulletin.mention_annuelle,
        },
        "observations": {
            "incompletudes": bulletin.incompletudes,
            "annuelles_absentes": bulletin.annuelles_absentes,
            "hors_bulletin": bulletin.hors_bulletin,
            "deliberation_absente": bulletin.deliberation_absente,
        },
    }


@router.get(
    "/bulletins/classe/{classe_id}/{semestre_id}/archive",
    summary="Bulletins d'une classe entiere pour un semestre (ZIP)",
)
async def telecharger_bulletins_classe(
    classe_id: str,
    semestre_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_pedagogy_grades_read),
):
    """Le lot de toute une classe : un ZIP, un bulletin par etudiant.

    La seance de signature du directeur ne demande pas trente clics : elle
    demande une liasse. L'archive reprend, pour chaque etudiant inscrit dans
    la classe, **exactement** le PDF que l'ecran individuel produit — le meme
    calcul, la meme mise en page. Un lot qui imiterait le bulletin sans le
    recalculer pourrait diverger du document signe un par un ; il n'y a donc
    pas deux chemins de rendu.

    Les garde-fous du bulletin individuel tient dans le lot : une classe sans
    etudiant refuse (un ZIP vide se lirait comme des bulletins perdus), et un
    etudiant dont le bulletin echoue n'interrompt pas les autres — son nom
    figure dans un rapport joint a l'archive, jamais perdu en silence.
    """

    classe = await db.get(Classe, classe_id)
    if classe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette classe n'existe pas.",
        )

    semestre = await db.get(Semestre, semestre_id)
    if semestre is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce semestre n'existe pas. Créez-le depuis Paramètres ▸ "
                   "Structure ▸ Semestres.",
        )

    etudiants = list(
        (
            await db.execute(
                select(Etudiant)
                .where(Etudiant.classe_id == classe_id)
                .order_by(Etudiant.nom, Etudiant.prenom)
            )
        ).scalars().all()
    )
    if not etudiants:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"La classe {classe.nom} n'a aucun étudiant inscrit : rien à "
                "télécharger. Les bulletins se créent par dossier, pas par "
                "promotion vide."
            ),
        )

    etablissement = (
        await db.execute(select(Etablissement).limit(1))
    ).scalars().first()
    session = await db.get(SessionAcademique, semestre.session_id)

    archive = io.BytesIO()
    echecs: List[Dict[str, str]] = []
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as lot:
        for etudiant in etudiants:
            try:
                decision = await service.derniere_decision(
                    db, etudiant_id=etudiant.id, session_id=semestre.session_id
                )
                contenu, nom_fichier = await rendre_bulletin_pour(
                    db,
                    etudiant=etudiant,
                    semestre=semestre,
                    etablissement=etablissement,
                    session=session,
                    decision=decision,
                )
                lot.writestr(nom_fichier, contenu)
            except Exception as exception:  # noqa: BLE001
                # Un etudiant en erreur ne prive pas la classe de son lot :
                # le secretariat imprime les vingt-neuf autres, et le rapport
                # dit lequel reprodure a la main. Avaler l'erreur sans trace
                # ferait croire a un bulletin perdu dans la liasse.
                echecs.append({
                    "matricule": etudiant.matricule or "?",
                    "etudiant": f"{etudiant.nom} {etudiant.prenom}",
                    "raison": str(exception) or exception.__class__.__name__,
                })

        if echecs:
            rapport = ["Bulletins non produits :", ""]
            for echec in echecs:
                rapport.append(
                    f"- {echec['matricule']} — {echec['etudiant']} : "
                    f"{echec['raison']}"
                )
            lot.writestr("_bulletins-non-produits.txt", "\n".join(rapport))

    morceau = re.compile(r"[^A-Za-z0-9_-]+")
    nom_archive = (
        f"bulletins_{morceau.sub('-', (classe.nom or classe_id).strip())}_"
        f"{morceau.sub('-', semestre.libelle or f'S{semestre.numero}')}.zip"
    )
    return Response(
        content=archive.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nom_archive}"'},
    )


@router.get(
    "/bulletins/{etudiant_id}/{semestre_id}",
    summary="Contenu du bulletin d'un etudiant (JSON)",
)
async def lire_bulletin(
    etudiant_id: str,
    semestre_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_pedagogy_grades_read),
):
    """Le contenu du bulletin, avant impression.

    Cette route et le PDF sortent du meme calcul : ce que l'agent lit ici est
    exactement ce qui sera imprime. C'est ce qui permet de verifier un bulletin
    sans l'imprimer, et donc de ne pas distribuer un document faux.
    """

    bulletin = await _composer(db, etudiant_id, semestre_id)
    return _en_json(bulletin)


@router.get(
    "/bulletins/{etudiant_id}/{semestre_id}/pdf",
    summary="Bulletin d'un etudiant (PDF)",
)
async def telecharger_bulletin(
    etudiant_id: str,
    semestre_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_pedagogy_grades_read),
):
    """Rend le bulletin en PDF.

    Le document sort de l'imprimante pour etre signe et cachete a la main :
    ni signature ni cachet n'y sont imprimes, et le pied de page le dit.
    """

    etudiant, semestre, etablissement, session, decision = await _contexte(
        db, etudiant_id, semestre_id
    )
    contenu, nom_fichier = await rendre_bulletin_pour(
        db,
        etudiant=etudiant,
        semestre=semestre,
        etablissement=etablissement,
        session=session,
        decision=decision,
    )
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


@router.get(
    "/rattrapage/{etudiant_id}",
    summary="Matieres a reprendre pour un etudiant",
)
async def lire_rattrapage(
    etudiant_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_pedagogy_grades_read),
):
    """Les matieres sur lesquelles l'etudiant peut repasser une epreuve.

    La liste vient des **decisions du jury**, pas des propositions du moteur :
    tant que le jury n'a pas tranche, rien n'est a reprendre. Sans cela,
    l'ecran proposerait des epreuves que personne n'a decidees.

    Trois etats, distingues parce qu'ils ne se remedent pas de la meme facon :

    - **aucune seance** : le jury ne s'est pas prononce. Rien a afficher, et
      le dire — pas une liste vide qui se lirait comme « rien a reprendre » ;
    - **seance tenue, aucune UE a reprendre** : c'est une reponse. Elle est
      ecrite comme telle ;
    - **liste** : les matieres, avec leur UE et leur coefficient.
    """

    etudiant = await db.get(Etudiant, etudiant_id)
    if etudiant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet étudiant n'existe pas.",
        )

    decision = await service.derniere_decision(
        db, etudiant_id=etudiant_id, session_id=session_id
    )
    matieres = await service.matieres_a_reprendre(
        db, etudiant_id=etudiant_id, session_id=session_id
    )

    if decision is None:
        etat = "aucune_seance"
        message = (
            "Aucune séance de jury n'est enregistrée pour cet étudiant sur "
            "cette session. Les matières à reprendre seront connues une fois "
            "que le jury aura statué."
        )
    elif not matieres:
        etat = "rien_a_reprendre"
        message = "Le jury n'a mis aucune unité d'enseignement à reprendre."
    else:
        etat = "a_reprendre"
        message = None

    unites: Dict[str, Any] = {}
    for entree in matieres:
        groupe = unites.setdefault(entree["ue_id"], {
            "ue_id": entree["ue_id"],
            "ue_code": entree["ue_code"],
            "ue_nom": entree["ue_nom"],
            "credits_ue": entree["credits_ue"],
            "matieres": [],
        })
        groupe["matieres"].append({
            "matiere_id": entree["matiere_id"],
            "matiere_code": entree["matiere_code"],
            "matiere_nom": entree["matiere_nom"],
            "coefficient": entree["coefficient"],
        })

    return {
        "etudiant_id": etudiant_id,
        "matricule": etudiant.matricule,
        "nom": etudiant.nom,
        "prenom": etudiant.prenom,
        "etat": etat,
        "message": message,
        "unites": list(unites.values()),
        "total_matieres": len(matieres),
    }


__all__ = ["router"]
