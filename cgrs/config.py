"""Chemins de l'application (dossier statique et dossier des fichiers envoyés)."""

import os

import paths


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
UPLOADS.mkdir(parents=True, exist_ok=True)   # paths.py ne crée que le dossier de données : sans ceci, le premier envoi de PDF échouait (erreur 500)
