"""PDF des statistiques : répartitions sans chevauchement (tout tient dans la page) et lignes de repas complètes."""

import pdfplumber

from .conftest import aller


def test_pdf_des_statistiques_complet(admin, api, tmp_path):
    page = admin
    categories = [
        "Légumes",
        "Fruits",
        "Viandes",
        "Poissons",
        "Laitiers",
        "Épicerie",
        "Boissons",
        "Pain",
        "Surgelés",
        "Oeufs",
        "Condiments",
        "Divers",
    ]
    fournisseurs = [
        api.post("/api/suppliers", {"name": f"Fournisseur au nom vraiment très long numéro {i}"})["id"]
        for i in range(12)
    ]
    produits = []
    for i, cat in enumerate(categories):
        produits.append(
            api.post(
                "/api/products",
                {
                    "name": f"Produit {i}",
                    "supplier_id": fournisseurs[i],
                    "unit": "kg",
                    "unit_price": 2.0 + i,
                    "category": cat,
                    "label_egalim": "bio" if i % 2 else "sans",
                },
            )["id"]
        )
    for d in range(1, 31):
        api.post(
            "/api/meals",
            {
                "date": f"2030-03-{d:02d}",
                "nb_adultes": 10 + d,
                "statut": "passe",
                "entree": "Salade de carottes",
                "plat": "Sauté de porc aux légumes",
                "dessert": "Compote de pommes",
                "items": [{"product_id": produits[d % 12], "qty": 5, "unit": "kg"}],
            },
        )
    aller(page, "Statistiques")
    with page.expect_download() as dl:
        page.get_by_role("button", name="Exporter en PDF").click()
    fichier = tmp_path / "stats.pdf"
    dl.value.save_as(str(fichier))
    with pdfplumber.open(fichier) as pdf:
        texte = "\n".join(p.extract_text() or "" for p in pdf.pages)
        for p in pdf.pages:  # rien ne déborde de la page, ni sur le pied de page
            for mot in p.extract_words():
                assert mot["x1"] <= p.width - 10 and mot["x0"] >= 10, mot
                if not mot["text"].startswith(("Page", "Cantine", "/")) and mot["top"] > p.height - 40:
                    assert mot["bottom"] < p.height - 20, mot
    assert "Salade de carottes" in texte and "Sauté de porc aux légumes" in texte  # menu de chaque repas
    assert "% bio" in texte and "% local" in texte and "Convives" in texte
    assert "30 repas" not in texte and "Repas valorisés" in texte
