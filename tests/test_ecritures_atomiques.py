"""Une saisie refusée ne laisse rien derrière elle, et dit pourquoi (au lieu d'une erreur 500)."""
import sqlite3

from cgrs import errors

INEXISTANT = 999_999


def test_dossier_uploads_cree_au_demarrage(client):
    from cgrs.config import UPLOADS
    assert UPLOADS.is_dir()


def test_repas_avec_produit_inexistant_est_refuse_sans_rien_creer(client):
    avant = client.get("/api/meals").json()
    r = client.post("/api/meals", json={"date": "2030-01-01", "plat": "Test",
                                        "items": [{"product_id": INEXISTANT, "qty": 1}]})
    assert r.status_code == 422
    assert "Référence inconnue" in r.json()["detail"]
    assert client.get("/api/meals").json() == avant            # aucun repas vide ne doit rester


def test_modification_de_recette_refusee_garde_les_ingredients(client):
    pid = client.post("/api/products", json={"name": "Farine test"}).json()["id"]
    rid = client.post("/api/recipes", json={"name": "Gâteau", "items": [{"product_id": pid, "qty_servi": 1}]}).json()["id"]
    r = client.put(f"/api/recipes/{rid}", json={"name": "Autre", "items": [{"product_id": INEXISTANT, "qty_servi": 1}]})
    assert r.status_code == 422
    recette = client.get(f"/api/recipes/{rid}").json()
    assert recette["name"] == "Gâteau"
    assert len(recette["items"]) == 1                           # avant : les ingrédients étaient effacés


def test_recette_avec_produit_inexistant_ne_cree_pas_de_recette_vide(client):
    avant = client.get("/api/recipes").json()
    r = client.post("/api/recipes", json={"name": "Orpheline", "items": [{"product_id": INEXISTANT, "qty_servi": 1}]})
    assert r.status_code == 422
    assert client.get("/api/recipes").json() == avant


def test_reception_avec_ligne_inexistante_ne_cree_pas_de_reception(client):
    sid = client.post("/api/suppliers", json={"name": "Fournisseur test"}).json()["id"]
    avant = client.get("/api/orders").json()
    r = client.post("/api/orders", json={"supplier_id": sid, "ref": "T-1", "kind": "livraison", "date": "2030-01-01",
                                         "lines": [{"product_id": INEXISTANT, "qty": 1, "unit": "kg", "unit_price": 1.0}]})
    assert r.status_code == 422
    assert client.get("/api/orders").json() == avant


def test_produit_sur_fournisseur_inexistant(client):
    r = client.post("/api/products", json={"name": "Produit orphelin", "supplier_id": INEXISTANT})
    assert r.status_code == 422
    assert "Référence inconnue" in r.json()["detail"]


def test_les_reponses_d_erreur_portent_les_en_tetes_de_securite(client):
    r = client.post("/api/products", json={"name": "Produit orphelin 2", "supplier_id": INEXISTANT})
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"


def test_messages_selon_la_contrainte():
    assert errors.integrity_response(sqlite3.IntegrityError("FOREIGN KEY constraint failed"))[0] == 422
    assert errors.integrity_response(sqlite3.IntegrityError("UNIQUE constraint failed: users.username")) == (409, "Cet élément existe déjà.")
    assert errors.integrity_response(sqlite3.IntegrityError("NOT NULL constraint failed: meals.date"))[0] == 422
    assert errors.integrity_response(sqlite3.IntegrityError("CHECK constraint failed: x"))[0] == 409
