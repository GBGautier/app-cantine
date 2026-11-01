# Construction de l'exécutable (PyInstaller) : voir construire_exe.bat
#   depuis la racine du projet : pyinstaller windows/cgrs.spec  ->  dist/Cantine.exe (Windows) ou dist/Cantine (autre système)
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))   # racine du projet (ce fichier est dans windows/)
sys.path.insert(0, ROOT)

# CGRS_DEBUG=1 (voir construire_exe.bat debug) : exécutable avec console, pour voir les erreurs de démarrage
DEBUG = os.environ.get("CGRS_DEBUG") == "1"

datas = [(os.path.join(ROOT, "static"), "static")]          # l'interface (lue depuis le dossier d'extraction)
binaries = []
hiddenimports = collect_submodules("uvicorn") + collect_submodules("cgrs") + ["multipart"]

# bibliothèques qui embarquent des fichiers de données (polices/cartes de caractères des PDF, etc.)
for pkg in ("pdfplumber", "pdfminer", "pytesseract"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis([os.path.join(ROOT, "main.py")], pathex=[ROOT], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=["pytest", "httpx", "ruff", "tkinter"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name="Cantine-debug" if DEBUG else "Cantine",
          console=DEBUG,   # normal : sans console (fenêtre seule) ; debug : avec console
          icon=os.path.join(SPECPATH, "cgrs.ico"))
