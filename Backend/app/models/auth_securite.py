"""Modeles du durcissement d'authentification (lot 2).

Trois pieces :

- ``LoginAttempt``  : la trace de chaque tentative de connexion, reussie ou
  non. C'est la matiere premiere de l'enquete apres coup — une attaque par
  dictionnaire se voit dans la repetition d'emails tentes depuis une meme
  adresse, pas dans un compteur reinitialise a chaque reussite.
- ``RefreshToken``  : une session revoquable. La table conserve l'**empreinte**
  SHA-256 du jeton de rafraichissement, jamais le jeton lui-meme : une base
  interceptee ne doit pas contenir de quoi fabriquer une session valide.
- les colonnes de verrouillage de ``Utilisateur`` (``locked_until``,
  ``failed_login_count``), declarees dans ``utilisateur.py``.

Le refus de conserver le jeton en clair est la seule decision non negociable
du module. Une empreinte suffit a tout : la verification est une comparaison,
la rotation cree une nouvelle ligne, la revocation date la ligne existante.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LoginAttempt(Base):
    """Une tentative de connexion, reussie ou echouee.

    La ligne est ecrite **avant** la reponse : un attaquant qui martèle le
    endpoint ne doit jamais pouvoir deviner l'issue par la presence ou
    l'absence d'une trace. Les champs ``email`` et ``ip_address`` sont ceux
    **tentés** : l'email peut ne correspondre a aucun compte, c'est
    precisement ce qui interesse l'enquete.
    """

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="CURRENT_TIMESTAMP",
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    #: ``success`` ou ``failed`` — deux valeurs, pas une enumeration ouverte :
    #: un etat inattendu doit se lire comme une corruption, pas comme un
    #: troisieme etat metier.
    resultat: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_login_attempts_occurred_at", "occurred_at"),
        Index("ix_login_attempts_email", "email"),
    )


class RefreshToken(Base):
    """Une session revoquable : l'empreinte d'un jeton de rafraichissement.

    La table ne conserve **jamais** le jeton lui-meme, seulement son empreinte
    SHA-256. La rotation remplace l'empreinte active par une nouvelle a chaque
    rafraichissement ; rejouer une empreinte deja remplacee est le signal d'un
    vol potentiel, et l'unicite ne doit pas s'y opposer (une meme empreinte
    revoquee peut theoretiquement revenir) — c'est la surveillance qui juge.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Empreinte hexadecimale SHA-256 (64 caracteres). Pas le jeton.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: ``None`` tant que la session est vivante. Revoquer, c'est dater.
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    #: ``logout``, ``rotation`` ou ``admin`` — la raison se lit apres coup,
    #: elle ne decide de rien.
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index("ix_refresh_tokens_token_hash", "token_hash"),
        Index("ix_refresh_tokens_user_id", "user_id"),
    )


__all__ = ["LoginAttempt", "RefreshToken"]
