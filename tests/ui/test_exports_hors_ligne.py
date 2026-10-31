"""Les exports PDF fonctionnent sans Internet : les bibliothèques sont embarquées, aucun site externe n'est contacté."""

from .conftest import aller, champ


def debut_du_fichier(telechargement, n=5):
    with open(telechargement.path(), "rb") as f:
        return f.read(n)


def test_bibliotheques_pdf_embarquees(admin):
    page = admin
    assert page.evaluate("typeof window.jspdf?.jsPDF") == "function"
    assert page.evaluate("typeof new window.jspdf.jsPDF().autoTable") == "function"  # plugin des tableaux


def test_export_pdf_des_statistiques_sans_internet(admin):
    page = admin
    aller(page, "Statistiques")
    with page.expect_download() as dl:
        page.get_by_role("button", name="Exporter en PDF").click()
    assert dl.value.suggested_filename.lower().endswith(".pdf")
    assert debut_du_fichier(dl.value) == b"%PDF-"


def test_liste_de_courses_pdf_sans_internet(admin, api):
    page = admin
    fid = api.post("/api/suppliers", {"name": "Fournisseur PDF"})["id"]
    pid = api.post("/api/products", {"name": "Haricots", "supplier_id": fid, "unit": "kg", "unit_price": 3.0})["id"]
    api.post("/api/meals", {"date": "2030-01-15", "plat": "Haricots", "items": [{"product_id": pid, "qty": 4}]})
    aller(page, "Repas")
    page.get_by_role("button", name="Liste de courses PDF").click()
    champ(page, "Du").fill("2030-01-01")
    champ(page, "Au").fill("2030-01-31")
    with page.expect_download() as dl:
        page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    assert debut_du_fichier(dl.value) == b"%PDF-"
