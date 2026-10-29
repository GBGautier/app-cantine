"""Chemins de l'application CGRS.

Deux contextes :
- dev / serveur (uvicorn) : tout reste à côté du code, comme avant ;
- exe PyInstaller (--onefile) : les données persistantes (BDD, uploads,
  sauvegardes) vivent dans %LOCALAPPDATA%/CGRS/, car le dossier
  d'extraction (sys._MEIPASS) est en lecture seule et effacé à la fermeture.
"""
import sys
from pathlib import Path

APP_NAME = "CGRS"


def app_dir() -> Path:
    """Dossier des ressources en lecture seule (front static/, ...)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent


def data_dir() -> Path:
    """Dossier de données persistantes, inscriptible même en mode --onefile."""
    if getattr(sys, "frozen", False):
        base = Path.home() / "AppData" / "Local" / APP_NAME
    else:
        base = Path(__file__).parent.parent.parent.parent
    base.mkdir(parents=True, exist_ok=True)
    return base


# Chemins par défaut
STATIC = app_dir() / "frontend" / "static"
UPLOADS = data_dir() / "uploads"
BACKUPS = data_dir() / "sauvegardes-auto"
DB_PATH = data_dir() / "cantine.db"

# Initialisation des répertoires
UPLOADS.mkdir(parents=True, exist_ok=True)
BACKUPS.mkdir(parents=True, exist_ok=True)
