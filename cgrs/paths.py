"""Chemins de l'application.

Deux contextes :
- dev / serveur (uvicorn) : tout reste a cote du code, comme avant ;
- exe PyInstaller (--onefile) : les donnees persistantes (BDD, uploads,
  sauvegardes) vivent dans %LOCALAPPDATA%/Cantine/, car le dossier
  d'extraction (sys._MEIPASS) est en lecture seule et efface a la fermeture.
"""

import sys
import pathlib

APP_NAME = "Cantine"
LEGACY_APP_NAME = "CGRS"  # ancien nom du dossier de données de l'exécutable : repris automatiquement

# Racine du projet (ce fichier est dans cgrs/) : les données restent à côté du code, comme avant le déplacement
ROOT = pathlib.Path(__file__).resolve().parent.parent


def app_dir() -> pathlib.Path:
    """Dossier des ressources en lecture seule (front static/, ...)."""
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys._MEIPASS)
    return ROOT


def migrate_legacy_dir(base: pathlib.Path, legacy: pathlib.Path) -> pathlib.Path:
    """Dossier de données à utiliser : `base`, après reprise de l'ancien dossier `legacy` s'il existe encore.

    Le dossier est renommé (rien n'est copié ni supprimé) seulement si `base` n'existe pas encore. Si le renommage échoue
    (fichier ouvert, droits), on continue avec l'ancien dossier plutôt que de démarrer sur une base vide.
    """
    if base.exists() or not legacy.is_dir():
        return base
    try:
        legacy.rename(base)
    except OSError:
        return legacy
    return base


def data_dir() -> pathlib.Path:
    """Dossier de donnees persistantes, inscriptible meme en mode --onefile."""
    if getattr(sys, "frozen", False):
        local = pathlib.Path.home() / "AppData" / "Local"
        base = migrate_legacy_dir(local / APP_NAME, local / LEGACY_APP_NAME)
    else:
        base = ROOT
    base.mkdir(parents=True, exist_ok=True)
    return base


STATIC = app_dir() / "static"
UPLOADS = data_dir() / "uploads"
BACKUPS = data_dir() / "sauvegardes-auto"
LOGS = data_dir() / "logs"
DB_PATH = data_dir() / "cantine.db"
