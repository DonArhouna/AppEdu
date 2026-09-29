"""Anti-brute-force et sessions revocables : la logique, pas les endpoints.

Ce module porte les deux defenses du lot 2, et ne decide d'aucune reponse
HTTP : les endpoints traduisent, le service juge.

**Le login se defend par paliers.**  Trois questions, dans l'ordre :

1. le compte est-il **verrouille** ? Le verrou suit le compte, pas l'adresse
   qui tente de se connecter en son nom : un attaquant distribue ses requetes
   sur des IP, jamais sur les comptes qu'il vise. La duree du verrou est un
   reglage, pas une sentence : elle expire toute seule ;
2. le mot de passe est-il bon ? Aucune reponse avant d'avoir consulte la
   base : repondre « compte verrouille » a un mauvais mot de passe dirait a
   l'attaquant qu'il a trouve le bon compte ;
3. l'echec est-il **consecutif** au seuil ? Le compteur remonte a la
   reussite ; franchir le seuil pose le verrou.

**Une session est une ligne qu'on peut dater.**  Le jeton de rafraichissement
n'est jamais conserve — son empreinte SHA-256 suffit — et l'access token ne
vaut que si la ligne qui l'a emis est toujours vivante. La rotation a chaque
``/auth/refresh`` remplace l'empreinte : rejouer une ancienne empreinte est
refuse et **revoque la famille** (les autres sessions du compte) — c'est le
signal standard d'un vol de jeton, et la seule parade utile est la fermeture.

La rotation detecte le rejeu **avant** d'echouer proprement : la session
rejouee est revoquee avec la raison ``rotation``, et les autres sessions
actives du compte sont fermees avec la raison ``fuite``. Un utilisateur legitime
a perdu une session ; un attaquant a perdu les siennes.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.models.auth_securite import LoginAttempt, RefreshToken
from app.models.utilisateur import Utilisateur


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _vers_utc(valeur: datetime) -> datetime:
    """Compare une echeance lue en base a l'horloge, sans exception.

    PostgreSQL rend des datetimes **conscients** du fuseau (colonne
    ``timestamptz``) ; SQLite rend des **naifs** — la colonne conserve les
    octets, pas le fuseau. Comparer les deux leve ``TypeError``. La
    normalisation lit la base, decide le fuseau : une heure stockee naive
    EST une heure UTC (c'est ainsi que le serveur l'a ecrite).
    """
    if valeur.tzinfo is None:
        return valeur.replace(tzinfo=timezone.utc)
    return valeur


def _expire(echeance: datetime) -> bool:
    """L'echeance (normalizee) est-elle passee ?"""
    return _vers_utc(echeance) <= _maintenant()


def empreinte(jeton: str) -> str:
    """L'empreinte SHA-256 hexadecimale du jeton. Pas le jeton."""
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def ip_de_requete(requete) -> Optional[str]:
    """L'adresse client, derriere un eventuel proxy de confiance.

    Derriere un reverse-proxy, ``client.host`` vaudrait l'adresse du proxy :
    toutes les attaques partageraient alors une seule IP imaginaire, et le
    taux par adresse deviendrait un verrou global — pire que rien. Le header
    ``X-Forwarded-For`` n'est lu que si l'instance se declare derriere un
    proxy ; sinon il est ignore, parce qu'un client le fabrique en une ligne.
    """
    if not getattr(settings, "TRUST_PROXY_HEADERS", False):
        return requete.client.host if requete and requete.client else None
    forwarded = requete.headers.get("x-forwarded-for") if requete else None
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return requete.client.host if requete and requete.client else None


# ---------------------------------------------------------------------------
# 1. Anti-brute-force
# ---------------------------------------------------------------------------
class CompteVerrouille(Exception):
    """Le compte est verrouille jusqu'a une date, connue du porteur."""

    def __init__(self, jusqu_a: datetime):
        self.jusqu_a = jusqu_a
        restant = max(0, int((jusqu_a - _maintenant()).total_seconds()))
        minutes = max(1, restant // 60 + (1 if restant % 60 else 0))
        super().__init__(
            f"Compte temporairement verrouillé après trop d'échecs de "
            f"connexion. Réessayez dans environ {minutes} minute(s)."
        )


async def tracer_tentative(
    db: AsyncSession,
    *,
    email: str,
    ip: Optional[str],
    resultat: str,
    user_id: Optional[int] = None,
) -> None:
    """Ecrit la trace de la tentative. La ligne precede la reponse."""
    db.add(
        LoginAttempt(
            email=email,
            ip_address=ip,
            resultat=resultat,
            user_id=user_id,
        )
    )


async def compte_verrouille(
    db: AsyncSession, utilisateur: Utilisateur
) -> Optional[datetime]:
    """La date de deverrouillage si le compte est sous verrou vivant, sinon None."""
    if utilisateur.locked_until is None:
        return None
    if _expire(utilisateur.locked_until):
        # Le verrou a expire : il ne reprime plus personne. Le compteur
        # repart de zero — le verrou a deja servi de punition.
        utilisateur.locked_until = None
        utilisateur.failed_login_count = 0
        return None
    return utilisateur.locked_until


async def enregistrer_echec(db: AsyncSession, utilisateur: Utilisateur) -> None:
    """Compte un echec consecutif, et verrouille au seuil.

    Le compteur ne compte pas la vie du compte : il compte la **serie**.
    Une reussite le remet a zero (voir ``enregistrer_succes``), une heure de
    verrou expire le remet a zero aussi.
    """
    utilisateur.failed_login_count = (utilisateur.failed_login_count or 0) + 1
    if utilisateur.failed_login_count >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
        utilisateur.locked_until = _maintenant() + timedelta(
            minutes=settings.LOGIN_LOCKOUT_MINUTES
        )
        # Le verrou est la punition du seuil franchi ; le compteur repartira
        # a son expiration (voir ``compte_verrouille``).


async def enregistrer_succes(db: AsyncSession, utilisateur: Utilisateur) -> None:
    """Une reussite efface la serie d'echecs : le compte repart propre."""
    utilisateur.failed_login_count = 0
    utilisateur.locked_until = None


def nouveau_jeton_refresh() -> str:
    """Un jeton opaque, aleatoire, sans information exploitable."""
    return secrets.token_urlsafe(48)


async def emettre_session(
    db: AsyncSession, *, utilisateur: Utilisateur
) -> tuple[str, datetime, str]:
    """Cree une session (ligne) et rend ``(jeton, expiration, id_session)``.

    La ligne est ajoutee a la transaction de l'appelant : pas de commit ici,
    l'endpoint garde la main sur l'atomicite de la reponse. L'identifiant de
    session est repris dans le claim ``sid`` de l'access token : c'est lui
    qui permet de refuser un access token dont la session a ete revoquee,
    et d'indiquer a l'ecran quelle ligne est « cette » machine.
    """
    jeton = nouveau_jeton_refresh()
    expiration = _maintenant() + timedelta(
        minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
    )
    id_session = str(uuid.uuid4())
    db.add(
        RefreshToken(
            id=id_session,
            user_id=utilisateur.id,
            token_hash=empreinte(jeton),
            expires_at=expiration,
            created_at=_maintenant(),
        )
    )
    return jeton, expiration, id_session


async def session_active_par_jeton(
    db: AsyncSession, jeton: str
) -> Optional[RefreshToken]:
    """La ligne de session vivante pour ce jeton, sinon None.

    Vivante : non revoquee, non expiree. Le jeton presente n'existe pas ou
    plus — meme raison, meme reponse : on ne dit jamais si la session a
    existe, un attaquant n'en tirerait qu'une confirmation.
    """
    ligne = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == empreinte(jeton)
            )
        )
    ).scalars().first()
    if ligne is None or ligne.revoked_at is not None:
        return None
    if _expire(ligne.expires_at):
        return None
    return ligne


class JetonInvalide(Exception):
    """Le jeton presente n'ouvre aucune session : inconnu, expire ou revoque.

    Une seule exception pour trois causes : la reponse ne dit jamais laquelle.
    Un attaquant qui sondere les jetons n'en tirerait qu'un oracle de
    validite, exactement ce que le flou empeche.
    """


class RejeuDetecte(Exception):
    """Un jeton deja tourne vient d'etre rejoue : signature d'un vol.

    L'attaquant et le legitimate portent le meme jeton ; le serveur ne peut
    pas les departager, et ne le doit pas — il ferme la famille entiere.
    L'utilisateur legitime se reconnecte ; l'attaquant perd ce qu'il avait
    intercepte. C'est la seule reponse utile quand on ne peut pas trancher.
    """

    def __init__(self, sessions_fermees: int):
        self.sessions_fermees = sessions_fermees
        super().__init__(
            "Jeton de rafraîchissement déjà utilisé : les sessions actives "
            "du compte ont été fermées par précaution. Reconnectez-vous."
        )


async def rafraichir_session(
    db: AsyncSession, *, jeton: str
) -> tuple[Utilisateur, str, datetime, str]:
    """Tourne une session vivante : ``(utilisateur, nouveau_jeton, expiration, id)``.

    La rotation remplace l'empreinte active : l'ancienne ligne reste en base
    datee ``rotation``, la nouvelle recupere une echeance pleine. Rejouer un
    jeton tourne declenche ``RejeuDetecte`` — et la fermeture des autres
    sessions du compte, dans la meme transaction que le refus.
    """
    ligne = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == empreinte(jeton))
        )
    ).scalars().first()

    if ligne is not None and ligne.revoked_at is not None:
        if ligne.revoked_reason == "rotation":
            # Rejouer une empreinte que la rotation a remplacee : le jeton
            # circule donc entre au moins deux porteurs. Fermer la famille
            # est le seul geste qui protege les deux.
            fermees = await revoquer_famille(db, ligne.user_id)
            raise RejeuDetecte(fermees)
        raise JetonInvalide()

    if ligne is None or _expire(ligne.expires_at):
        raise JetonInvalide()

    utilisateur = await db.get(Utilisateur, ligne.user_id)
    if utilisateur is None or not utilisateur.is_active:
        # Un compte desactive ne rafraichit pas : la session meurt ici, et
        # la raison le dit — l'enquete apres coup saura pourquoi.
        ligne.revoked_at = _maintenant()
        ligne.revoked_reason = "compte_inactif"
        raise JetonInvalide()

    ligne.revoked_at = _maintenant()
    ligne.revoked_reason = "rotation"
    ligne.last_used_at = _maintenant()
    nouveau, expiration, id_session = await emettre_session(
        db, utilisateur=utilisateur
    )
    return utilisateur, nouveau, expiration, id_session


async def revoquer_famille(db: AsyncSession, utilisateur_id: int) -> int:
    """Revoque les autres sessions actives du compte (signal de vol)."""
    resultat = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == utilisateur_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=_maintenant(), revoked_reason="fuite")
    )
    return int(resultat.rowcount or 0)


async def revoquer_jeton(db: AsyncSession, jeton: str) -> bool:
    """Revoque la session designee par le jeton. Revoquer deux fois ne fait rien."""
    ligne = await session_active_par_jeton(db, jeton)
    if ligne is None:
        return False
    ligne.revoked_at = _maintenant()
    ligne.revoked_reason = "logout"
    return True


def session_id_du_jeton(jeton: Optional[str]) -> Optional[str]:
    """Le claim ``sid`` d'un access token, sans le valider.

    Pour l'affichage « cette machine » : on ne consulte pas la base ici, on
    lit seulement le jeton que le client vient de presenter. Un jeton
    illisible ne designe aucune session.
    """
    if not jeton:
        return None
    payload = decode_access_token(jeton)
    if not payload:
        return None
    return payload.get("sid")


async def revoquer_session_par_id(
    db: AsyncSession, utilisateur_id: int, session_id: str
) -> bool:
    """Ferme la session designee, si elle appartient au compte et est vivante.

    La session à révoquer appartient **au compte appelant** : un identifiant
    d'autrui ne trouve rien, la réponse ne distingue pas « inconnue » et
    « pas à vous » — pas d'information pour un sondage.
    """
    ligne = (
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.id == session_id,
                RefreshToken.user_id == utilisateur_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    ).scalars().first()
    if ligne is None:
        # Inconnue, d'autrui, ou deja fermee : la reponse ne change rien, et
        # une seconde demande reste idempotente.
        return False
    ligne.revoked_at = _maintenant()
    ligne.revoked_reason = "session"
    return True


async def revoquer_autres_sessions(
    db: AsyncSession, utilisateur_id: int, session_epargnee: Optional[str]
) -> int:
    """Ferme toutes les sessions vivantes **sauf** celle designee.

    « Fermer les autres » : la session qui a servi a poser la question est
    la seule épargnée, sinon l'action deconnecterait celui qui la demande.
    Sans session courante identifiable (jeton legacy sans ``sid``), tout
    est ferme : c'est l'ancien comportement « deconnexion partout ».
    """
    conditions = [
        RefreshToken.user_id == utilisateur_id,
        RefreshToken.revoked_at.is_(None),
    ]
    if session_epargnee:
        conditions.append(RefreshToken.id != session_epargnee)
    resultat = await db.execute(
        update(RefreshToken)
        .where(*conditions)
        .values(revoked_at=_maintenant(), revoked_reason="fermer_autres")
    )
    return int(resultat.rowcount or 0)


async def revoquer_toutes_les_sessions(
    db: AsyncSession, utilisateur_id: int
) -> int:
    """Ferme toutes les sessions vivantes du compte (changement de mot de passe)."""
    resultat = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == utilisateur_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=_maintenant(), revoked_reason="mot_de_passe")
    )
    return int(resultat.rowcount or 0)


async def purger_expirees(db: AsyncSession, *, age_jours: int) -> int:
    """Supprime les traces et sessions mortes plus vieilles que la retention.

    Une table d'incidents qui grossit sans fin finirait par n'etre jamais
    lue. La retention est un reglage ; le cron de purge appartient a
    l'exploitation.
    """
    frontiere = _maintenant() - timedelta(days=age_jours)
    tentatives = await db.execute(
        delete(LoginAttempt).where(LoginAttempt.occurred_at < frontiere)
    )
    sessions = await db.execute(
        delete(RefreshToken).where(
            (RefreshToken.expires_at < frontiere)
            | (RefreshToken.revoked_at.is_not(None) & (RefreshToken.revoked_at < frontiere))
        )
    )
    return int(tentatives.rowcount or 0) + int(sessions.rowcount or 0)


def access_token_pour(
    utilisateur: Utilisateur, *, session_id: Optional[str] = None
) -> str:
    """L'access token du compte, lie a sa session quand il en a une.

    Le claim ``sid`` est ce qui rend la revocation immediate : la validation
    d'un jeton consulte la session, et une session revoquee ferme l'acces
    avant l'expiration du jeton. Les jetons sans ``sid`` — emis avant le lot
    2 — gardent leur dureelegacy : la fenetre de compatibilite les laisse
    finir leur heure sans requete supplementaire.
    """
    claims: dict[str, Any] = {"email": utilisateur.email, "role": utilisateur.role}
    if session_id:
        claims["sid"] = session_id
    return create_access_token(
        subject=utilisateur.id,
        claims=claims,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


async def session_vivante(db: AsyncSession, session_id: str) -> bool:
    """La session designee existe-t-elle et n'a-t-elle pas ete revoquee ?

    Consulte a chaque validation de jeton porteuse de ``sid`` : c'est le
    prix d'une revocation qui mord sur l'access token, une lecture par cle
    primaire deja payee deux fois par requete (l'utilisateur, sa session).
    """
    ligne = await db.get(RefreshToken, session_id)
    if ligne is None or ligne.revoked_at is not None:
        return False
    return not _expire(ligne.expires_at)


__all__ = [
    "CompteVerrouille",
    "JetonInvalide",
    "RejeuDetecte",
    "access_token_pour",
    "compte_verrouille",
    "emettre_session",
    "enregistrer_echec",
    "enregistrer_succes",
    "empreinte",
    "ip_de_requete",
    "nouveau_jeton_refresh",
    "purger_expirees",
    "rafraichir_session",
    "revoquer_famille",
    "revoquer_jeton",
    "revoquer_toutes_les_sessions",
    "session_active_par_jeton",
    "session_vivante",
    "tracer_tentative",
]
