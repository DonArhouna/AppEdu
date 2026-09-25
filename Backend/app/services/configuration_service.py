"""Service de la configuration institutionnelle versionnee.

Toute ecriture passe par : lire la configuration courante, comparer champ par
champ, n'ecrire que si quelque chose change, et produire une version.

Deux garanties :

- **Une version n'est creee que s'il y a un changement reel.** Enregistrer un
  formulaire sans modifier un champ ne doit pas polluer l'historique : sinon
  l'historique devient illisible et la version affichee ne veut plus rien dire.
- **La numerotation est reservee sous verrou.** Deux administrateurs qui
  enregistrent en meme temps ne peuvent pas obtenir le meme numero, ni ecrire
  deux fois le meme numero.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration import ConfigurationVersion
from app.models.etablissement import Etablissement
from app.models.utilisateur import Utilisateur
from app.services import branding_service

#: Verrou consultatif : serialize la reservation du numero de version.
_LOCK_CONFIGURATION_ID = 7_310_024_002

#: Champs d'identite compares pour detecter un changement.
CHAMPS_IDENTITE = ("nom", "sigle", "adresse", "telephone", "email", "pays", "devise")

#: Libelles lisibles pour l'historique : la cle est technique, l'affichage ne
#: l'est pas.
LIBELLES: Dict[str, str] = {
    "nom": "Nom de l'etablissement",
    "sigle": "Sigle",
    "adresse": "Adresse",
    "telephone": "Telephone",
    "email": "Courriel",
    "pays": "Pays",
    "devise": "Devise",
}


async def _verrouiller(db: AsyncSession) -> None:
    """Serialise la reservation du numero de version (PostgreSQL)."""

    if db.get_bind().dialect.name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _LOCK_CONFIGURATION_ID},
        )


async def charger_etablissement(db: AsyncSession) -> Etablissement:
    """Etablissement configure. Sa absence est un defaut d'installation."""

    etablissement = (await db.execute(select(Etablissement).limit(1))).scalars().first()
    if etablissement is None:
        raise LookupError(
            "Aucun etablissement configure. Terminez l'installation avant de "
            "modifier la configuration."
        )
    return etablissement


def instantane(etablissement: Etablissement) -> Dict[str, Any]:
    """Etat complet et serialisable de la configuration."""

    return {
        "nom": etablissement.nom,
        "sigle": etablissement.sigle,
        "adresse": etablissement.adresse,
        "telephone": etablissement.telephone,
        "email": etablissement.email,
        "pays": etablissement.pays,
        "devise": etablissement.devise,
        "logo_url": etablissement.logo_url,
    }


async def version_courante(db: AsyncSession, etablissement_id: str) -> int:
    """Derniere version enregistree (0 si aucune ecriture depuis l'install)."""

    sommet = await db.execute(
        select(func.max(ConfigurationVersion.version)).where(
            ConfigurationVersion.etablissement_id == etablissement_id
        )
    )
    return int(sommet.scalar() or 0)


async def enregistrer_version(
    db: AsyncSession,
    etablissement: Etablissement,
    *,
    nature: str,
    modifications: Dict[str, Any],
    auteur: Optional[Utilisateur],
) -> ConfigurationVersion:
    """Cree la version suivante. A appeler apres avoir flush l'etablissement.

    L'instantane est pris apres l'ecriture des attributs, sinon l'historique
    enregistrerait l'etat d'avant.
    """

    await _verrouiller(db)
    await db.flush()

    version = ConfigurationVersion(
        id=str(uuid.uuid4()),
        etablissement_id=etablissement.id,
        version=await version_courante(db, etablissement.id) + 1,
        nature=nature,
        modifications=modifications,
        instantane=instantane(etablissement),
        logo_present=bool(etablissement.logo_url),
        modifie_par_id=auteur.id if auteur else None,
        modifie_par_email=auteur.email if auteur else None,
    )
    db.add(version)
    await db.flush()
    return version


def comparer(
    etablissement: Etablissement, changement: Dict[str, Any]
) -> Dict[str, Any]:
    """Champs dont la valeur reellement change, avec l'ancienne valeur.

    La comparaison est faite sur la valeur normalisee (chaines sans espaces
    de bord), pas sur l'egalite brute : passer de ``"XOF"`` a ``" XOF "`` n'est
    pas un changement de configuration.
    """

    modifications: Dict[str, Any] = {}
    for champ, nouvelle in changement.items():
        if champ not in CHAMPS_IDENTITE or nouvelle is None:
            continue
        avant = getattr(etablissement, champ, None)
        if isinstance(avant, str) and isinstance(nouvelle, str):
            identique = avant.strip() == nouvelle.strip()
        else:
            identique = avant == nouvelle
        if not identique:
            modifications[champ] = {"avant": avant, "apres": nouvelle}
    return modifications


async def historique(
    db: AsyncSession, etablissement_id: str, limite: int = 50
) -> List[ConfigurationVersion]:
    """Versions les plus recentes d'abord."""

    stmt = (
        select(ConfigurationVersion)
        .where(ConfigurationVersion.etablissement_id == etablissement_id)
        .order_by(ConfigurationVersion.version.desc())
        .limit(limite)
    )
    return list((await db.execute(stmt)).scalars().all())


def libelle_changement(corps: Dict[str, Any]) -> str:
    """Resume lisible d'une version, pour l'affichage."""

    if not corps:
        return "Configuration enregistree"
    noms = [LIBELLES.get(champ, champ) for champ in corps]
    if len(noms) == 1:
        return noms[0]
    if len(noms) == 2:
        return f"{noms[0]} et {noms[1]}"
    return f"{', '.join(noms[:-1])} et {noms[-1]}"
