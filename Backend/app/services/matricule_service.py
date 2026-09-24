"""
Service de génération automatique des matricules étudiants.
Format paramétrable : {ANNEE}-{CODE_FILIERE}-{SEQUENCE:04d}
Exemple : 2026-GL-0001
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.etudiant import Etudiant


async def generate_matricule(db: AsyncSession, filiere_code: str, annee: int = None) -> str:
    """
    Génère un matricule unique pour un étudiant.
    Ex: 2026-GL-0001
    """
    if not annee:
        annee = datetime.now().year

    clean_code = filiere_code.upper().strip()
    if not clean_code:
        raise ValueError("Un code de filière est requis pour générer un matricule.")
    prefix = f"{annee}-{clean_code}-"

    # Un simple count est insuffisant : une suppression ou une reprise de
    # données peut laisser un trou dans la séquence. On recherche donc le
    # premier numéro réellement libre.
    stmt = select(Etudiant.matricule).where(Etudiant.matricule.like(f"{prefix}%"))
    result = await db.execute(stmt)
    used = {str(value) for value in result.scalars().all()}

    sequence = 1
    while f"{prefix}{sequence:04d}" in used:
        sequence += 1
    return f"{prefix}{sequence:04d}"
