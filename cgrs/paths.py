"""Chemins de l'application CGRS.

Deux contextes :
- dev / serveur (uvicorn) : tout reste a cote du code, comme avant ;
- exe PyInstaller (--onefile) : les donnees persistantes (BDD, uploads,
  sauvegardes) vivent dans %LOCALAPPDATA%/CGRS/, car le dossier
  d'extraction (sys._MEIPASS) est en lecture seule et efface a la fermeture.
"""
import sys
import pathlib

APP_NAME = "CGRS"

# Racine du projet (ce fichier est dans cgrs/) : les données restent à côté du code, comme avant le déplacement
ROOT = pathlib.Path(__file__).resolve().parent.parent


def app_dir() -> pathlib.Path:
    """Dossier des ressources en lecture seule (front static/, ...)."""
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys._MEIPASS)
    return ROOT


def data_dir() -> pathlib.Path:
    """Dossier de donnees persistantes, inscriptible meme en mode --onefile."""
    if getattr(sys, "frozen", False):
        base = pathlib.Path.home() / "AppData" / "Local" / APP_NAME
    else:
        base = ROOT
    base.mkdir(parents=True, exist_ok=True)
    return base


STATIC = app_dir() / "static"
UPLOADS = data_dir() / "uploads"
BACKUPS = data_dir() / "sauvegardes-auto"
LOGS = data_dir() / "logs"
DB_PATH = data_dir() / "cantine.db"