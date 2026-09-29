"""
CLI de provisioning multi-tenant (lot 6) — l'outillage d'exploitation.

**Pourquoi une CLI et pas des endpoints ?** Créer une base et appliquer
des migrations est une opération synchrone (Alembic) qui ne doit jamais
tourner dans la boucle d'événements du serveur, et une opération qui
mérite une trace humaine : elle se lance depuis la machine d'exploitation,
avec le même ``.env`` que le serveur.

Usage (depuis ``Backend/``) :

    .\\venv\\Scripts\\python.exe -m app.provisioning creer isi "Institut ISI" --email contact@isi.org
    .\\venv\\Scripts\\python.exe -m app.provisioning lister
    .\\venv\\Scripts\\python.exe -m app.provisioning migrer-tous
    .\\venv\\Scripts\\python.exe -m app.provisioning suspendre isi
    .\\venv\\Scripts\\python.exe -m app.provisioning reactiver isi
    .\\venv\\Scripts\\python.exe -m app.provisioning resilier isi

Chaque commande vit dans **sa propre** boucle ``asyncio.run()`` ; les
connexions passent donc par des moteurs jetables (_session_dediee),
jamais par la fabrique globale du serveur.

``creer`` fabrique ``emp_tenant_{slug}`` sur le serveur PostgreSQL de
``.env``, y applique **toutes** les migrations, puis inscrit l'école au
registre (base de contrôle). Le directeur crée ensuite son compte admin
par le Setup Wizard habituel — la même route que votre client on-premise :
un seul parcours, zéro différence.
"""

import argparse
import asyncio
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from sqlalchemy import text

from app.core.config import settings
from app.models.tenant import TENANT_ACTIF, TENANT_RESILIEE, TENANT_SUSPENDUE
from app.services.tenant_dto import TenantDetail
from app.services.tenant_service import TenantInvalide, slug_valide, url_base_tenant


@asynccontextmanager
async def _session_dediee(url: Optional[str] = None):
    """Ouvre une session sur un moteur jetable, propre à cette commande.

    La fabrique globale (``async_session_factory``) met ses connexions en
    pool, attachées à la boucle qui les a créées : chaîner plusieurs
    ``asyncio.run()`` — comme le fait cette CLI — réutiliserait des
    connexions d'une boucle déjà fermée (« Event loop is closed »). Chaque
    phase crée donc son moteur, puis le dispose proprement.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    moteur = create_async_engine(url or settings.DATABASE_URL, pool_pre_ping=True)
    fabrique = async_sessionmaker(bind=moteur, expire_on_commit=False, autoflush=False)
    try:
        async with fabrique() as session:
            yield session
    finally:
        await moteur.dispose()


def _migrer_base(url: str) -> None:
    """Applique les migrations jusqu'à ``head`` sur une base — processus dédié."""
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    ancienne = settings.DATABASE_URL
    settings.DATABASE_URL = url
    try:
        command.upgrade(config, "head")
    finally:
        settings.DATABASE_URL = ancienne


async def _base_existe(slug: str) -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine

    admin_url = settings.DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    engine = create_async_engine(admin_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            resultat = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :nom"),
                {"nom": f"emp_tenant_{slug}"},
            )
            return resultat.first() is not None
    finally:
        await engine.dispose()


async def _creer_base(slug: str) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    admin_url = settings.DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f'CREATE DATABASE "emp_tenant_{slug}"'))
    finally:
        await engine.dispose()


def creer(
    slug: str,
    nom: str,
    email: Optional[str] = None,
    plan: str = "standard",
    abonnement: Optional[date] = None,
) -> None:
    """Crée la base de l'école, la migre, puis l'inscrit au registre.

    L'ordre : base physique → migrations → registre. Une base prête sans
    ligne de registre n'est qu'un retry sans conséquence ; l'inverse serait
    une école annoncée et injoignable.
    """
    if not slug_valide(slug):
        raise TenantInvalide(
            f"Slug invalide : « {slug} ». Minuscules, chiffres, tirets et "
            "soulignés uniquement, 50 caractères maximum."
        )

    async def _verifier_registre() -> bool:
        from sqlalchemy import select

        from app.models.tenant import Tenant

        async with _session_dediee() as db:
            existe = (
                await db.execute(
                    select(Tenant.id).where(Tenant.slug == slug)
                )
            ).first()
        return existe is not None

    if asyncio.run(_verifier_registre()):
        raise TenantInvalide(f"Un tenant avec le slug « {slug} » existe déjà.")

    deja_la = asyncio.run(_base_existe(slug))
    if deja_la:
        print(f"Base emp_tenant_{slug} déjà présente : migrations seules.")
    else:
        print(f"Création de la base emp_tenant_{slug}...")
        asyncio.run(_creer_base(slug))

    print("Application des migrations (alembic upgrade head)...")
    _migrer_base(url_base_tenant(slug))

    async def _inscrire() -> str:
        from app.models.tenant import Tenant

        async with _session_dediee() as db:
            tenant = Tenant(
                id=str(uuid.uuid4()),
                slug=slug,
                nom=nom,
                statut=TENANT_ACTIF,
                plan=plan,
                abonnement_jusquau=abonnement,
                contact_email=email,
            )
            db.add(tenant)
            await db.commit()
            return tenant.id

    tenant_id = asyncio.run(_inscrire())
    print(f"École inscrite au registre ({tenant_id[:8]}).")
    print(
        f"Terminé : {nom} → X-Tenant-ID: {slug} (base emp_tenant_{slug}).\n"
        "Le directeur crée son compte admin par le Setup Wizard habituel."
    )


def lister() -> None:
    async def _lister() -> None:
        from app.services.tenant_service import lister as service_lister

        async with _session_dediee() as db:
            tenants = await service_lister(db)
        if not tenants:
            print("Registre vide : aucune école provisionnée.")
            return
        print(f"{'slug':<20} {'statut':<11} {'plan':<10} nom")
        for tenant in tenants:
            print(
                f"{tenant.slug:<20} {tenant.statut:<11} {tenant.plan:<10} {tenant.nom}"
            )

    asyncio.run(_lister())


def migrer_tous() -> None:
    """Applique les migrations à toutes les bases d'écoles (hors résiliées)."""

    async def _slugs() -> list:
        from sqlalchemy import select

        from app.models.tenant import Tenant

        async with _session_dediee() as db:
            lignes = (
                await db.execute(
                    select(Tenant.slug).where(Tenant.statut != TENANT_RESILIEE).order_by(Tenant.slug)
                )
            ).all()
        return [ligne[0] for ligne in lignes]

    slugs = asyncio.run(_slugs())
    if not slugs:
        print("Aucune école à migrer.")
        return
    echecs = []
    for slug in slugs:
        print(f"Migration de emp_tenant_{slug}...")
        try:
            _migrer_base(url_base_tenant(slug))
        except Exception as exc:
            print(f"  ÉCHEC : {exc}")
            echecs.append(slug)
    if echecs:
        print(f"Terminé avec {len(echecs)} échec(s) : {', '.join(echecs)}")
        sys.exit(1)
    print(f"Terminé : {len(slugs)} base(s) migrée(s) jusqu'à head.")


def _changer_statut(slug: str, statut: str, libelle: str) -> None:
    async def _faire() -> None:
        from app.services.tenant_service import changer_statut as service_changer

        async with _session_dediee() as db:
            tenant = await service_changer(db, slug, statut)
        print(f"{tenant.nom} → {libelle}.")

    asyncio.run(_faire())


def suspendre(slug: str) -> None:
    _changer_statut(slug, TENANT_SUSPENDUE, "suspendue (accès fermé)")


def reactiver(slug: str) -> None:
    _changer_statut(slug, TENANT_ACTIF, "réactivée")


def resilier(slug: str) -> None:
    _changer_statut(slug, TENANT_RESILIEE, "résiliée (données conservées, accès fermé)")


def main() -> None:
    # Consoles Windows (cp1252) : sans cela, un simple « → » dans un
    # message lève UnicodeEncodeError — après que le travail est fait.
    for flux in (sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8", errors="replace")

    parseur = argparse.ArgumentParser(description="Provisionnement multi-tenant EduManagePro")
    sous = parseur.add_subparsers(dest="commande", required=True)

    p_creer = sous.add_parser("creer", help="Créer une école (base + migrations + registre)")
    p_creer.add_argument("slug")
    p_creer.add_argument("nom")
    p_creer.add_argument("--email", default=None)
    p_creer.add_argument("--plan", default="standard")
    p_creer.add_argument("--abonnement", type=date.fromisoformat, default=None)

    sous.add_parser("lister", help="Lister les écoles du registre")
    sous.add_parser("migrer-tous", help="Appliquer les migrations à toutes les bases")

    for nom_commande, libelle in (
        ("suspendre", "Fermer l'accès (impayé)"),
        ("reactiver", "Rétablir l'accès"),
        ("resilier", "Fermer définitivement (données conservées)"),
    ):
        p = sous.add_parser(nom_commande, help=libelle)
        p.add_argument("slug")

    arguments = parseur.parse_args()
    try:
        if arguments.commande == "creer":
            creer(
                arguments.slug,
                arguments.nom,
                email=arguments.email,
                plan=arguments.plan,
                abonnement=arguments.abonnement,
            )
        elif arguments.commande == "lister":
            lister()
        elif arguments.commande == "migrer-tous":
            migrer_tous()
        elif arguments.commande == "suspendre":
            suspendre(arguments.slug)
        elif arguments.commande == "reactiver":
            reactiver(arguments.slug)
        elif arguments.commande == "resilier":
            resilier(arguments.slug)
    except TenantInvalide as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
