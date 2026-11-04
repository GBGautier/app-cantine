"""Assistant IA dans le navigateur : bouton, chat, validation des écritures, réglages. Le modèle est un faux serveur local."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from .conftest import aller


def _appel(id_, outil, **args):
    return {"id": id_, "type": "function", "function": {"name": outil, "arguments": json.dumps(args)}}


def _reponse(msgs):
    """Scénario du faux modèle d'après le dernier message reçu."""
    dernier = msgs[-1]
    if dernier["role"] == "user":
        if "fournisseur" in dernier["content"]:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [_appel("w2", "creer_fournisseur", nom="Fournisseur Refuse")],
            }
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [_appel("r1", "rechercher_produits", requete="courgettes ui")],
        }
    nom = next(
        c["function"]["name"]
        for m in msgs
        if m.get("tool_calls")
        for c in m["tool_calls"]
        if c["id"] == dernier["tool_call_id"]
    )
    if nom == "rechercher_produits":
        pid = json.loads(dernier["content"])["produits"][0]["id"]
        ingredients = [{"produit_id": pid, "grammes_par_convive": 120, "principal": True}]
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                _appel("w1", "creer_recette", nom="Gratin de courgettes UI", categorie="plat", ingredients=ingredients)
            ],
        }
    return {
        "role": "assistant",
        "content": "Recette créée !" if nom == "creer_recette" else "D'accord, rien n'a été créé.",
    }


@pytest.fixture()
def faux_modele(monkeypatch):
    class Gestionnaire(BaseHTTPRequestHandler):
        def do_POST(self):
            corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert self.headers["Authorization"] == "Bearer cle-de-test-12345"
            msg = _reponse([m for m in corps["messages"] if m["role"] != "system"])
            data = json.dumps({"choices": [{"message": msg}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Gestionnaire)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("CGRS_ASSISTANT_URL", f"http://127.0.0.1:{srv.server_port}/v1/chat/completions")
    yield
    srv.shutdown()


def _ouvrir(page):
    page.locator("#assistant-btn").click()
    page.locator("#assistant-panel").wait_for()


def _dire(page, texte):
    page.locator("#assistant-panel textarea").fill(texte)
    page.locator("#assistant-panel").get_by_role("button", name="Envoyer").click()


def test_assistant_non_configure(admin):
    _ouvrir(admin)
    admin.locator("#assistant-panel").get_by_text("pas encore configuré").wait_for()
    admin.locator("#assistant-panel").get_by_role("button", name="Ouvrir les paramètres").click()
    admin.get_by_role("heading", name="Assistant IA").wait_for()


def test_creer_une_recette_avec_validation(faux_modele, admin, api):
    page = admin
    fid = api.post("/api/suppliers", {"name": "Ferme UI"})["id"]
    api.post("/api/products", {"name": "Courgettes UI", "supplier_id": fid, "unit": "kg", "unit_price": 2.0})
    api.put("/api/assistant/config", {"fournisseur": "mistral", "modele": "", "cle": "cle-de-test-12345"})
    page.reload()
    page.locator("#nav").wait_for()
    _ouvrir(page)
    panneau = page.locator("#assistant-panel")
    _dire(page, "Crée une recette de gratin de courgettes")
    panneau.get_by_text("Créer la recette « Gratin de courgettes UI »").wait_for()
    assert not [
        r for r in page.context.request.get(page.base + "/api/recipes").json() if r["name"] == "Gratin de courgettes UI"
    ]
    panneau.get_by_role("button", name="✔ Valider").click()
    panneau.get_by_text("Recette créée !").wait_for()
    recettes = page.context.request.get(page.base + "/api/recipes").json()
    assert [r["name"] for r in recettes] == ["Gratin de courgettes UI"]
    aller(page, "Recettes")
    page.get_by_text("Gratin de courgettes UI").first.wait_for()  # la page affichée a été rafraîchie


def test_refuser_une_ecriture(faux_modele, admin, api):
    page = admin
    api.put("/api/assistant/config", {"fournisseur": "mistral", "modele": "", "cle": "cle-de-test-12345"})
    page.reload()
    page.locator("#nav").wait_for()
    _ouvrir(page)
    panneau = page.locator("#assistant-panel")
    _dire(page, "Crée un fournisseur")
    panneau.get_by_text("Créer le fournisseur « Fournisseur Refuse »").wait_for()
    panneau.get_by_role("button", name="✖ Refuser").click()
    panneau.get_by_text("rien n'a été créé").wait_for()
    assert not [
        s for s in page.context.request.get(page.base + "/api/suppliers").json() if s["name"] == "Fournisseur Refuse"
    ]


def test_reglages_et_jeton_mcp(admin):
    page = admin
    aller(page, "Paramètres")
    carte = page.locator(".card", has=page.get_by_role("heading", name="Assistant IA"))
    page.once("dialog", lambda d: d.accept())  # sans nom, une alerte native demande d'en donner un
    carte.get_by_role("button", name="Créer un jeton").click()
    carte.get_by_placeholder("ex. Claude Desktop").fill("Mon client")
    carte.get_by_role("button", name="Créer un jeton").click()
    page.locator(".modal code").first.wait_for()
    jeton = page.locator(".modal code").first.inner_text()
    assert jeton.startswith("cgrs_") and "mcp-remote" in page.locator(".modal pre").inner_text()
    r = page.context.request.post(
        page.base + "/mcp",
        data={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={"Authorization": "Bearer " + jeton},
    )
    assert r.ok and any(t["name"] == "rechercher_produits" for t in r.json()["result"]["tools"])
