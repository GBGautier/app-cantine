"""Statistiques : seuls les repas valorisés (coût > 0 et au moins un convive) sont comptés."""


def test_repas_sans_convive_ou_sans_cout_ignores(client):
    fid = client.post("/api/suppliers", json={"name": "Ferme Stats"}).json()["id"]
    pid = client.post(
        "/api/products", json={"name": "Carottes", "supplier_id": fid, "unit": "kg", "unit_price": 2.0}
    ).json()["id"]
    avec_cout = [{"product_id": pid, "qty": 10, "unit": "kg"}]

    def repas(date, adultes, items):
        r = client.post("/api/meals", json={"date": date, "nb_adultes": adultes, "plat": "x", "items": items})
        assert r.status_code == 200, r.text

    repas("2031-04-01", 10, avec_cout)  # valorisé : 20 € pour 10 convives
    repas("2031-04-02", 0, avec_cout)  # 0 convive : ignoré
    repas("2031-04-03", 10, [])  # aucun produit sorti : ignoré
    repas("2031-04-04", 0, [])  # ni l'un ni l'autre : ignoré

    s = client.get("/api/stats", params={"date_from": "2031-04-01", "date_to": "2031-04-30"}).json()
    assert (s["meals"], s["meals_priced"], s["guests"]) == (1, 1, 10)
    assert [d["date"] for d in s["daily"]] == ["2031-04-01"]
    assert s["price_per_meal"] == 2.0 and s["cost_total"] == 20.0
