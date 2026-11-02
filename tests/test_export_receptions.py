"""Export des réceptions d'une période : CSV des lignes avec indicateurs, archive zip des PDF."""

import csv
import io
import zipfile

import pytest

from cgrs.services.exports import CSV_HEADER, check_period, csv_text, line_row, safe_name, zip_member_name

# ---------- règles pures ----------


def test_periode_valide():
    assert check_period("2030-01-01", "2030-01-31", "facture") == ("2030-01-01", "2030-01-31", "facture")
    assert check_period("2030-01-05", "2030-01-05", "tous")[:2] == ("2030-01-05", "2030-01-05")  # un seul jour


@pytest.mark.parametrize(
    "debut, fin, type_, message",
    [
        ("2030-02-01", "2030-01-01", "facture", "après la date de fin"),
        ("01/01/2030", "2030-01-31", "facture", "AAAA-MM-JJ"),
        ("", "2030-01-31", "facture", "AAAA-MM-JJ"),
        ("2030-02-30", "2030-03-01", "facture", "AAAA-MM-JJ"),
        ("2030-01-01", "2030-01-31", "avoir", "Type inconnu"),
    ],
)
def test_periode_refusee(debut, fin, type_, message):
    with pytest.raises(ValueError, match=message):
        check_period(debut, fin, type_)


def ligne(**kw):
    base = {
        "date": "2030-01-10",
        "kind": "facture",
        "order_ref": "F-1",
        "supplier_name": "Ferme du Test",
        "product_id": 1,
        "product_ref": "CAR01",
        "product_name": "Carottes",
        "category": "Légumes",
        "gamme": "1",
        "qty": 12.5,
        "unit": "kg",
        "unit_price": 1.2,
        "total_ht": None,
        "label_egalim": "bio",
        "label_detail": "AB",
        "provenance": "loire_atlantique",
        "direct_producteur": 1,
        "commerce_equitable": 0,
        "source_file_name": "facture.pdf",
    }
    return {**base, **kw}


def test_ligne_avec_indicateurs():
    row = dict(zip(CSV_HEADER, line_row(ligne())))
    assert row["type"] == "facture" and row["fournisseur"] == "Ferme du Test"
    assert row["quantite"] == "12,5" and row["prix_unitaire_ht"] == "1,2"  # virgule décimale : s'ouvre dans Excel
    assert row["montant_ht"] == "15"  # quantité x prix, arrondi au centime
    assert (row["bio"], row["egalim"], row["local"], row["direct_producteur"], row["commerce_equitable"]) == (
        "oui",
        "oui",
        "oui",
        "oui",
        "non",
    )
    assert row["provenance"] == "Loire-Atlantique" and row["label_egalim"] == "bio" and row["detail_label"] == "AB"


def test_indicateurs_comme_dans_les_statistiques():
    r = lambda **kw: dict(zip(CSV_HEADER, line_row(ligne(**kw))))  # noqa: E731
    assert (r(label_egalim="autre")["bio"], r(label_egalim="autre")["egalim"]) == ("non", "oui")
    assert (r(label_egalim="sans")["bio"], r(label_egalim="sans")["egalim"]) == ("non", "non")
    assert r(provenance="france")["local"] == "non" and r(provenance="cc_nozay")["local"] == "oui"


def test_montant_saisi_prioritaire_et_ligne_sans_produit():
    r = dict(zip(CSV_HEADER, line_row(ligne(total_ht=20.0, product_id=None, product_name=None, label="Pommes vrac"))))
    assert r["montant_ht"] == "20"
    assert r["produit"] == "Pommes vrac"
    assert (r["bio"], r["local"], r["provenance"], r["label_egalim"]) == ("", "", "", "")  # inconnus : vides


def test_csv_en_tete_et_separateur():
    rows = list(csv.reader(io.StringIO(csv_text([line_row(ligne())])), delimiter=";"))
    assert rows[0] == CSV_HEADER and len(rows[1]) == len(CSV_HEADER)


def test_noms_de_fichiers_du_zip():
    used = set()
    o = {"date": "2030-01-10", "supplier_name": "Ferme d'Élodie & fils", "ref": "FAC/0042", "source_file": "ab12_x.pdf"}
    assert zip_member_name(o, used) == "2030-01-10_Ferme-d-Elodie-fils_FAC-0042.pdf"
    assert zip_member_name(o, used) == "2030-01-10_Ferme-d-Elodie-fils_FAC-0042-2.pdf"  # jamais deux fois le même nom
    assert (
        zip_member_name({"date": None, "supplier_name": None, "ref": None, "source_file": None}, used)
        == "sans-date.pdf"
    )
    assert safe_name("../../etc/passwd") == "etc-passwd"


# ---------- API ----------


@pytest.fixture(scope="module")
def jeu(client):
    """Fournisseur, produit et réceptions de mars 2031 (dates propres à ces tests : la base est partagée)."""
    from cgrs.config import UPLOADS

    UPLOADS.mkdir(exist_ok=True)
    for nom in ("aaaaaaaaaaaa_f1.pdf", "bbbbbbbbbbbb_bl1.pdf", "cccccccccccc_hors.pdf"):
        (UPLOADS / nom).write_bytes(b"%PDF-1.4 " + nom.encode())
    fid = client.post("/api/suppliers", json={"name": "Ferme Export"}).json()["id"]
    pid = client.post(
        "/api/products",
        json={
            "name": "Carottes export",
            "ref": "CE1",
            "supplier_id": fid,
            "unit": "kg",
            "unit_price": 1.5,
            "label_egalim": "bio",
            "provenance": "pays_loire",
            "direct_producteur": True,
            "category": "Légumes",
            "gamme": "1",
        },
    ).json()["id"]

    def reception(**kw):
        corps = {"supplier_id": fid, "lines": [{"product_id": pid, "qty": 10, "unit": "kg", "unit_price": 1.5}]}
        r = client.post("/api/orders", json={**corps, **kw})
        assert r.status_code == 200, r.text

    reception(kind="facture", ref="F-EXP-1", date="2031-03-05", source_file="aaaaaaaaaaaa_f1.pdf")
    reception(kind="facture", ref="F-EXP-2", date="2031-03-06", source_file="aaaaaaaaaaaa_f1.pdf")  # même PDF
    reception(kind="facture", ref="F-EXP-3", date="2031-03-07")  # sans fichier
    reception(kind="livraison", ref="BL-EXP-1", date="2031-03-08", source_file="bbbbbbbbbbbb_bl1.pdf")
    reception(kind="facture", ref="F-EXP-HORS", date="2031-05-01", source_file="cccccccccccc_hors.pdf")
    return {"fid": fid, "pid": pid}


def lire_csv(reponse):
    assert reponse.content.startswith(b"\xef\xbb\xbf")  # BOM UTF-8 pour Excel
    return list(csv.DictReader(io.StringIO(reponse.content.decode("utf-8-sig")), delimiter=";"))


def test_csv_des_factures_de_la_periode(client, jeu):
    r = client.get("/api/export/receptions/lignes.csv", params={"date_from": "2031-03-01", "date_to": "2031-03-31"})
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    lignes = lire_csv(r)
    assert [l["reference_reception"] for l in lignes] == [
        "F-EXP-1",
        "F-EXP-2",
        "F-EXP-3",
    ]  # factures de mars, pas le BL ni mai
    premiere = lignes[0]
    assert premiere["produit"] == "Carottes export" and premiere["fournisseur"] == "Ferme Export"
    assert (premiere["quantite"], premiere["prix_unitaire_ht"], premiere["montant_ht"]) == ("10", "1,5", "15")
    assert (premiere["bio"], premiere["egalim"], premiere["local"], premiere["direct_producteur"]) == ("oui",) * 4
    assert premiere["provenance"] == "Pays de la Loire et limitrophes" and premiere["fichier_pdf"] == "f1.pdf"


def test_csv_types_et_bornes(client, jeu):
    p = {"date_from": "2031-03-05", "date_to": "2031-03-05"}  # bornes incluses
    assert [l["reference_reception"] for l in lire_csv(client.get("/api/export/receptions/lignes.csv", params=p))] == [
        "F-EXP-1"
    ]
    tous = lire_csv(
        client.get("/api/export/receptions/lignes.csv", params={**p, "date_to": "2031-03-08", "kind": "tous"})
    )
    assert [l["type"] for l in tous] == ["facture", "facture", "facture", "bon de livraison"]
    bl = lire_csv(
        client.get("/api/export/receptions/lignes.csv", params={**p, "date_to": "2031-03-31", "kind": "livraison"})
    )
    assert [l["reference_reception"] for l in bl] == ["BL-EXP-1"]
    vide = client.get("/api/export/receptions/lignes.csv", params={"date_from": "2032-01-01", "date_to": "2032-01-31"})
    assert vide.status_code == 200 and lire_csv(vide) == []  # période sans réception : CSV avec l'en-tête seul


def test_zip_des_pdf_un_exemplaire_par_fichier(client, jeu):
    r = client.get("/api/export/receptions/pdf.zip", params={"date_from": "2031-03-01", "date_to": "2031-03-31"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert z.namelist() == ["2031-03-05_Ferme-Export_F-EXP-1.pdf"]  # F-EXP-2 : même PDF ; F-EXP-3 : pas de fichier
    assert z.read(z.namelist()[0]).startswith(b"%PDF-1.4")
    assert r.headers["x-documents-sans-fichier"] == "1"
    tous = client.get(
        "/api/export/receptions/pdf.zip", params={"date_from": "2031-03-01", "date_to": "2031-03-31", "kind": "tous"}
    )
    assert len(zipfile.ZipFile(io.BytesIO(tous.content)).namelist()) == 2  # la facture et le bon de livraison


def test_zip_sans_document_ou_sans_pdf(client, jeu):
    r = client.get("/api/export/receptions/pdf.zip", params={"date_from": "2032-01-01", "date_to": "2032-01-31"})
    assert r.status_code == 404 and "Aucun document" in r.json()["detail"]
    r = client.get("/api/export/receptions/pdf.zip", params={"date_from": "2031-03-07", "date_to": "2031-03-07"})
    assert r.status_code == 404 and "Aucun PDF conservé" in r.json()["detail"]


@pytest.mark.parametrize("chemin", ["lignes.csv", "pdf.zip"])
def test_periode_invalide_refusee(client, chemin):
    r = client.get(f"/api/export/receptions/{chemin}", params={"date_from": "2031-04-01", "date_to": "2031-03-01"})
    assert r.status_code == 400 and "après la date de fin" in r.json()["detail"]
    assert client.get(f"/api/export/receptions/{chemin}").status_code == 422  # dates obligatoires


def test_acces_reserve_aux_utilisateurs_connectes(client):
    from fastapi.testclient import TestClient

    from cgrs.application import app

    anonyme = TestClient(app, headers={"X-Requested-With": "cgrs"})
    for chemin in ("lignes.csv", "pdf.zip"):
        r = anonyme.get(f"/api/export/receptions/{chemin}", params={"date_from": "2031-03-01", "date_to": "2031-03-31"})
        assert r.status_code == 401
