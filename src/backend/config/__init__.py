"""Configuration de l'application.

Ce module centralise toute la configuration de l'application,
y compris les paramètres par défaut et la lecture des variables d'environnement.
"""

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()


class Settings:
    """Paramètres de configuration de l'application."""

    # Environnement
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Serveur
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))

    # Base de données
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "cantine.db")

    # Répertoires
    UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", "uploads")
    BACKUPS_DIR: str = os.getenv("BACKUPS_DIR", "sauvegardes-auto")
    STATIC_DIR: str = os.getenv("STATIC_DIR", "static")

    # Authentification
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key-change-me")
    PASSWORD_HASH_ALGORITHM: str = os.getenv("PASSWORD_HASH_ALGORITHM", "pbkdf2_sha256")
    PBKDF2_ITERATIONS: int = int(os.getenv("PBKDF2_ITERATIONS", "240000"))
    SESSION_EXPIRY_DAYS: int = int(os.getenv("SESSION_EXPIRY_DAYS", "30"))
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "cgrs_session")

    # Sécurité
    CSRF_PROTECTION: bool = os.getenv("CSRF_PROTECTION", "true").lower() == "true"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
    HTTPS_MODE: bool = os.getenv("HTTPS_MODE", "false").lower() == "true"

    # OCR
    TESSERACT_PATH: str = os.getenv("TESSERACT_PATH", "")
    TESSERACT_LANGUAGES: str = os.getenv("TESSERACT_LANGUAGES", "fra+eng")

    # Journalisation
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "")
    LOG_MAX_SIZE: int = int(os.getenv("LOG_MAX_SIZE", "10"))
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # Sauvegardes
    AUTO_BACKUP_ENABLED: bool = os.getenv("AUTO_BACKUP_ENABLED", "true").lower() == "true"
    AUTO_BACKUP_FREQUENCY: int = int(os.getenv("AUTO_BACKUP_FREQUENCY", "24"))
    AUTO_BACKUP_RETENTION: int = int(os.getenv("AUTO_BACKUP_RETENTION", "7"))

    # Export Dolibarr
    CLIENT_NAMES: str = os.getenv("CLIENT_NAMES", "")

    # Limites
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "25"))
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_DURATION: int = int(os.getenv("LOGIN_LOCKOUT_DURATION", "60"))

    @classmethod
    def get_cors_origins_list(cls) -> list[str]:
        """Retourne la liste des origines CORS autorisées."""
        return [origin.strip() for origin in cls.CORS_ORIGINS.split(",") if origin.strip()]

    @classmethod
    def get_client_names_list(cls) -> list[str]:
        """Retourne la liste des noms de clients."""
        if not cls.CLIENT_NAMES:
            return []
        return [name.strip() for name in cls.CLIENT_NAMES.split(";") if name.strip()]


# Instance globale des paramètres
settings = Settings()


def get_settings() -> Settings:
    """Retourne l'instance globale des paramètres."""
    return settings


def get_data_dir() -> Path:
    """Retourne le répertoire des données persistantes."""
    # En mode développement, utiliser le répertoire courant
    # En mode production (exécutable), utiliser %LOCALAPPDATA%/CGRS/
    if getattr(sys, "frozen", False):
        base = Path.home() / "AppData" / "Local" / "CGRS"
    else:
        base = Path(__file__).parent.parent.parent.parent
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_uploads_dir() -> Path:
    """Retourne le répertoire des uploads."""
    data_dir = get_data_dir()
    uploads_dir = data_dir / settings.UPLOADS_DIR
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


def get_backups_dir() -> Path:
    """Retourne le répertoire des sauvegardes."""
    data_dir = get_data_dir()
    backups_dir = data_dir / settings.BACKUPS_DIR
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir


def get_static_dir() -> Path:
    """Retourne le répertoire des fichiers statiques."""
    return Path(__file__).parent.parent.parent / "frontend" / settings.STATIC_DIR


def get_database_path() -> Path:
    """Retourne le chemin vers la base de données."""
    data_dir = get_data_dir()
    return data_dir / settings.DATABASE_PATH
