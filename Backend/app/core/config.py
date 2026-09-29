"""
Configuration centralisée de l'application EduManagePro (EMP).
Utilise Pydantic Settings V2 pour la validation et le chargement depuis le fichier .env.
"""

from typing import List, Union
import secrets
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Métadonnées Projet
    PROJECT_NAME: str = "EduManagePro API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Mode Déploiement : "standalone" (On-premise client unique) ou "multi_tenant" (Cloud / SaaS)
    TENANT_MODE: str = "standalone"

    # Sécurité & Tokens JWT
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    # Un access token vit une heure : c'est la fenetre d'exploitation d'un
    # jeton intercepte. La session survit au jeton via le refresh token.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Anti-brute-force (lot 2). Le verrou suit le COMPTE : un attaquant
    # distribue ses requetes sur des IP, jamais sur les comptes visees. Les
    # trois valeurs sont des reglages d'exploitation, pas des constantes.
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    # Limiteur de debit en memoire : nombre d'ECHECS toleres par fenetre
    # glissante, pour le couple (adresse, email tente). Un NAT d'ecole ne
    # doit pas se bloquer lui-meme : les reussites ne comptent pas.
    LOGIN_RATE_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_WINDOW_SECONDS: int = 300
    # Les tentatives tracees ne vivent pas pour toujours : une table
    # d'incidents qui grossit sans fin finit par n'etre jamais relue.
    LOGIN_ATTEMPTS_RETENTION_DAYS: int = 90

    # Sessions revocables (lot 2). Le refresh token vit une semaine, glisse
    # a chaque rotation ; l'access token, lui, meurt au bout d'une heure et
    # se renouvelle silencieusement. Revoquer la ligne ferme l'acces avant
    # l'expiration.
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 7 * 24 * 60

    # Derriere un reverse-proxy (nginx, traefik), l'adresse vue par l'API
    # est celle du proxy : lire ``X-Forwarded-For`` est alors necessaire.
    # Hors proxy, le header est ignore — un client le fabrique en une ligne.
    TRUST_PROXY_HEADERS: bool = False

    # Envoi d'emails (lot 4). Sans serveur configure (SMTP_HOST vide), aucun
    # email ne part : l'envoi passe en mode SIMULATION, trace et lisible,
    # pour qu'un institut puisse utiliser le module sans compte SMTP et pour
    # que les tests ne dependent jamais d'un serveur exterieur.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_STARTTLS: bool = True
    #: Expediteur affiche : « Institut X <no-reply@institut.org> ».
    SMTP_FROM: str = "EduManagePro <no-reply@edumanagepro.local>"
    #: En production, un email part en 10 secondes et peut echouer : l'envoi
    # se fait hors de la requete HTTP, jamais en bloquant le secretaire.
    EMAIL_SEND_TIMEOUT_SECONDS: int = 15

    # Paiements en ligne (lot 4b). Tant qu'aucune passerelle reelle n'est
    # branchee, le provider est ``simulation`` : la confirmation suit les
    # regles du guichet et produit un Paiement + Recu normaux. Brancher Wave
    # ou Orange Money reviendra a remplacer la fonction de confirmation.
    PAYMENT_LINK_VALIDITY_DAYS: int = 7

    # Multi-tenant (lot 6). En ``standalone`` (defaut), tout continue de
    # pointer sur ``DATABASE_URL`` : une installation cliente ne sait même
    # pas que le multi-tenant existe. En ``multi_tenant``, la base de
    # contrôle (``DATABASE_URL``) porte le registre des écoles et chaque
    # école reçoit sa base ``emp_tenant_{id}`` sur le même serveur.
    #
    # La résolution de la requête à l'école se fait par l'en-tête
    # ``X-Tenant-ID`` ; le sous-domaine (``isi.edumanagepro.com``) viendra
    # s'ajouter au même middleware le jour du déploiement, sans rien
    # réécrire ailleurs.
    TENANT_HEADER: str = "X-Tenant-ID"

    # Base de données PostgreSQL Asynchrone
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/edumanagepro"
    
    # Paramètres de grappe SGBD (pour le provisionnement dynamique multi-tenant)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"

    # Stockage local des pièces d'admission (les octets restent hors PostgreSQL)
    ADMISSIONS_STORAGE_DIR: str = "storage/admissions"
    ADMISSIONS_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024

    # Documents officiels generes (PDF). Les octets restent hors PostgreSQL,
    # qui ne conserve que le chemin relatif et l'empreinte SHA-256.
    DOCUMENTS_STORAGE_DIR: str = "storage/documents"

    # Branding institutionnel (logo). Les octets restent hors PostgreSQL, qui
    # ne conserve que le chemin relatif dans ``etablissements.logo_url``.
    BRANDING_STORAGE_DIR: str = "storage/etablissement"

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            if self.DEBUG:
                raise ValueError("DEBUG doit être désactivé en production.")
            weak_markers = ("emp_dev_secret", "emp_super_secret", "change_in_production")
            if len(self.SECRET_KEY) < 32 or any(marker in self.SECRET_KEY for marker in weak_markers):
                raise ValueError("SECRET_KEY doit être aléatoire et faire au moins 32 caractères en production.")
        elif not self.SECRET_KEY:
            # En développement, une clé éphémère évite tout secret codé en dur
            # tout en invalidant les tokens lors d'un redémarrage du processus.
            self.SECRET_KEY = secrets.token_urlsafe(48)
        return self

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


settings = Settings()
