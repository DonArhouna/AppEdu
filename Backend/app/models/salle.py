"""
Modèle Salle : les lieux physiques où se donnent les cours.

Une salle existe enfin comme donnee. Jusqu'ici, ``cours.salle`` portait un
texte libre et deux cours pouvaient s'y retrouver le même créneau sans que
rien ne le signale — la salle n'était pas une donnée, donc le conflit
n'était pas detectable. Le rattachement d'un cours reste, pour l'instant,
une correspondance **par nom** (insensible à la casse) : aucune migration
ne reinterprete les cours existants.
"""

from typing import Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Salle(Base, TimestampMixin):
    __tablename__ = "salles"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    #: Ce que les cours citent. Unique : deux salles du même nom rendraient
    #: la correspondance cours ↔ salle ambigue.
    nom: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    #: Identifiant court d'affichage (planning, inventaire).
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    campus_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("campuses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    batiment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    etage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    capacite: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    #: Salle de classe, laboratoire, amphi, atelier... : une etiquette libre,
    #: l'institut nomme ses lieux comme il veut.
    type_salle: Mapped[str] = mapped_column(String(50), nullable=False, default="Salle de classe")
    equipements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    #: Une salle indisponible (travaux) refuse une nouvelle planification,
    #: sans que les cours deja poses ne disparaissent.
    disponible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    campus: Mapped[Optional["Campus"]] = relationship("Campus", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Salle code='{self.code}' nom='{self.nom}' capacite={self.capacite}>"
