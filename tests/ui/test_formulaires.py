"""Formulaires de saisie : repas, recettes, inventaire de stock, import d'un PDF (fictif)."""

from .conftest import aller, champ
from .pdf_factice import pdf_minimal


def modal_enregistrer(page):
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.locator(".modal").wait_for(state="detached")


def test_saisie_d_un_repas(admin, api):
    page = admin
    aller(page, "Repas")
    page.get_by_role("button", name="+ Repas").click()
    champ(page, "Jour *").fill("2030-02-12")
    champ(page, "Adultes").fill("7")
    page.locator(".modal").get_by_placeholder("Libellé du plat…").nth(1).fill("Rôti de dinde")
    page.locator(".modal").get_by_placeholder("Libellé du plat…").nth(4).fill("Compote")
    modal_enregistrer(page)
    repas = page.context.request.get(page.base + "/api/meals").json()
    assert [(m["date"], m["nb_adultes"], m["plat"], m["dessert"]) for m in repas] == [
        ("2030-02-12", 7, "Rôti de dinde", "Compote")
    ]
    aller(page, "Repas")
    page.get_by_text("Rôti de dinde").wait_for()


def test_saisie_d_une_recette(admin):
    page = admin
    aller(page, "Recettes")
    page.get_by_role("button", name="+ Recette").click()
    page.locator(".modal").get_by_placeholder("Nom de la recette *").fill("Gratin de courgettes")
    modal_enregistrer(page)
    recettes = page.context.request.get(page.base + "/api/recipes").json()
    recettes = recettes if isinstance(recettes, list) else recettes["items"]
    assert [r["name"] for r in recettes] == ["Gratin de courgettes"]
    aller(page, "Recettes")
    page.get_by_text("Gratin de courgettes").wait_for()


def test_recette_sans_nom_refusee(admin):
    page = admin
    aller(page, "Recettes")
    page.get_by_role("button", name="+ Recette").click()
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.locator(".modal").wait_for()  # le formulaire reste ouvert
    assert page.context.request.get(page.base + "/api/recipes").json() in ([], {"items": []})


def test_inventaire_ajuste_le_stock(admin, api):
    page = admin
    fid = api.post("/api/suppliers", {"name": "Ferme Test"})["id"]
    pid = api.post("/api/products", {"name": "Carottes", "supplier_id": fid, "unit": "kg", "unit_price": 1.5})["id"]
    api.post(
        "/api/orders",
        {
            "supplier_id": fid,
            "ref": "BL-1",
            "date": "2030-01-10",
            "lines": [{"product_id": pid, "qty": 10, "unit": "kg"}],
        },
    )
    aller(page, "Stocks")
    ligne = page.locator("tbody tr", has_text="Carottes")
    ligne.get_by_role("button", name="Inventaire").click()
    champ(page, "Quantité réelle (kg)").fill("8")
    champ(page, "Motif").fill("perte")
    modal_enregistrer(page)
    stock = page.context.request.get(page.base + "/api/stock").json()
    assert [(r["name"], r["stock"]) for r in stock["rows"]] == [("Carottes", 8)]
    assert [(a["qty"], a["reason"]) for a in stock["adjustments"]] == [(-2, "perte")]


def test_import_d_un_pdf_fictif(admin, api, tmp_path):
    page = admin
    api.post("/api/suppliers", {"name": "Ferme Test"})
    pdf = tmp_path / "bl.pdf"
    pdf.write_bytes(
        pdf_minimal(
            [
                "Bon de livraison N° BL-2030-001",
                "Date : 15/01/2030",
                "Réf. Désignation Qté Prix Montant",
                "CAR01 Carottes bio 10,00 kg 1,50 15,00",
                "POM02 Pommes de terre 20,00 kg 0,80 16,00",
                "Total HT 31,00",
            ]
        )
    )
    aller(page, "Réceptions")
    page.locator("input[type=file]").first.set_input_files(str(pdf))
    page.locator(".modal").wait_for()
    assert champ(page, "Référence").input_value() == "BL-2030-001"
    assert champ(page, "Date").input_value() == "2030-01-15"
    assert float(champ(page, "Total HT (€)").input_value()) == 31.0
    page.locator(".modal").get_by_text("2 ligne(s) lue(s)").wait_for()
    valeurs = [i.input_value() for i in page.locator(".modal tbody input").all()]
    assert "CAR01 Carottes bio" in valeurs and "POM02 Pommes de terre" in valeurs


def test_export_des_receptions_d_une_periode(admin, api, tmp_path):
    import csv
    import io
    import zipfile

    page = admin
    fid = api.post("/api/suppliers", {"name": "Ferme Export"})["id"]
    pid = api.post(
        "/api/products",
        {"name": "Carottes", "supplier_id": fid, "unit": "kg", "unit_price": 1.5, "label_egalim": "bio"},
    )["id"]
    oid = api.post(
        "/api/orders",
        {
            "supplier_id": fid,
            "ref": "F-2030-1",
            "kind": "facture",
            "date": "2030-03-05",
            "lines": [{"product_id": pid, "qty": 10, "unit": "kg", "unit_price": 1.5}],
        },
    )["id"]
    r = page.context.request.post(
        f"{page.base}/api/orders/{oid}/upload-pdf",
        multipart={
            "file": {"name": "f.pdf", "mimeType": "application/pdf", "buffer": pdf_minimal(["Facture F-2030-1"])}
        },
        headers={"X-Requested-With": "cgrs"},
    )
    assert r.ok, r.text()

    aller(page, "Réceptions")
    page.get_by_role("button", name="Exporter…").click()
    champ(page, "Du").fill("2030-03-01")
    champ(page, "Au").fill("2030-03-31")

    with page.expect_download() as dl:
        page.get_by_role("button", name="Télécharger les PDF (archive zip)").click()
    assert dl.value.suggested_filename == "pdf_factures_2030-03-01_2030-03-31.zip"
    assert zipfile.ZipFile(dl.value.path()).namelist() == ["2030-03-05_Ferme-Export_F-2030-1.pdf"]

    with page.expect_download() as dl:
        page.locator(".modal").get_by_role("button", name="Télécharger le CSV des lignes").click()
    lignes = list(csv.DictReader(io.StringIO(open(dl.value.path(), encoding="utf-8-sig").read()), delimiter=";"))
    assert [(l["reference_reception"], l["produit"], l["quantite"], l["bio"]) for l in lignes] == [
        ("F-2030-1", "Carottes", "10", "oui")
    ]


def test_export_d_une_periode_sans_document_affiche_le_message(admin):
    page = admin
    aller(page, "Réceptions")
    page.get_by_role("button", name="Exporter…").click()
    champ(page, "Du").fill("2030-03-01")
    champ(page, "Au").fill("2030-03-31")
    page.get_by_role("button", name="Télécharger les PDF (archive zip)").click()
    page.get_by_text("Aucun document (factures)").wait_for()  # message lisible, la fenêtre reste ouverte
    champ(page, "Au").fill("2029-01-01")
    page.locator(".modal").get_by_role("button", name="Télécharger le CSV des lignes").click()
    page.get_by_text("La date de début est après la date de fin").wait_for()
