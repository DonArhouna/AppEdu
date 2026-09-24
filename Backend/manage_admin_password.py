"""Réinitialisation interactive et sécurisée du mot de passe administrateur.

Usage:
    python manage_admin_password.py --email admin@votre-etablissement.org

Le mot de passe n'est jamais lu depuis un argument, un fichier ou une variable
d'environnement. Il est demandé deux fois avec getpass.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import get_password_hash
from app.models.utilisateur import Utilisateur, UserRole


async def reset_password(email: str) -> int:
    password = getpass.getpass("Nouveau mot de passe administrateur : ")
    confirmation = getpass.getpass("Confirmation : ")
    if password != confirmation:
        raise SystemExit("Les mots de passe ne correspondent pas.")
    if len(password) < 12:
        raise SystemExit("Le mot de passe doit contenir au moins 12 caractères.")

    async with async_session_factory() as session:
        result = await session.execute(
            select(Utilisateur).where(
                Utilisateur.email == email.strip().lower(),
                Utilisateur.role == UserRole.ADMIN.value,
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise SystemExit("Aucun administrateur actif trouvé pour cet email.")

        user.hashed_password = get_password_hash(password)
        await session.commit()
        print(f"Mot de passe mis à jour pour {user.email}.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Modifier le mot de passe d'un administrateur")
    parser.add_argument("--email", required=True, help="Email du compte administrateur")
    args = parser.parse_args()
    try:
        return asyncio.run(reset_password(args.email))
    except KeyboardInterrupt:
        print("\nOpération annulée.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
