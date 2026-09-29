"""
Authentication Endpoints :
- POST /login : Connexion avec email et mot de passe, génération du token JWT
- GET /me : Profil de l'utilisateur actuellement connecté, augmenté des rôles
  dynamiques et des permissions effectives
- POST /refresh : rotation d'une session révocable (lot 2)
- POST /logout : révocation de la session courante ou de toutes (lot 2)
- GET /sessions : les sessions vivantes du compte (lot 2)

La défense du login vit dans ``auth_service`` (compteur d'échecs consécutifs,
verrouillage du compte, trace de chaque tentative) et dans ``rate_limit``
(débit par adresse+email) ; ce module ne traduit que les réponses HTTP.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    PERMISSIONS_ADMIN_SEULE,
    get_current_active_user,
    get_db,
    legacy_permissions_for,
    oauth2_scheme,
)
from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from app.models.auth_securite import RefreshToken
from app.models.utilisateur import Utilisateur, UserRole
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    SessionListResponse,
    SessionResponse,
    TokenResponse,
)
from app.schemas.rbac import CurrentUserResponse
from app.schemas.user import CurrentProfileUpdate, PasswordChange, UserResponse
from app.services import auth_service
from app.services import rate_limit
from app.services.audit_service import record_audit_event
from app.services.rbac_service import effective_permissions

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authentification utilisateur",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authentifie un utilisateur avec son email et son mot de passe.

    Retourne un jeton d'accès Bearer, le profil utilisateur, et un jeton de
    rafraîchissement ouvrant une session révocable. Le compte se verrouille
    temporairement après trop d'échecs consécutifs ; chaque tentative est
    tracée, réussie comme échouée.
    """
    email = payload.email.lower().strip()
    ip = auth_service.ip_de_requete(request)
    cle = rate_limit.cle_login(ip, email)

    # La fenêtre de débit se lit AVANT tout travail : bcrypt coûte cher, et
    # un attaquant ne doit pas pouvoir dépenser le CPU du serveur une seule
    # fois de plus que la fenêtre ne l'autorise.
    depasse, retry = rate_limit.depasser(cle)
    if depasse:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Trop de tentatives de connexion. Réessayez dans "
                f"{retry} seconde(s)."
            ),
            headers={"Retry-After": str(retry)},
        )

    stmt = select(Utilisateur).where(Utilisateur.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is not None:
        verrou = await auth_service.compte_verrouille(db, user)
        if verrou is not None:
            # La trace precedente la reponse — et le commit aussi : la
            # session de requete annule tout ce qui n'est pas valide des
            # qu'une exception quitte l'endpoint. Un refus sans trace serait
            # une attaque que personne ne pourrait lire apres coup.
            await auth_service.tracer_tentative(
                db, email=email, ip=ip, resultat="failed", user_id=user.id
            )
            await record_audit_event(
                db,
                action="auth.login.refuse",
                resource_type="utilisateur",
                resource_id=str(user.id),
                actor_id=user.id,
                actor_email=user.email,
                outcome="failure",
                reason="compte_verrouille",
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=(
                    "Compte temporairement verrouillé après trop d'échecs de "
                    "connexion. Réessayez plus tard."
                ),
                headers={"Retry-After": str(settings.LOGIN_LOCKOUT_MINUTES * 60)},
            )

    mot_de_passe_ok = user is not None and verify_password(
        payload.password, user.hashed_password
    )

    if user is None or not mot_de_passe_ok:
        if user is not None:
            await auth_service.enregistrer_echec(db, user)
        await auth_service.tracer_tentative(
            db, email=email, ip=ip, resultat="failed", user_id=user.id if user else None
        )
        # Le commit AVANT le refus : le compteur d'echecs et la trace
        # survivent a l'exception qui ferme la transaction. Sans lui, chaque
        # echec serait oublie a la reponse, et le compte ne se verrouillerait
        # jamais — une defense qui ne compte pas n'est pas une defense.
        await db.commit()
        rate_limit.compter(cle)
        # Le message ne dit pas lequel des deux identifiants est faux :
        # distinguer « email inconnu » et « mot de passe faux » dirait à un
        # attaquant qu'il a trouvé un compte existant.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        await auth_service.tracer_tentative(
            db, email=email, ip=ip, resultat="failed", user_id=user.id
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte utilisateur a été désactivé. Veuillez contacter l'administrateur."
        )

    # Le débit se libère à la réussite : un NAT d'école ne cumule pas les
    # échecs de ses différents élèves.
    rate_limit.liberer(cle)
    await auth_service.enregistrer_succes(db, user)
    await auth_service.tracer_tentative(
        db, email=email, ip=ip, resultat="success", user_id=user.id
    )

    # Mise à jour date dernière connexion
    user.last_login = datetime.now(timezone.utc)

    # Session révocable + jeton d'accès lié par ``sid`` : revoquer la session
    # ferme l'accès avant l'expiration du jeton.
    jeton_refresh, _, id_session = await auth_service.emettre_session(
        db, utilisateur=user
    )
    jeton = auth_service.access_token_pour(user, session_id=id_session)

    await record_audit_event(
        db,
        action="auth.login.reussi",
        resource_type="utilisateur",
        resource_id=str(user.id),
        actor_id=user.id,
        actor_email=user.email,
        outcome="success",
    )

    # Un seul commit : la trace, le compteur et la session partent avec la
    # réponse. Un trace perdu en route ferait croire qu'une tentative n'a
    # jamais eu lieu.
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=jeton,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
        refresh_token=jeton_refresh,
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Rafraîchir la session (rotation du jeton)",
)
async def refresh_session(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Échange un jeton de rafraîchissement contre une session neuve.

    La rotation est **obligatoire** : l'ancien jeton est révoqué à chaque
    appel, et le nouveau ne sert qu'une fois. Rejouer un jeton déjà tourné
    ferme toutes les sessions du compte — le signal standard d'un vol.
    """
    try:
        user, nouveau, expiration, id_session = await auth_service.rafraichir_session(
            db, jeton=payload.refresh_token
        )
    except auth_service.RejeuDetecte as rejeu:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(rejeu),
        ) from rejeu
    except auth_service.JetonInvalide:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton de rafraîchissement invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    await db.commit()
    return RefreshResponse(
        access_token=auth_service.access_token_pour(user, session_id=id_session),
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=nouveau,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Fermer sa (ou ses) session(s)",
)
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    """Révoque la session désignée, ou toutes les sessions du compte.

    Un jeton de rafraîchissement inconnu ne change rien : la déconnexion est
    idempotente, on ne dit jamais si la session a existé.
    """
    if payload.refresh_token:
        await auth_service.revoquer_jeton(db, payload.refresh_token)
    else:
        await auth_service.revoquer_toutes_les_sessions(db, current_user.id)
    await db.commit()
    return None


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="Les sessions vivantes du compte",
)
async def lister_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
    jeton: Optional[str] = Depends(oauth2_scheme),
):
    """Les sessions révocables actives du compte, pour l'écran « mes sessions ».

    La session qui a émis le jeton de la requête est marquée ``actuelle`` :
    l'écran désigne « cette machine » sans deviner, et propose « fermer les
    autres » qui n'en fait jamais partie.
    """
    session_courante = auth_service.session_id_du_jeton(jeton)
    lignes = list(
        (
            await db.execute(
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == current_user.id,
                    RefreshToken.revoked_at.is_(None),
                    RefreshToken.expires_at > datetime.now(timezone.utc),
                )
                .order_by(RefreshToken.created_at.desc())
            )
        ).scalars().all()
    )
    sessions = [
        SessionResponse(
            id=ligne.id,
            created_at=ligne.created_at.isoformat(),
            expires_at=ligne.expires_at.isoformat(),
            last_used_at=ligne.last_used_at.isoformat() if ligne.last_used_at else None,
            actuelle=ligne.id == session_courante,
        )
        for ligne in lignes
    ]
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Fermer une session précise du compte",
)
async def fermer_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    """Ferme la session désignée, si elle appartient au compte.

    Révoquer la session actuelle déconnecte cette machine dès la prochaine
    requête : l'écran le dit avant de le faire.
    """
    await auth_service.revoquer_session_par_id(db, current_user.id, session_id)
    await db.commit()
    return None


@router.post(
    "/sessions/fermer-autres",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Fermer toutes les sessions sauf celle-ci",
)
async def fermer_autres_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
    jeton: Optional[str] = Depends(oauth2_scheme),
):
    """Le réflexe « j'ai oublié une session ouverte ailleurs ».

    La session qui a émis le jeton de la requête est la seule épargnée : se
    déconnecter soi-même en voulant fermer les autres serait un piège.
    """
    session_courante = auth_service.session_id_du_jeton(jeton)
    await auth_service.revoquer_autres_sessions(db, current_user.id, session_courante)
    await db.commit()
    return None


@router.get("/me", response_model=CurrentUserResponse, summary="Profil utilisateur connecté")
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    """Retourne le profil de l'utilisateur actuellement authentifié.

    Le contrat historique est intégralement préservé : ``role`` reste la
    projection legacy et ``is_superuser`` reste la projection historique.
    Quatre champs additifs exposent l'autorité :

    - ``roles``                  : codes des rôles dynamiques actifs portés ;
    - ``permissions``            : autorité dynamique **pure** (allow-only) ;
    - ``permissions_effectives`` : droits **réellement exerçables**, c'est-à-dire
      l'union des permissions dynamiques et de la fenêtre de compatibilité du
      rôle legacy.  C'est le champ que l'interface doit utiliser pour afficher
      un menu ou ouvrir une vue, sans maintenir de matrice locale ;
    - ``authz_version``          : horodatage de la dernière modification
      d'autorité, à utiliser pour invalider un cache côté client.

    Les permissions sont résolues dans la transaction de la requête : la
    réponse est atomique avec l'état de la base au moment de la lecture.
    """
    profile = CurrentUserResponse.model_validate(current_user)
    authorization = await effective_permissions(db, current_user)
    profile.roles = list(authorization.role_codes)
    profile.permissions = list(authorization.permission_codes)
    # Fenêtre legacy issue de la même table de guards que les endpoints : le
    # client ne peut donc ni inventer ni manquer un droit.
    if current_user.role == UserRole.ADMIN.value:
        # Raccourci de transition : l'ADMIN herite des permissions sans
        # fenetre legacy declaree, afin que l'interface reste coherente avec
        # ce que les guards autorisent reellement pour ce compte.
        heritee = set(PERMISSIONS_ADMIN_SEULE)
    else:
        heritee = set(legacy_permissions_for(current_user.role))
    profile.permissions_effectives = sorted(
        set(authorization.permission_codes) | heritee
    )
    profile.authz_version = authorization.authz_version
    return profile


@router.patch("/me", response_model=UserResponse, summary="Modifier son profil")
async def update_current_user_profile(
    payload: CurrentProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(current_user, field, value or None)
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT, summary="Modifier son mot de passe")
async def change_current_password(
    payload: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_active_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mot de passe actuel incorrect.")
    current_user.hashed_password = get_password_hash(payload.new_password)
    # Un mot de passe change invalide les sessions ouvertes : qui possède
    # l'ancien secret ne doit pas garder un accès glissant au compte.
    fermees = await auth_service.revoquer_toutes_les_sessions(db, current_user.id)
    await db.commit()
    if fermees:
        await record_audit_event(
            db,
            action="auth.sessions.revoquees",
            resource_type="utilisateur",
            resource_id=str(current_user.id),
            actor_id=current_user.id,
            actor_email=current_user.email,
            outcome="success",
            reason="changement_mot_de_passe",
            details={"sessions_fermees": fermees},
        )
        await db.commit()
