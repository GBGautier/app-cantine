# Construction de l'exécutable (PyInstaller) : voir construire_exe.bat
#   pyinstaller cgrs.spec  ->  dist/CGRS.exe (Windows) ou dist/CGRS (autre système)
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [("static", "static")]          # l'interface (lue depuis le dossier d'extraction)
binaries = []
hiddenimports = collect_submodules("uvicorn") + collect_submodules("cgrs") + ["multipart"]

# bibliothèques qui embarquent des fichiers de données (polices/cartes de caractères des PDF, etc.)
for pkg in ("pdfplumber", "pdfminer", "pytesseract"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(["main.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             excludes=["pytest", "httpx", "ruff", "tkinter"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name="CGRS",
          console=False,                # sans console : pour la diagnostiquer, mettre True (ou lire logs/cgrs.log)
          # pas de fenêtre noire : l'interface s'ouvre dans une fenêtre dédiée
          icon=None)
