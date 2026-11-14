"""Le guide utilisateur (docs/GUIDE.md) doit suivre l'application : pages, cartes de Paramètres, outils de l'assistant."""

import importlib.util
import re
from pathlib import Path

from cgrs.assistant.outils import OUTILS

RACINE = Path(__file__).resolve().parents[1]
GUIDE = (RACINE / "docs" / "GUIDE.md").read_text(encoding="utf-8")


def test_chaque_page_est_decrite():
    nav = (RACINE / "static" / "js" / "navigation.js").read_text(encoding="utf-8")
    pages = re.findall(r"^\s+\w+: \['([^']+)'", nav, re.M)
    assert pages, "aucune page trouvée dans navigation.js"
    manquantes = [p for p in pages if f"**{p}**" not in GUIDE]
    assert not manquantes, f"pages absentes du guide : {manquantes}"


def test_chaque_carte_des_parametres_est_decrite():
    js = (RACINE / "static" / "js" / "parametres.js").read_text(encoding="utf-8")
    cartes = re.findall(r"h\('h3', \{\}, '((?:[^'\\]|\\.)+)'\)", js)
    cartes = [c.replace("\\'", "'") for c in cartes]
    assert cartes
    manquantes = [c for c in cartes if f"**{c}**" not in GUIDE]
    assert not manquantes, f"cartes de Paramètres absentes du guide : {manquantes}"


def test_chaque_outil_de_l_assistant_est_cite():
    manquants = [o.nom for o in OUTILS if f"`{o.nom}`" not in GUIDE]
    assert not manquants, f"outils de l'assistant absents du guide : {manquants}"


def test_date_de_mise_a_jour_presente():
    assert re.search(r"Dernière mise à jour : \d{1,2} \w+ 20\d\d", GUIDE)


def _generateur():
    spec = importlib.util.spec_from_file_location("generer_guide", RACINE / "docs" / "generer_guide.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_chaque_page_a_sa_diapositive_dans_le_pdf():
    gen = _generateur()
    nav = (RACINE / "static" / "js" / "navigation.js").read_text(encoding="utf-8")
    pages = re.findall(r"^\s+\w+: \['([^']+)'", nav, re.M)
    rubriques = {d[0].upper() for d in gen.DIAPOSITIVES}
    manquantes = [p for p in pages if p.upper() not in rubriques]
    assert not manquantes, f"pages sans diapositive dans docs/generer_guide.py : {manquantes}"


def test_pdf_du_guide_a_jour_avec_l_interface():
    """L'interface a changé depuis la dernière génération du PDF : lancer `python docs/generer_guide.py`."""
    assert (RACINE / "docs" / "guide-application.pdf").stat().st_size > 100_000
    enregistree = (RACINE / "docs" / "guide-application.empreinte").read_text(encoding="utf-8").strip()
    assert enregistree == _generateur().empreinte(), (
        "docs/guide-application.pdf n'est plus à jour : lancer `python docs/generer_guide.py` puis le valider"
    )
