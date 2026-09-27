"""Deliberation : regles du jury, seance, decisions, proces-verbal.

Trois droits distincts, coherents avec le partage retenu pour l'identite
institutionnelle :

- **lire** les regles, les seances et le projet de PV (``academic.read``) :
  un enseignant doit voir a quelle regle la promotion va etre evaluee ;
- **proposer et deliberer** (``pedagogy.write``) : ouvrir une seance, consigner
  une decision, arreter le verdict. L'ecriture des notes et la tenue du jury
  relevent du meme metier academique ;
- **administrer le reglement** (``institution.settings``) : les seuils sont
  une decision d'institut, pas une preference pedagogique. Les entrusted a
  celui qui configure l'etablissement evite d'ouvrir ``roles.manage`` au
  directeur des etudes pour ajuster un bareme.

Le proces-verbal se telecharge par ``documents.read``, comme les autres
documents officiels.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_academic_read, require_permission
from app.models.academic import Classe
from app.models.deliberation import Deliberation as DeliberationModel
from app.models.deliberation import DeliberationDecision, ReglesDeliberation
from app.models.etablissement import Etablissement
from app.models.etudiant import Etudiant
from app.models.session_academique import SessionAcademique
from app.models.utilisateur import Utilisateur
from app.schemas.deliberation import (
    DecisionOut,
    DecisionPrise,
    DecisionsUnitesEns,
    DeliberationCloture,
    DeliberationCreation,
    DeliberationDetail,
    DeliberationOut,
    ReglesDeliberationMaj,
    ReglesDeliberationOut,
)
from app.services import deliberation_service as service
from app.services.deliberation_service import DeliberationInvalide
from app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()

#: Tenue d'une seance de jury : meme metier que la saisie des notes.
require_deliberation_write = require_permission("pedagogy.write")
#: Le reglement est une decision d'institut.
require_regles_write = require_permission("institution.settings")


def _erreur(cause: DeliberationInvalide) -> HTTPException:
    """Transforme une regle metier refus en reponse explicite."""

    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(cause))


# ---------------------------------------------------------------------------
# Regles
# ---------------------------------------------------------------------------
@router.get(
    "/regles",
    response_model=ReglesDeliberationOut,
    summary="Consulter le reglement de deliberation",
)
async def lire_regles(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
):
    regles = await service.charger_regles(db)
    return ReglesDeliberationOut(
        seuil_validation_moyenne=regles["seuil_validation_moyenne"],
        seuil_eliminatoire=regles["seuil_eliminatoire"],
        seuil_rattrapage_minimale=regles["seuil_rattrapage_minimale"],
        seuil_passage_conditionnel_ects=regles["seuil_passage_conditionnel_ects"],
        compensation_autorisee=regles["compensation_autorisee"],
        bareme_mentions=regles["bareme_mentions"],
        confirmee=bool(regles.get("confirmee")),
        confirme_par=regles.get("confirme_par"),
        confirme_le=regles.get("confirme_le"),
    )


@router.put(
    "/regles",
    response_model=ReglesDeliberationOut,
    summary="Modifier le reglement de deliberation",
)
async def modifier_regles(
    payload: ReglesDeliberationMaj,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_regles_write),
):
    """Enregistre le reglement de l'institut.

    Modifier le reglement ne modifie **aucune** deliberation deja tenue : les
    regles sont figees dans chaque seance. Un changement de bareme n'a donc
    d'effet que sur les prochaines seances.
    """

    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    if etablissement is None:
        raise HTTPException(
            status_code=404, detail="Aucun etablissement configure."
        )

    ligne = (await db.execute(select(ReglesDeliberation).limit(1))).scalars().first()
    if ligne is None:
        ligne = ReglesDeliberation(
            id="regles-deliberation",
            etablissement_id=etablissement.id,
        )
        db.add(ligne)

    ligne.seuil_validation_moyenne = payload.seuil_validation_moyenne
    ligne.seuil_eliminatoire = payload.seuil_eliminatoire
    ligne.seuil_rattrapage_minimale = payload.seuil_rattrapage_minimale
    ligne.seuil_passage_conditionnel_ects = payload.seuil_passage_conditionnel_ects
    ligne.compensation_autorisee = payload.compensation_autorisee
    ligne.bareme_mentions = [entree.model_dump() for entree in payload.bareme_mentions]

    if payload.confirme:
        ligne.confirme_par_id = auteur.id
        ligne.confirme_par_email = auteur.email
        ligne.confirme_le = datetime.now(timezone.utc)
    elif not ligne.confirme_le:
        # Les valeurs changent sans être validees : le reglement retombe en
        # « a confirmer ». C'est plus strict, mais c'est honnete.
        ligne.confirme_par_id = None
        ligne.confirme_par_email = None
        ligne.confirme_le = None

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="institution.regles_deliberation.updated",
        resource_type="etablissement",
        resource_id=etablissement.id,
        details={
            "seuil_validation": payload.seuil_validation_moyenne,
            "seuil_eliminatoire": payload.seuil_eliminatoire,
            "confirme": payload.confirme,
        },
    )
    await db.commit()
    await db.refresh(ligne)

    return await lire_regles(db=db, _auth=auteur)


# ---------------------------------------------------------------------------
# Seances
# ---------------------------------------------------------------------------
def _donnees_seance(
    seance: DeliberationModel, decisions: List[DeliberationDecision]
) -> Dict[str, Any]:
    """Champs communs d'une seance, prets pour l'un ou l'autre schema.

    On prepare un dictionnaire plutot que d'instancier ``DeliberationOut`` et
    d'y ajouter des champs ensuite : Pydantic v2 refuse l'affectation d'un
    champ absent du modele, et la seance detaillee en a trois de plus.
    """

    return dict(
        id=seance.id,
        classe_id=seance.classe_id,
        classe_nom=seance.classe.nom if seance.classe else None,
        session_id=seance.session_id,
        session_nom=seance.session.nom if seance.session else None,
        date_deliberation=seance.date_deliberation,
        lieu=seance.lieu,
        president=seance.president,
        membres=list(seance.membres or []),
        statut=seance.statut,
        regles=dict(seance.regles or {}),
        close_le=seance.close_le,
        created_at=seance.created_at,
        nb_decisions=len(decisions),
    )


@router.get(
    "/",
    response_model=List[DeliberationOut],
    summary="Lister les seances de jury",
)
async def lister_deliberations(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
):
    stmt = (
        select(DeliberationModel)
        .order_by(DeliberationModel.date_deliberation.desc())
    )
    seances = list((await db.execute(stmt)).scalars().all())
    if not seances:
        return []

    decisions = list(
        (
            await db.execute(
                select(DeliberationDecision).where(
                    DeliberationDecision.deliberation_id.in_([s.id for s in seances])
                )
            )
        )
        .scalars()
        .all()
    )
    par_seance: Dict[str, List[DeliberationDecision]] = {}
    for decision in decisions:
        par_seance.setdefault(decision.deliberation_id, []).append(decision)

    resultats = []
    for seance in seances:
        donnees = _donnees_seance(seance, par_seance.get(seance.id, []))
        donnees["nb_inscrits"] = len(
            await service.etudiants_promotion(db, seance.classe_id, seance.session_id)
        )
        resultats.append(DeliberationOut(**donnees))
    return resultats


@router.post(
    "/",
    response_model=DeliberationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ouvrir une seance de jury",
)
async def ouvrir_deliberation(
    payload: DeliberationCreation,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_deliberation_write),
):
    """Ouvre une seance et fige les regles en vigueur.

    Une seance **ne decide de rien** a elle seule : elle ouvre le travail du
    jury. Les decisions sont consignees une par une, puis le verdict est
    arrete par un appel distinct.
    """

    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    if etablissement is None:
        raise HTTPException(status_code=404, detail="Aucun etablissement configure.")

    classe = await db.get(Classe, payload.classe_id)
    if classe is None:
        raise HTTPException(
            status_code=422, detail="La classe selectionnee n'existe pas."
        )
    session = await db.get(SessionAcademique, payload.session_id)
    if session is None:
        raise HTTPException(
            status_code=422, detail="La session selectionnee n'existe pas."
        )

    try:
        seance = await service.creer_deliberation(
            db,
            etablissement_id=etablissement.id,
            classe_id=payload.classe_id,
            session_id=payload.session_id,
            date_deliberation=payload.date_deliberation,
            president=payload.president,
            membres=[membre.model_dump() for membre in payload.membres],
            lieu=payload.lieu,
        )
    except DeliberationInvalide as exc:
        await db.rollback()
        raise _erreur(exc) from exc

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="deliberation.opened",
        resource_type="deliberation",
        resource_id=seance.id,
        details={
            "classe_id": payload.classe_id,
            "session_id": payload.session_id,
            "president": seance.president,
            "membres": len(seance.membres),
            "regles_confirmees": bool((seance.regles or {}).get("confirmee")),
        },
    )
    await db.commit()
    await db.refresh(seance)

    donnees = _donnees_seance(seance, [])
    donnees["nb_inscrits"] = len(
        await service.etudiants_promotion(db, seance.classe_id, seance.session_id)
    )
    return DeliberationOut(**donnees)


@router.get(
    "/{deliberation_id}",
    response_model=DeliberationDetail,
    summary="Consulter une seance, ses propositions et ses decisions",
)
async def lire_deliberation(
    deliberation_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
):
    seance = await service.deliberation_id(db, deliberation_id)
    if seance is None:
        raise HTTPException(status_code=404, detail="Seance de jury introuvable.")

    inscrits = await service.etudiants_promotion(db, seance.classe_id, seance.session_id)

    # Les propositions sont recalculees a partir des notes **du jour**. La
    # decision, elle, reste celle qui a ete consignee : si des notes ont ete
    # modifiees depuis, l'ecart est visible plutot que masque.
    regles = dict(seance.regles or {})
    propositions: List[Dict[str, Any]] = []
    avertissements: List[str] = []
    try:
        brutes = await service.proposer_promotion(
            db, seance.classe_id, seance.session_id, regles
        )
    except DeliberationInvalide as exc:
        brutes = []
        avertissements.append(str(exc))

    decisions_par_etudiant = {d.etudiant_id: d for d in seance.decisions}

    for brute in brutes:
        if brute.get("etudiant") is None:
            avertissements.extend(brute.get("avertissements") or [])
            continue
        etudiant = brute["etudiant"]
        classe = brute["inscription"].classe
        avertissements.extend(brute.get("avertissements") or [])
        decision = decisions_par_etudiant.get(etudiant.id)
        propositions.append(
            {
                "etudiant_id": etudiant.id,
                "matricule": etudiant.matricule,
                "nom": etudiant.nom,
                "prenom": etudiant.prenom,
                "filiere": classe.filiere.nom if classe and classe.filiere else None,
                "moyenne_generale": brute["moyenne_generale"],
                "ects_acquis": brute["ects_acquis"],
                "ects_total": brute["ects_total"],
                "proposition_statut": brute["proposition_statut"],
                "proposition_mention": brute["proposition_mention"],
                "moyennes_ue": brute["moyennes_ue"],
                "notes_eliminatoires": brute["notes_eliminatoires"],
                "matieres_hors_ue": brute["matieres_hors_ue"],
                "avertissements": brute["avertissements"],
                "decision_statut": decision.statut if decision else None,
                "decision_mention": decision.mention if decision else None,
                "motif_ecart": decision.motif_ecart if decision else None,
                "ecart": decision.ecart_proposition if decision else False,
            }
        )

    detail = DeliberationDetail(
        **_donnees_seance(seance, list(seance.decisions)),
        nb_inscrits=len(inscrits),
        propositions=propositions,
        decisions=[
        DecisionOut(
            etudiant_id=decision.etudiant_id,
            matricule=decision.etudiant.matricule if decision.etudiant else None,
            nom=decision.etudiant.nom if decision.etudiant else None,
            prenom=decision.etudiant.prenom if decision.etudiant else None,
            proposition_statut=decision.proposition_statut,
            proposition_mention=decision.proposition_mention,
            statut=decision.statut,
            mention=decision.mention,
            motif_ecart=decision.motif_ecart,
            ecart=decision.ecart_proposition,
            moyenne_generale=decision.moyenne_generale,
            ects_acquis=decision.ects_acquis,
            ects_total=decision.ects_total,
            moyennes_ue=dict(decision.moyennes_ue or {}),
            notes_eliminatoires=list(decision.notes_eliminatoires or []),
            decide_le=decision.decide_le,
        )
            for decision in seance.decisions
        ],
        avertissements=sorted(set(avertissements)),
    )
    return detail


@router.post(
    "/{deliberation_id}/decisions",
    response_model=DecisionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Consigner la decision du jury pour un etudiant",
)
async def consigner_decision(
    deliberation_id: str,
    etudiant_id: str,
    payload: DecisionPrise,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_deliberation_write),
):
    """Consigne une decision, en conservant la proposition du moteur.

    Ce que le moteur calcule et ce que le jury decide restent deux choses
    distinctes dans la base. Un ecart exige un motif : sans lui, le verdict
    serait inexplique.
    """

    seance = await service.deliberation_id(db, deliberation_id)
    if seance is None:
        raise HTTPException(status_code=404, detail="Seance de jury introuvable.")

    regles = dict(seance.regles or {})
    try:
        inscriptions = await service.etudiants_promotion(
            db, seance.classe_id, seance.session_id
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail="Promotion illisible."
        ) from exc

    etudiant = next(
        (i.etudiant for i in inscriptions if str(i.etudiant_id) == etudiant_id), None
    )
    if etudiant is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Cet etudiant n'est pas inscrit dans la promotion concernee : "
                "le jury n'a pas a se prononcer sur lui."
            ),
        )

    try:
        proposition = await service.proposer(db, etudiant, seance.session_id, regles)
        decision = await service.enregistrer_decision(
            db,
            seance,
            etudiant_id=etudiant_id,
            statut=payload.statut,
            mention=payload.mention,
            proposition=proposition,
            motif_ecart=payload.motif_ecart,
            auteur_id=auteur.id,
        )
    except DeliberationInvalide as exc:
        await db.rollback()
        raise _erreur(exc) from exc

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="deliberation.decision.recorded",
        resource_type="deliberation",
        resource_id=seance.id,
        details={
            "etudiant_id": etudiant_id,
            "statut": decision.statut,
            "mention": decision.mention,
            "proposition": decision.proposition_statut,
            "ecart": decision.ecart_proposition,
        },
    )
    await db.commit()
    await db.refresh(decision)

    return DecisionOut(
        etudiant_id=decision.etudiant_id,
        matricule=etudiant.matricule,
        nom=etudiant.nom,
        prenom=etudiant.prenom,
        proposition_statut=decision.proposition_statut,
        proposition_mention=decision.proposition_mention,
        statut=decision.statut,
        mention=decision.mention,
        motif_ecart=decision.motif_ecart,
        ecart=decision.ecart_proposition,
        moyenne_generale=decision.moyenne_generale,
        ects_acquis=decision.ects_acquis,
        ects_total=decision.ects_total,
        moyennes_ue=dict(decision.moyennes_ue or {}),
        notes_eliminatoires=list(decision.notes_eliminatoires or []),
        decide_le=decision.decide_le,
    )


@router.put(
    "/{deliberation_id}/decisions/{etudiant_id}/unites",
    response_model=DecisionOut,
    summary="Consigner les decisions du jury par unite d'enseignement",
)
async def consigner_decisions_unites(
    deliberation_id: str,
    etudiant_id: str,
    payload: DecisionsUnitesEns,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_deliberation_write),
):
    """Enregistre, pour un etudiant, ce que le jury decide sur chaque UE.

    C'est l'ecrit qui manque entre la proposition du moteur et le bulletin : les
    trois etats — ``Validée``, ``Validée en SR``, ``À reprendre`` — qui
    commandent la suite, dont le rattrapage.

    Trois garde-fous, tous necessaires :

    - **Une UE inconnue est refusee.** Un typo dans un identifiant
      enregistrerait une decision sur une UE qui n'existe pas, et le bulletin
      n'afficherait rien — la decision serait perdue sans bruit.
    - **Un credit superieur au total de l'UE est refuse.** Le total d'ECTS
      acquis ne peut pas depasser le total prevu ; c'est une arithmetique, pas
      une convention.
    - **Un ecart avec la proposition exige un motif**, comme pour la decision
      d'ensemble. Valider une UE que le moteur jugeait a reprendre, sans dire
      pourquoi, laisserait un verdict inexplicable.

    L'enregistrement est **partiel et repete** : envoyer trois UE sur cinq
    n'annule pas les deux autres. Une seance se tranche progressivement, et un
    agent qui recoit une erreur au milieu ne doit pas perdre ce qu'il a deja
    saisi.
    """

    seance = await service.deliberation_id(db, deliberation_id)
    if seance is None:
        raise HTTPException(status_code=404, detail="Seance de jury introuvable.")

    decision = (
        await db.execute(
            select(DeliberationDecision).where(
                DeliberationDecision.deliberation_id == deliberation_id,
                DeliberationDecision.etudiant_id == etudiant_id,
            )
        )
    ).scalars().first()
    if decision is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Aucune decision n'est encore consignee pour cet etudiant sur "
                "cette seance. Consignez d'abord la decision d'ensemble."
            ),
        )

    # Copie **profonde** de chaque entree, pas du seul dictionnaire.
    #
    # ``dict(moyennes_ue)`` ne copierait que le premier niveau : les
    # dictionnaires internes resteraient les memes objets, et ecrire dans l'un
    # d'eux modifierait la valeur que SQLAlchemy compare — qui ne verrait donc
    # aucun changement, et n'ecrirait rien. L'API repondrait 200 sur une
    # decision perdue. Chaque entree est donc recopiee, pour que l'ecriture
    # porte sur un objet nouveau.
    moyennes = {
        identifiant: dict(entree)
        for identifiant, entree in (decision.moyennes_ue or {}).items()
        if isinstance(entree, dict)
    }
    inconnues = [
        entree.ue_id
        for entree in payload.decisions
        if entree.ue_id not in moyennes
    ]
    if inconnues:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Ces unites d'enseignement ne figurent pas a cette seance : "
                f"{', '.join(inconnues[:5])}"
                + ("…" if len(inconnues) > 5 else "")
                + ". La seance ne porte que les UE de la promotion, avec les "
                "moyennes calculees a son ouverture."
            ),
        )

    for entree in payload.decisions:
        ref = moyennes[entree.ue_id]
        total_ue = int(ref.get("ects") or 0)
        # Non fourni : la totalite des credits de l'UE. C'est la lecture
        # naturelle de « validee », et elle evite au client d'envoyer un
        # total qu'il n'a pas a connaitre.
        if entree.credits_obtenus is None:
            credits = total_ue if entree.validation != service.VALIDATION_UE_A_REPRENDRE else 0
        else:
            credits = entree.credits_obtenus
        if credits > total_ue:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"« {ref.get('code') or entree.ue_id} » porte {total_ue} "
                    f"crédit(s) : on ne peut en accorder {credits}. Si le jury "
                    "veut en accorder plus, c'est que les credits de l'UE sont "
                    "mal saisis — corrigez l'UE, pas la decision."
                ),
            )

        proposee = ref.get("proposition_validation")
        ecart = proposee is not None and proposee != entree.validation
        if ecart and not entree.motif:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"« {ref.get('code') or entree.ue_id} » : le moteur "
                    f"proposait « {proposee} », le jury decide "
                    f"« {entree.validation} ». Un ecart exige un motif."
                ),
            )

        ref["validation"] = entree.validation
        ref["credits_obtenus"] = credits
        ref["mention"] = entree.mention or ref.get("proposition_mention")
        if entree.motif:
            ref["motif_ecart"] = entree.motif

    decision.moyennes_ue = moyennes
    # Le total acquis se recalcule sur les seules decisions prises. Les UE non
    # tranchees comptent zero : leyer les credits d'une UE que le jury n'a pas
    # validee les concedait par defaut.
    decision.ects_acquis = sum(
        int(ref.get("credits_obtenus") or 0)
        for ref in moyennes.values()
        if ref.get("validation")
    )
    decision.decide_le = datetime.now(timezone.utc)
    decision.decide_par_id = auteur.id

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="deliberation.decision.unites_recorded",
        resource_type="deliberation",
        resource_id=seance.id,
        details={
            "etudiant_id": etudiant_id,
            "unites": [e.ue_id for e in payload.decisions],
            "ects_acquis": decision.ects_acquis,
        },
    )
    await db.commit()
    await db.refresh(decision)

    etudiant = await db.get(Etudiant, etudiant_id)
    return DecisionOut(
        etudiant_id=decision.etudiant_id,
        matricule=getattr(etudiant, "matricule", None) or "",
        nom=getattr(etudiant, "nom", None) or "",
        prenom=getattr(etudiant, "prenom", None) or "",
        proposition_statut=decision.proposition_statut,
        proposition_mention=decision.proposition_mention,
        statut=decision.statut,
        mention=decision.mention,
        motif_ecart=decision.motif_ecart,
        ecart=decision.ecart_proposition,
        moyenne_generale=decision.moyenne_generale,
        ects_acquis=decision.ects_acquis,
        ects_total=decision.ects_total,
        moyennes_ue=dict(decision.moyennes_ue or {}),
        notes_eliminatoires=list(decision.notes_eliminatoires or []),
        decide_le=decision.decide_le,
    )


@router.post(
    "/{deliberation_id}/cloturer",
    response_model=DeliberationOut,
    summary="Arreter le verdict d'une seance",
)
async def cloturer_deliberation(
    deliberation_id: str,
    payload: DeliberationCloture,
    db: AsyncSession = Depends(get_db),
    auteur: Utilisateur = Depends(require_deliberation_write),
):
    """Arrete le verdict. Apres cet appel, les decisions sont immuables.

    C'est la condition que l'attestation de reussite exige : tant qu'une
    seance est en brouillon, elle ne fonde aucun droit.
    """

    if (payload.confirmation or "").strip().lower() != "arreter":
        raise HTTPException(
            status_code=422,
            detail=(
                "La cloture est irreversible : confirmez en envoyant "
                "« arreter ». Sans cela, une seance pourrait etre fermee par "
                "une manipulation involontaire."
            ),
        )

    seance = await service.deliberation_id(db, deliberation_id)
    if seance is None:
        raise HTTPException(status_code=404, detail="Seance de jury introuvable.")

    try:
        await service.cloturer(db, seance, auteur_id=auteur.id)
    except DeliberationInvalide as exc:
        await db.rollback()
        raise _erreur(exc) from exc

    await record_audit_event(
        db,
        actor_id=auteur.id,
        actor_email=auteur.email,
        action="deliberation.closed",
        resource_type="deliberation",
        resource_id=seance.id,
        details={"nb_decisions": len(seance.decisions)},
    )
    await db.commit()
    await db.refresh(seance)

    return DeliberationOut(**_donnees_seance(seance, list(seance.decisions)))


@router.get(
    "/{deliberation_id}/proces-verbal",
    summary="Telecharger le proces-verbal de la seance",
    responses={200: {"content": {"application/pdf": {}}, "description": "PV du jury."}},
)
async def proces_verbal(
    deliberation_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_read),
):
    """Genere le proces-verbal a partir des decisions **consignees**.

    Un PV qui refleterait les propositions du moteur porterait des verdicts
    que le jury n'a pas pris. Seules les decisions enregistrees apparaissent.
    """

    seance = await service.deliberation_id(db, deliberation_id)
    if seance is None:
        raise HTTPException(status_code=404, detail="Seance de jury introuvable.")
    if not seance.decisions:
        raise HTTPException(
            status_code=422,
            detail=(
                "Aucune decision consignee : il n'y a pas de proces-verbal a "
                "produire. Un PV sans verdict serait un document vide."
            ),
        )

    from app.services.pv_service import rendre_proces_verbal

    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    contenu, nom_fichier = await rendre_proces_verbal(
        db,
        seance=seance,
        etablissement=etablissement,
        decisions=list(seance.decisions),
    )
    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nom_fichier}"'
        },
    )


__all__ = ["router"]
