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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 heures

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
