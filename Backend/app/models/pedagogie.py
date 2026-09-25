"""
Modèles Pédagogie :
- Cours : Séances de cours / emplois du temps
- Examen : Épreuves et contrôles continus
- Note : Notes obtenues par les étudiants
- Absence : Suivi des absences et assiduité
"""

from datetime import date, time
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, Date, Time, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Cours(Base, TimestampMixin):
    __tablename__ = "cours"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    matiere_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("matieres.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enseignant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    enseignant_nom: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    salle: Mapped[str] = mapped_column(String(50), nullable=False)
    jour_semaine: Mapped[str] = mapped_column(String(20), nullable=False)  # Lundi..Samedi
    heure_debut: Mapped[str] = mapped_column(String(10), nullable=False)   # "08:00"
    heure_fin: Mapped[str] = mapped_column(String(10), nullable=False)     # "10:00"
    type_cours: Mapped[str] = mapped_column(String(20), nullable=False)  # CM, TD, TP

    matiere: Mapped["Matiere"] = relationship("Matiere", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Cours {self.jour_semaine} {self.heure_debut}-{self.heure_fin} salle='{self.salle}'>"


class Examen(Base, TimestampMixin):
    __tablename__ = "examens"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("sessions_academiques.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matiere_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("matieres.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type_examen: Mapped[str] = mapped_column(String(50), nullable=False, default="Examen Final")  # CC, Partiel, Examen Final, Rattrapage
    date_examen: Mapped[date] = mapped_column(Date, nullable=False)
    duree_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    coefficient: Mapped[float] = mapped_column(Float, nullable=False)

    matiere: Mapped["Matiere"] = relationship("Matiere", lazy="selectin")
    session: Mapped["SessionAcademique"] = relationship("SessionAcademique", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Examen '{self.nom}' date={self.date_examen}>"


class Note(Base, TimestampMixin):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    etudiant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matiere_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("matieres.id", ondelete="CASCADE"), nullable=False, index=True
    )
    examen_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("examens.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("sessions_academiques.id", ondelete="SET NULL"), nullable=True, index=True
    )
    valeur: Mapped[float] = mapped_column(Float, nullable=False)  # Note sur 20
    coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    appreciation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    statut: Mapped[str] = mapped_column(String(30), nullable=False, default="Validé")  # Validé, Rattrapage
    saisi_par_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )

    etudiant: Mapped["Etudiant"] = relationship("Etudiant", lazy="selectin")
    matiere: Mapped["Matiere"] = relationship("Matiere", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Note etudiant='{self.etudiant_id}' note={self.valeur}/20>"


class Absence(Base, TimestampMixin):
    __tablename__ = "absences"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    etudiant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("etudiants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cours_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("cours.id", ondelete="SET NULL"), nullable=True, index=True
    )
    matiere_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("matieres.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("sessions_academiques.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date_absence: Mapped[date] = mapped_column(Date, nullable=False)
    duree_heures: Mapped[float] = mapped_column(Float, nullable=False)
    justifiee: Mapped[bool] = mapped_column(Boolean, nullable=False)
    motif: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    etudiant: Mapped["Etudiant"] = relationship("Etudiant", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Absence etudiant='{self.etudiant_id}' date={self.date_absence} justifiee={self.justifiee}>"
