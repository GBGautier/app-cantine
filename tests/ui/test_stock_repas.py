"""Un produit sorti dans le bilan d'un repas doit diminuer le stock (à la création comme à la modification)."""

from .conftest import aller, champ


def _stock(page, pid):
    rows = page.context.request.get(page.base + "/api/stock").json()["rows"]
    return next(r["stock"] for r in rows if r["product_id"] == pid)


def _preparer(api):
    fid = api.post("/api/suppliers", {"name": "Ferme Stock"})["id"]
    pid = api.post("/api/products", {"name": "Carottes", "supplier_id": fid, "unit": "kg", "unit_price": 1.5})["id"]
    api.post(
        "/api/orders",
        {
            "supplier_id": fid,
            "ref": "BL-S1",
            "date": "2030-01-10",
            "lines": [{"product_id": pid, "qty": 10, "unit": "kg"}],
        },
    )
    return pid


def _sortir(page, produit, qte):
    modal = page.locator(".modal")
    modal.get_by_role("button", name="📋 Bilan").click()
    modal.get_by_role("button", name="+ Produit").last.click()
    champ_produit = modal.get_by_placeholder("Rechercher un produit…").last
    champ_produit.click()
    champ_produit.fill(produit)
    page.get_by_text(produit).last.dispatch_event("mousedown")
    modal.locator("tbody input[type=number]").last.fill(str(qte))


def test_sortie_dans_un_nouveau_repas(admin, api):
    page = admin
    pid = _preparer(api)
    aller(page, "Repas")
    page.get_by_role("button", name="+ Repas").click()
    champ(page, "Jour *").fill("2030-02-12")
    _sortir(page, "Carottes", 2)
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.locator(".modal").wait_for(state="detached")
    assert _stock(page, pid) == 8


def test_sortie_ajoutee_a_un_repas_existant(admin, api):
    page = admin
    pid = _preparer(api)
    api.post("/api/meals", {"date": "2030-02-12", "plat": "Carottes râpées", "items": []})
    aller(page, "Repas")
    page.get_by_text("Carottes râpées").first.click()
    page.locator(".modal").get_by_role("button", name="Modifier").click()
    _sortir(page, "Carottes", 3)
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.locator(".modal").wait_for(state="detached")
    assert _stock(page, pid) == 7


def test_sortie_depuis_une_recette(admin, api):
    """Repas lié à une recette : le bilan reprend les produits de la recette, et l'enregistrement sort le stock."""
    page = admin
    pid = _preparer(api)
    rid = api.post(
        "/api/recipes",
        {
            "name": "Carottes râpées",
            "categorie": "entree",
            "nb_adultes": 10,
            "items": [{"product_id": pid, "qty_servi": 2, "qty_commander": 2, "unit": "kg", "principal": True}],
        },
    )["id"]
    api.post(
        "/api/meals",
        {"date": "2030-02-12", "entree": "Carottes râpées", "recipe_entree": rid, "nb_adultes": 10, "items": []},
    )
    aller(page, "Repas")
    page.get_by_text("Carottes râpées").first.click()
    page.locator(".modal").get_by_role("button", name="Modifier").click()
    page.wait_for_timeout(800)
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.locator(".modal").wait_for(state="detached")
    assert _stock(page, pid) == 8
