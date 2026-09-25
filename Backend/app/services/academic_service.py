"""Services métier partagés par le socle académique.

Les fonctions de ce module ne font pas de commit implicite : elles
s'exécutent dans la transaction de l'endpoint appelant.  Cela permet aux
parcours Étudiant/Candidature de rester atomiques.
"""

from datetime import date
from typing import Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import Classe, Inscription, Niveau
from app.models.session_academique import SessionAcademique
from app.models.structure import Filiere


async def get_classe(db: AsyncSession, classe_id: str) -> Optional[Classe]:
    """Charge une classe et les résumés nécessaires à sa projections."""
    result = await db.execute(
        select(Classe)
        .options(
            selectinload(Classe.filiere),
            selectinload(Classe.niveau).selectinload(Niveau.cycle),
        )
        .where(Classe.id == classe_id)
    )
    return result.scalar_one_or_none()


async def get_niveau(db: AsyncSession, niveau_id: str) -> Optional[Niveau]:
    result = await db.execute(
        select(Niveau)
        .options(selectinload(Niveau.cycle))
        .where(Niveau.id == niveau_id)
    )
    return result.scalar_one_or_none()


async def get_filiere(db: AsyncSession, filiere_id: str) -> Optional[Filiere]:
    return await db.get(Filiere, filiere_id)


async def get_session(db: AsyncSession, session_id: str) -> Optional[SessionAcademique]:
    return await db.get(SessionAcademique, session_id)


async def get_classe_and_session(
    db: AsyncSession,
    classe_id: str,
    session_id: str,
) -> Tuple[Optional[Classe], Optional[SessionAcademique]]:
    """Charge les deux références; l'endpoint transforme l'absence en 422/404."""
    classe = await get_classe(db, classe_id)
    session = await get_session(db, session_id)
    return classe, session


def class_projections(classe: Classe) -> dict[str, str]:
    """Retourne les projections legacy derives d'une classe.

    Le niveau est stocké avec son nom metier lorsqu'il est disponible.  Pour
    le modèle LMD, ``code`` reste la valeur normalisée (``L1``/``M1``) et
    ``nom`` reste le libellé historique exploitable par les anciens modules.
    """
    filiere = classe.filiere
    niveau = classe.niveau
    return {
        "filiere_id": filiere.id,
        "filiere": filiere.nom,
        "niveau": niveau.nom or niveau.code,
    }


async def find_active_inscription(
    db: AsyncSession,
    *,
    etudiant_id: str,
    session_id: str,
) -> Optional[Inscription]:
    result = await db.execute(
        select(Inscription)
        .options(
            selectinload(Inscription.etudiant),
            selectinload(Inscription.classe)
            .selectinload(Classe.filiere),
            selectinload(Inscription.classe)
            .selectinload(Classe.niveau)
            .selectinload(Niveau.cycle),
            selectinload(Inscription.session).selectinload(SessionAcademique.periodes),
        )
        .where(
            Inscription.etudiant_id == etudiant_id,
            Inscription.session_id == session_id,
            Inscription.actif.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def sync_active_inscription(
    db: AsyncSession,
    *,
    etudiant_id: str,
    classe_id: str,
    session_id: str,
    date_inscription: Optional[date] = None,
) -> Tuple[Inscription, bool]:
    """Crée ou met à jour l'inscription active du triplet demandé.

    Une ligne inactive n'est jamais réutilisée : elle reste une trace et une
    nouvelle ligne active est créée.  Une ligne active déjà présente pour la
    même classe est conservée afin de rendre les appels répétés idempotents.
    Si la classe change pendant la même session, l'ancienne ligne estFermée
    avec le statut ``remplacee`` afin de ne jamais réécrire l'historique.
    """
    existing = await find_active_inscription(
        db, etudiant_id=etudiant_id, session_id=session_id
    )
    if existing is not None:
        if existing.classe_id == classe_id:
            return existing, False
        existing.actif = False
        existing.statut = "remplacee"
        await db.flush()

    inscription = Inscription(
        id=str(uuid.uuid4()),
        etudiant_id=etudiant_id,
        classe_id=classe_id,
        session_id=session_id,
        actif=True,
        statut="active",
        date_inscription=date_inscription or date.today(),
    )
    db.add(inscription)
    await db.flush()
    return inscription, True


async def load_inscription(db: AsyncSession, inscription_id: str) -> Optional[Inscription]:
    result = await db.execute(
        select(Inscription)
        .options(
            selectinload(Inscription.etudiant),
            selectinload(Inscription.classe).selectinload(Classe.filiere),
            selectinload(Inscription.classe)
            .selectinload(Classe.niveau)
            .selectinload(Niveau.cycle),
            selectinload(Inscription.session).selectinload(SessionAcademique.periodes),
        )
        .where(Inscription.id == inscription_id)
    )
    return result.scalar_one_or_none()


__all__ = [
    "get_classe",
    "get_niveau",
    "get_filiere",
    "get_session",
    "get_classe_and_session",
    "class_projections",
    "find_active_inscription",
    "sync_active_inscription",
    "load_inscription",
]
