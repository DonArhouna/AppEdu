"""Endpoints auto-service strictement scopés aux portails utilisateur.

Les listes métier globales restent réservées aux rôles du personnel. Les
portails utilisent des endpoints dédiés afin que le serveur filtre toujours les
données par l'identité authentifiée.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user, get_db
from app.models.etudiant import Etudiant
from app.models.etablissement import Etablissement
from app.models.finance import Facture
from app.models.pedagogie import Absence, Cours, Note
from app.models.session_academique import SessionAcademique
from app.models.structure import Filiere, Matiere, UniteEnseignement
from app.models.utilisateur import Utilisateur, UserRole
from app.schemas.portals import PortalEnseignantResponse, PortalEtudiantResponse

router = APIRouter()


def _require_portal_role(user: Utilisateur, expected_role: UserRole) -> None:
    if user.role != expected_role.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce portail est réservé au profil correspondant.",
        )


async def _resolve_student(db: AsyncSession, user: Utilisateur) -> Etudiant:
    """Résout le dossier lié au compte, avec reprise legacy par email.

    Le lien explicite est préféré. La correspondance email reste disponible
    pour les instances antérieures à la migration 0007, sans exposer une liste
    de dossiers au portail.
    """

    if user.etudiant_id:
        student = await db.get(Etudiant, user.etudiant_id)
    else:
        result = await db.execute(
            select(Etudiant).where(
                func.lower(Etudiant.email) == user.email.lower()
            )
        )
        student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun dossier étudiant n'est rattaché à ce compte. Contactez l'administration.",
        )
    return student


@router.get(
    "/etudiant",
    response_model=PortalEtudiantResponse,
    summary="Données du portail étudiant authentifié",
)
async def get_student_portal(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    _require_portal_role(current_user, UserRole.ETUDIANT)
    student = await _resolve_student(db, current_user)

    notes_result = await db.execute(
        select(Note)
        .where(Note.etudiant_id == student.id)
        .order_by(Note.created_at.desc())
    )
    notes = list(notes_result.scalars().all())

    absences_result = await db.execute(
        select(Absence)
        .where(Absence.etudiant_id == student.id)
        .order_by(Absence.date_absence.desc(), Absence.created_at.desc())
    )
    absences = list(absences_result.scalars().all())

    factures_result = await db.execute(
        select(Facture)
        .where(Facture.etudiant_id == student.id)
        .order_by(Facture.date_emission.desc(), Facture.created_at.desc())
    )
    factures = list(factures_result.scalars().all())

    # Les cours sont limités à la filière du dossier. Si la filière historique
    # n'est pas normalisée, aucun cours n'est exposé plutôt que tous les cours.
    matieres: List[Matiere] = []
    if student.filiere_id:
        matieres_result = await db.execute(
            select(Matiere)
            .join(UniteEnseignement, Matiere.ue_id == UniteEnseignement.id)
            .where(UniteEnseignement.filiere_id == student.filiere_id)
            .order_by(Matiere.nom)
        )
        matieres = list(matieres_result.scalars().all())
    elif student.filiere:
        matieres_result = await db.execute(
            select(Matiere)
            .join(UniteEnseignement, Matiere.ue_id == UniteEnseignement.id)
            .join(Filiere, UniteEnseignement.filiere_id == Filiere.id)
            .where(Filiere.nom == student.filiere)
            .order_by(Matiere.nom)
        )
        matieres = list(matieres_result.scalars().all())

    matiere_ids = [matiere.id for matiere in matieres]
    cours = []
    if matiere_ids:
        cours_result = await db.execute(
            select(Cours)
            .where(Cours.matiere_id.in_(matiere_ids))
            .order_by(Cours.jour_semaine, Cours.heure_debut)
        )
        cours = list(cours_result.scalars().all())

    session_ids = {note.session_id for note in notes if note.session_id}
    if student.session_id:
        session_ids.add(student.session_id)
    sessions = []
    if session_ids:
        sessions_result = await db.execute(
            select(SessionAcademique)
            .options(selectinload(SessionAcademique.periodes))
            .where(SessionAcademique.id.in_(session_ids))
            .order_by(SessionAcademique.date_debut.desc())
        )
        sessions = list(sessions_result.scalars().all())

    etablissement_result = await db.execute(select(Etablissement).limit(1))
    etablissement = etablissement_result.scalar_one_or_none()

    return PortalEtudiantResponse(
        etudiant=student,
        notes=notes,
        absences=absences,
        factures=factures,
        cours=cours,
        matieres=matieres,
        sessions=sessions,
        devise=etablissement.devise if etablissement else None,
    )


@router.get(
    "/enseignant",
    response_model=PortalEnseignantResponse,
    summary="Données du portail enseignant authentifié",
)
async def get_teacher_portal(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    _require_portal_role(current_user, UserRole.ENSEIGNANT)

    cours_result = await db.execute(
        select(Cours)
        .where(Cours.enseignant_id == current_user.id)
        .order_by(Cours.jour_semaine, Cours.heure_debut)
    )
    cours = list(cours_result.scalars().all())
    matiere_ids = sorted({cours_item.matiere_id for cours_item in cours})

    matieres: List[Matiere] = []
    notes: List[Note] = []
    if matiere_ids:
        matieres_result = await db.execute(
            select(Matiere)
            .where(Matiere.id.in_(matiere_ids))
            .order_by(Matiere.nom)
        )
        matieres = list(matieres_result.scalars().all())

        notes_result = await db.execute(
            select(Note)
            .where(Note.matiere_id.in_(matiere_ids))
            .order_by(Note.created_at.desc())
        )
        notes = list(notes_result.scalars().all())

    etudiant_ids = sorted({note.etudiant_id for note in notes})
    etudiants: List[Etudiant] = []
    if etudiant_ids:
        etudiants_result = await db.execute(
            select(Etudiant)
            .where(Etudiant.id.in_(etudiant_ids))
            .order_by(Etudiant.nom, Etudiant.prenom)
        )
        etudiants = list(etudiants_result.scalars().all())

    return PortalEnseignantResponse(
        cours=cours,
        matieres=matieres,
        notes=notes,
        etudiants=etudiants,
    )
