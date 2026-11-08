"""Tarif de vente d'un repas (utilisé par le bilan mensuel de l'assistant)."""

from .conftest import aller


def test_tarif_repas_dans_les_parametres(admin, api):
    page = admin
    aller(page, "Paramètres")
    champ = page.locator("input[type=number][step='0.01']").first
    champ.fill("2.5")
    champ.locator("xpath=following-sibling::button").click()
    page.wait_for_timeout(300)
    assert api.get("/api/settings")["tarif_repas"] == 2.5


def test_page_statistiques_affiche_le_bilan_de_la_periode(admin, api):
    page = admin
    f = api.post("/api/suppliers", {"name": "Ferme Stats Bilan", "direct_producteur": 1})["id"]
    p = api.post(
        "/api/products",
        {
            "name": "Carottes stats bilan",
            "supplier_id": f,
            "unit": "kg",
            "unit_price": 2.0,
            "category": "Légumes",
            "label_egalim": "bio",
            "provenance": "france",
            "gamme": "1",
        },
    )["id"]
    api.post(
        "/api/orders",
        {
            "supplier_id": f,
            "kind": "facture",
            "date": "2032-10-10",
            "lines": [{"product_id": p, "qty": 10, "unit": "kg", "unit_price": 2.0}],
        },
    )
    aller(page, "Statistiques")
    page.evaluate("store.set('cgrs.sf', '2032-10-01'); store.set('cgrs.st', '2032-10-31'); render()")
    page.get_by_text("Synthèse de la période").wait_for()
    corps = page.locator("main, body").first.inner_text()
    for attendu in (
        "Part de bio, toutes denrées",
        "Produits bio par famille",
        "Origine par famille de produits",
        "Répartition par gamme",
        "Respecté",
        "Non respecté",
    ):
        assert attendu in corps
    for interdit in (
        "cumul",
        "Cumul",
        "Ce mois",
        "Hors France",
        "Autres labels",
        "Sans label",
        "Engagements du marché",
        "Bilan mensuel",
        "Synthèse du mois",
        "Le mois par rapport",
    ):
        assert interdit not in corps
    aller(page, "Paramètres")
    assert "Engagements du marché" not in page.locator("main, body").first.inner_text()
