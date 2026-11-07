"""Bilan mensuel : ajouté à l'export PDF de la page Statistiques."""

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


def test_export_pdf_des_statistiques_contient_le_bilan(admin, api, tmp_path):
    page = admin
    _donnees(api)
    aller(page, "Statistiques")
    page.evaluate("store.set('cgrs.st', '2031-10-31'); render()")
    page.wait_for_function("document.querySelector('#st')?.value === '2031-10-31'")
    with page.expect_download() as dl:
        page.get_by_role("button", name="Exporter en PDF").click()
    fichier = tmp_path / "stats.pdf"
    dl.value.save_as(str(fichier))
    with pdfplumber.open(fichier) as pdf:
        texte = "\n".join(p.extract_text() or "" for p in pdf.pages)
    assert "Suivi des approvisionnements" in texte and "Octobre 2031" in texte
    assert "Part de bio, toutes denrees" in texte or "Part de bio, toutes denrées" in texte
    assert "Produits bio par famille" in texte and "Origine par famille de produits" in texte
    assert "Repartition par gamme" in texte
    assert "Evolution mois par mois" in texte and "Engagements du marche" in texte


def test_tarif_repas_dans_les_parametres(admin, api):
    page = admin
    aller(page, "Paramètres")
    champ = page.locator("input[type=number][step='0.01']").first
    champ.fill("2.5")
    champ.locator("xpath=following-sibling::button").click()
    page.wait_for_timeout(300)
    assert api.get("/api/settings")["tarif_repas"] == 2.5
