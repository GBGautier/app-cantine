"""Tests d'interface : un vrai navigateur (Chromium) pilote l'application lancée sur une base vide et jetable.

Prérequis : pip install playwright && playwright install chromium.  Sans cela, ces tests sont ignorés.
Variable CGRS_UI_TARGET : dossier de code à tester (défaut : ce dépôt) ; permet de jouer les mêmes tests sur une autre version.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402

RACINE = Path(__file__).resolve().parents[2]
CIBLE = Path(os.environ.get("CGRS_UI_TARGET", RACINE))
MOT_DE_PASSE = "Motdepasse1"


def port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def serveur():
    """Application neuve (copie du code, base vide) sur un port libre. Rend l'URL de base."""
    dossier = Path(tempfile.mkdtemp(prefix="cgrs-ui-"))
    code = dossier / "code"
    shutil.copytree(CIBLE, code, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", "*.db", "uploads", "sauvegardes-auto", "logs", "venv", ".venv", "tests", "build", "dist", ".*cache"))
    port = port_libre()
    env = {**os.environ, "CGRS_BACKUP_INTERVAL_HOURS": "0"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--port", str(port), "--log-level", "warning"],
                            cwd=code, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(base + "/api/auth/status", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("Le serveur de test n'a pas démarré : " + proc.stdout.read().decode(errors="replace")[-1500:])
    yield base
    proc.terminate()
    proc.wait(timeout=10)
    shutil.rmtree(dossier, ignore_errors=True)


@pytest.fixture(scope="session")
def navigateur():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture()
def contexte(navigateur):
    c = navigateur.new_context(locale="fr-FR", accept_downloads=True)
    # les bibliothèques d'export PDF viennent d'un CDN : inutile (et impossible hors ligne) pour ces tests
    c.route("**/cdnjs.cloudflare.com/**", lambda r: r.abort())
    yield c
    c.close()


@pytest.fixture()
def page(contexte, serveur):
    p = contexte.new_page()
    p.erreurs_js = []
    p.on("pageerror", lambda e: p.erreurs_js.append(str(e)))
    p.base = serveur
    p.set_default_timeout(8000)
    yield p
    assert not p.erreurs_js, f"Erreurs JavaScript dans la page : {p.erreurs_js}"


class Api:
    """Appels directs à l'API, avec la session du navigateur (pour préparer des données sans cliquer partout)."""

    def __init__(self, page):
        self.req = page.context.request
        self.base = page.base
        self.h = {"X-Requested-With": "cgrs"}

    def post(self, chemin, corps=None):
        r = self.req.post(self.base + chemin, data=corps, headers=self.h)
        assert r.ok, f"POST {chemin} -> {r.status} {r.text()}"
        return r.json()


@pytest.fixture()
def api(page):
    return Api(page)


@pytest.fixture()
def admin(page, api):
    """Compte administrateur créé par l'API, navigateur connecté et page principale affichée."""
    api.post("/api/auth/setup", {"username": "admin", "password": MOT_DE_PASSE})
    page.goto(page.base)
    page.locator("#nav").wait_for()
    return page


def champ(page, libelle):
    """Champ du formulaire ouvert, repéré par son libellé (l'interface n'a pas d'identifiants)."""
    return page.locator(f'.modal >> xpath=.//label[normalize-space(.)="{libelle}"]/following-sibling::*[self::input or self::select or self::textarea][1]')


def aller(page, nom):
    page.locator("#nav a", has_text=nom).click()
    page.locator("#nav a.on", has_text=nom).wait_for()
