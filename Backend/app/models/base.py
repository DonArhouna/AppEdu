"""
Modèle socle DeclarativeBase SQLAlchemy 2.0 avec colonnes de traçabilité automatique.
"""

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles ORM."""
    pass


class TimestampMixin:
    """Mixin ajoutant created_at et updated_at avec fuseau horaire."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
