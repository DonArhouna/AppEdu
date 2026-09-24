"""
Endpoints Gestion des Étudiants :
- Recherche multi-critères
- Création avec génération automatique de matricule
- Inscription et affectation de session
"""

from typing import List, Optional
from datetime import date
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.api.deps import get_db, require_secretariat, require_admin, require_academic_staff
from app.models.etudiant import Etudiant
from app.models.structure import Filiere
from app.schemas.etudiant import (
    EtudiantResponse,
    EtudiantCreate,
    EtudiantUpdate,
    EtudiantInscriptionRequest,
)
from app.services.matricule_service import generate_matricule

router = APIRouter()


@router.get("/", response_model=List[EtudiantResponse], summary="Rechercher des étudiants")
async def list_etudiants(
    search: Optional[str] = Query(None, description="Nom, prénom, email ou matricule"),
    filiere: Optional[str] = None,
    filiere_id: Optional[str] = None,
    session_id: Optional[str] = None,
    statut: Optional[str] = None,
    niveau: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_staff),
):
    """Recherche multi-critères et liste complète des étudiants."""
    stmt = select(Etudiant)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Etudiant.nom.ilike(pattern),
                Etudiant.prenom.ilike(pattern),
                Etudiant.matricule.ilike(pattern),
                Etudiant.email.ilike(pattern),
            )
        )
    if filiere_id:
        stmt = stmt.where(Etudiant.filiere_id == filiere_id)
    elif filiere:
        stmt = stmt.where(Etudiant.filiere == filiere)
    if session_id:
        stmt = stmt.where(Etudiant.session_id == session_id)
    if statut:
        stmt = stmt.where(Etudiant.statut == statut)
    if niveau:
        stmt = stmt.where(Etudiant.niveau == niveau)

    stmt = stmt.order_by(Etudiant.nom.asc(), Etudiant.prenom.asc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/", response_model=EtudiantResponse, status_code=status.HTTP_201_CREATED, summary="Créer un étudiant")
async def create_etudiant(
    payload: EtudiantCreate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_secretariat),
):
    """
    Crée un nouvel étudiant.
    Si aucun matricule n'est fourni, il est automatiquement généré au format standard (ex: 2026-GL-0001).
    """
    if not payload.filiere_id and not payload.filiere.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La filière est obligatoire pour générer un matricule.",
        )
    filiere_code = ""
    if payload.filiere_id:
        stmt_f = select(Filiere).where(Filiere.id == payload.filiere_id)
        res_f = await db.execute(stmt_f)
        f_obj = res_f.scalar_one_or_none()
        if not f_obj:
            raise HTTPException(status_code=422, detail="La filière sélectionnée n'existe pas.")
        filiere_code = f_obj.code
    elif payload.filiere.strip():
        filiere_code = "".join([w[0] for w in payload.filiere.split() if w]).upper()[:4]

    matricule = payload.matricule
    if not matricule or not matricule.strip():
        matricule = await generate_matricule(db, filiere_code=filiere_code)

    # Vérification d'unicité du matricule
    stmt_check = select(Etudiant).where(Etudiant.matricule == matricule)
    res_check = await db.execute(stmt_check)
    if res_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Un étudiant avec le matricule '{matricule}' existe déjà.")

    etudiant = Etudiant(
        id=str(uuid.uuid4()),
        matricule=matricule,
        nom=payload.nom,
        prenom=payload.prenom,
        sexe=payload.sexe,
        email=str(payload.email) if payload.email else None,
        telephone=payload.telephone,
        date_naissance=payload.date_naissance,
        adresse=payload.adresse,
        filiere=payload.filiere,
        filiere_id=payload.filiere_id,
        niveau=payload.niveau,
        statut=payload.statut,
        photo_url=payload.photo_url,
        date_inscription=payload.date_inscription or date.today(),
        session_id=payload.session_id,
    )
    db.add(etudiant)
    await db.commit()
    await db.refresh(etudiant)
    return etudiant


@router.get("/{etudiant_id}", response_model=EtudiantResponse, summary="Détail d'un étudiant")
async def get_etudiant(
    etudiant_id: str,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_academic_staff),
):
    stmt = select(Etudiant).where(Etudiant.id == etudiant_id)
    res = await db.execute(stmt)
    etudiant = res.scalar_one_or_none()
    if not etudiant:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")
    return etudiant


@router.put("/{etudiant_id}", response_model=EtudiantResponse, summary="Modifier un étudiant")
async def update_etudiant(
    etudiant_id: str,
    payload: EtudiantUpdate,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_secretariat),
):
    stmt = select(Etudiant).where(Etudiant.id == etudiant_id)
    res = await db.execute(stmt)
    etudiant = res.scalar_one_or_none()
    if not etudiant:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        data["email"] = str(data["email"])

    for k, v in data.items():
        setattr(etudiant, k, v)

    await db.commit()
    await db.refresh(etudiant)
    return etudiant


@router.delete("/{etudiant_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un étudiant")
async def delete_etudiant(
    etudiant_id: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    stmt = select(Etudiant).where(Etudiant.id == etudiant_id)
    res = await db.execute(stmt)
    etudiant = res.scalar_one_or_none()
    if not etudiant:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")
    await db.delete(etudiant)
    await db.commit()


@router.post("/{etudiant_id}/inscrire", response_model=EtudiantResponse, summary="Inscrire un étudiant à une session")
async def inscrire_etudiant(
    etudiant_id: str,
    payload: EtudiantInscriptionRequest,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_secretariat),
):
    """Rattache directement un étudiant à une session académique et optionnellement met à jour sa filière/niveau."""
    stmt = select(Etudiant).where(Etudiant.id == etudiant_id)
    res = await db.execute(stmt)
    etudiant = res.scalar_one_or_none()
    if not etudiant:
        raise HTTPException(status_code=404, detail="Étudiant introuvable.")

    etudiant.session_id = payload.session_id
    if payload.filiere_id:
        etudiant.filiere_id = payload.filiere_id
    if payload.filiere:
        etudiant.filiere = payload.filiere
    if payload.niveau:
        etudiant.niveau = payload.niveau

    etudiant.statut = "Inscrit"
    await db.commit()
    await db.refresh(etudiant)
    return etudiant
