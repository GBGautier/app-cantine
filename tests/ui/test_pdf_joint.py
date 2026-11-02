"""Joindre un PDF à la main à une réception (nouvelle ou existante) : il doit être enregistré."""

from .conftest import aller
from .pdf_factice import pdf_minimal


def _commande(api):
    fid = api.post("/api/suppliers", {"name": "Ferme Joint"})["id"]
    return api.post(
        "/api/orders", {"supplier_id": fid, "ref": "F-1", "kind": "facture", "date": "2030-03-05", "lines": []}
    )["id"]


def _orders(page):
    return page.context.request.get(page.base + "/api/orders").json()


def test_joindre_un_pdf_a_une_facture_existante(admin, api, tmp_path):
    page = admin
    oid = _commande(api)
    pdf = tmp_path / "facture.pdf"
    pdf.write_bytes(pdf_minimal(["Facture F-1"]))
    aller(page, "Réceptions")
    page.get_by_text("F-1").first.click()
    page.locator(".modal").get_by_role("button", name="Modifier").click()
    page.locator(".modal input[type=file]").set_input_files(str(pdf))
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.locator(".modal").wait_for(state="detached")
    o = [x for x in _orders(page) if x["id"] == oid][0]
    assert o["source_file"] and o["source_file"].endswith("facture.pdf"), o


def test_joindre_un_pdf_a_une_nouvelle_reception(admin, api, tmp_path):
    page = admin
    api.post("/api/suppliers", {"name": "Ferme Neuve"})
    pdf = tmp_path / "bl.pdf"
    pdf.write_bytes(pdf_minimal(["BL"]))
    aller(page, "Réceptions")
    page.get_by_role("button", name="+ Saisie manuelle").click()
    page.locator(".modal select").first.select_option(label="Ferme Neuve")
    page.locator(".modal input[type=file]").set_input_files(str(pdf))
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.locator(".modal").wait_for(state="detached")
    assert any((x["source_file"] or "").endswith("bl.pdf") for x in _orders(page))
