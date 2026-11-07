"""Bilan mensuel : la page compare le mois au cumul depuis septembre, et l'export PDF reprend les rubriques du suivi."""

import pdfplumber

from .conftest import aller


def _donnees(api):
    f = api.post("/api/suppliers", {"name": "Ferme Bilan", "direct_producteur": 1})["id"]
    p = api.post(
        "/api/products",
        {
            "name": "Carottes bilan",
            "supplier_id": f,
            "unit": "kg",
            "unit_price": 2.0,
            "category": "Légumes",
            "label_egalim": "bio",
            "provenance": "france",
            "gamme": "1",
        },
    )["id"]
    for jour in ("2031-09-10", "2031-10-10"):
        api.post(
            "/api/orders",
            {
                "supplier_id": f,
                "kind": "facture",
                "date": jour,
                "lines": [{"product_id": p, "qty": 100, "unit": "kg", "unit_price": 2.0}],
            },
        )
    api.post(
        "/api/meals",
        {
            "date": "2031-10-11",
            "nb_elementaires": 50,
            "statut": "passe",
            "items": [{"product_id": p, "qty": 40, "unit": "kg"}],
        },
    )


def test_page_bilan_et_export_pdf(admin, api, tmp_path):
    page = admin
    _donnees(api)
    aller(page, "Bilan mensuel")
    page.locator("input[type=month]").fill("2031-10")
    page.get_by_text("Octobre 2031", exact=False).first.wait_for()
    corps = page.locator("main, body").first.inner_text()
    assert "comparé au cumul depuis septembre 2031" in corps
    assert "Part de bio, toutes denrées" in corps and "Approvisionnement direct de producteurs" in corps
    assert "Évolution mois par mois" in corps and "septembre 2031" in corps
    with page.expect_download() as dl:
        page.get_by_role("button", name="Exporter en PDF").click()
    fichier = tmp_path / "bilan.pdf"
    dl.value.save_as(str(fichier))
    with pdfplumber.open(fichier) as pdf:
        texte = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Suivi des approvisionnements" in texte and "Octobre 2031" in texte
    assert "Part de bio, toutes denrees" in texte or "Part de bio, toutes denrées" in texte
    assert "Evolution mois par mois" in texte and "Engagements du marche" in texte


def test_tarif_repas_dans_les_parametres(admin, api):
    page = admin
    aller(page, "Paramètres")
    champ = page.locator("input[type=number][step='0.01']").first
    champ.fill("2.5")
    champ.locator("xpath=following-sibling::button").click()
    page.wait_for_timeout(300)
    assert api.get("/api/settings")["tarif_repas"] == 2.5
