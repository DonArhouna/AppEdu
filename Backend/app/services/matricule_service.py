"""
Service de génération automatique des matricules étudiants.
Format paramétrable : {ANNEE}-{CODE_FILIERE}-{SEQUENCE:04d}
Exemple : 2026-GL-0001
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.etudiant import Etudiant


async def generate_matricule(db: AsyncSession, filiere_code: str = "GEN", annee: int = None) -> str:
    """
    Génère un matricule unique pour un étudiant.
    Ex: 2026-GL-0001
    """
    if not annee:
        annee = datetime.now().year

    clean_code = (filiere_code or "GEN").upper().strip()
    prefix = f"{annee}-{clean_code}-"

    # Compter le nombre d'étudiants ayant ce préfixe
    stmt = select(func.count(Etudiant.id)).where(Etudiant.matricule.like(f"{prefix}%"))
    result = await db.execute(stmt)
    count = result.scalar() or 0

    sequence = count + 1
    return f"{prefix}{sequence:04d}"
