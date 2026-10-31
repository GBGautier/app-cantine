"""Chemins de l'application (dossier statique et dossier des fichiers envoyés)."""

import os

from cgrs import paths


STATIC = paths.STATIC
UPLOADS = paths.UPLOADS
LOGS = paths.LOGS
BACKUPS = paths.BACKUPS


def _number(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


# Sauvegardes automatiques : intervalle en heures (0 = désactivées) et nombre de copies conservées
BACKUP_INTERVAL_HOURS = _number("CGRS_BACKUP_INTERVAL_HOURS", 24)
BACKUP_KEEP = int(_number("CGRS_BACKUP_KEEP", 14))
UPLOADS.mkdir(
    parents=True, exist_ok=True
)  # paths.py ne crée que le dossier de données : sans ceci, le premier envoi de PDF échouait (erreur 500)


def _flag(name: str, default: bool) -> bool:
    return os.environ.get(name, "1" if default else "0").strip().lower() in ("1", "true", "oui", "yes", "on")


# Exposition sur Internet (derrière un proxy HTTPS) : tout est désactivé par défaut = comportement d'origine
API_DOCS = _flag("CGRS_DOCS", True)  # 0 : masque /docs, /redoc et /openapi.json
HSTS = _flag("CGRS_HSTS", False)  # 1 : en-tête Strict-Transport-Security (HTTPS uniquement)
SECURE_COOKIES = _flag(
    "CGRS_SECURE_COOKIES", False
)  # 1 : cookie de session toujours « Secure » (même derrière un proxy)
