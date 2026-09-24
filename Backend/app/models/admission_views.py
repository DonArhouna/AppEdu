"""Vues de filtres enregistrées pour le registre des admissions."""

from typing import Any, Dict

from sqlalchemy import ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class VueAdmissions(Base, TimestampMixin):
    __tablename__ = "vues_admissions"
    __table_args__ = (
        UniqueConstraint("user_id", "nom", name="uq_vues_admissions_user_nom"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    filtres: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped["Utilisateur"] = relationship("Utilisateur", lazy="selectin")

    def __repr__(self) -> str:
        return f"<VueAdmissions id={self.id!r} nom={self.nom!r}>"
