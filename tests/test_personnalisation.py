"""Personnalisation : nom, sous-titre, logo. Règles pures, puis API (lecture publique, écriture réservée à l'administrateur)."""

import struct
import zlib

import pytest

from cgrs.services.branding import DEFAULT_NAME, NAME_MAX, clean_name, clean_subtitle, image_type


def png(largeur=2, hauteur=2):
    """Plus petit PNG valide possible (pixels rouges)."""

    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))

    brut = b"".join(b"\x00" + b"\xff\x00\x00" * largeur for _ in range(hauteur))
    return (
        b"\x89PNG\r\n\x1a\n"
        + bloc(b"IHDR", struct.pack(">IIBBBBB", largeur, hauteur, 8, 2, 0, 0, 0))
        + bloc(b"IDAT", zlib.compress(brut))
        + bloc(b"IEND", b"")
    )


# ---------- règles pures ----------


@pytest.mark.parametrize(
    "saisi, attendu",
    [
        ("Cantine de Saffré", "Cantine de Saffré"),
        ("  Cantine   du   Port ", "Cantine du Port"),
        ("", DEFAULT_NAME),
        ("   ", DEFAULT_NAME),
        (None, DEFAULT_NAME),
        ("x" * 200, "x" * NAME_MAX),
    ],
)
def test_nom_affiche(saisi, attendu):
    assert clean_name(saisi) == attendu


def test_sous_titre_facultatif_et_borne():
    assert clean_subtitle(None) == ""
    assert clean_subtitle("  Restaurant   scolaire ") == "Restaurant scolaire"
    assert len(clean_subtitle("y" * 500)) == 80


@pytest.mark.parametrize(
    "contenu, type_attendu",
    [
        (png(), "image/png"),
        (b"\xff\xd8\xff\xe0" + b"0" * 20, "image/jpeg"),
        (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
        (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", None),  # SVG refusé
        (b"GIF89a....", None),
        (b"%PDF-1.4", None),
        (b"", None),
    ],
)
def test_type_d_image_reconnu_au_contenu(contenu, type_attendu):
    assert image_type(contenu) == type_attendu


# ---------- API ----------


@pytest.fixture()
def anonyme(client):
    from fastapi.testclient import TestClient

    from cgrs.application import app

    return TestClient(app, headers={"X-Requested-With": "cgrs"})  # sans session


@pytest.fixture(autouse=True)
def remise_a_zero(client):
    yield
    client.delete("/api/branding/logo")
    client.put("/api/branding", json={"name": "", "subtitle": ""})


def test_valeurs_par_defaut_neutres(client, anonyme):
    assert anonyme.get("/api/branding").json() == {"name": DEFAULT_NAME, "subtitle": "", "logo": None}
    assert anonyme.get("/api/branding/logo").status_code == 404


def test_lecture_publique_ecriture_reservee_a_l_administrateur(client, anonyme):
    assert anonyme.put("/api/branding", json={"name": "Pirate"}).status_code == 401
    assert anonyme.post("/api/branding/logo", files={"file": ("l.png", png(), "image/png")}).status_code == 401
    assert anonyme.delete("/api/branding/logo").status_code == 401
    assert anonyme.get("/api/branding").json()["name"] == DEFAULT_NAME


def test_nom_et_sous_titre_enregistres(client, anonyme):
    r = client.put("/api/branding", json={"name": "  Cantine   du Port ", "subtitle": "Ville de Test"})
    assert r.status_code == 200 and r.json()["name"] == "Cantine du Port"
    vu = anonyme.get("/api/branding").json()
    assert (vu["name"], vu["subtitle"]) == ("Cantine du Port", "Ville de Test")


def test_le_nom_est_aussi_un_nom_de_cantine_pour_l_import(client):
    from cgrs.routes.settings import get_client_names

    client.put("/api/branding", json={"name": "Cantine du Port"})
    assert "Cantine du Port" in get_client_names()
    # la liste modifiable dans Paramètres ne contient que ce qui a été saisi
    assert "Cantine du Port" not in client.get("/api/settings").json()["client_names"]


def test_logo_envoye_servi_puis_retire(client, anonyme):
    r = client.post("/api/branding/logo", files={"file": ("mon logo.png", png(), "image/png")})
    assert r.status_code == 200 and r.json()["logo"].startswith("/api/branding/logo?v=")
    img = anonyme.get("/api/branding/logo")
    assert img.status_code == 200 and img.headers["content-type"] == "image/png" and img.content == png()
    assert "default-src 'none'" in img.headers["content-security-policy"]
    assert client.delete("/api/branding/logo").json()["logo"] is None
    assert anonyme.get("/api/branding/logo").status_code == 404


def test_logo_refuse_si_ce_n_est_pas_une_image_ou_trop_gros(client):
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
    assert client.post("/api/branding/logo", files={"file": ("a.png", svg, "image/png")}).status_code == 400
    assert (
        client.post("/api/branding/logo", files={"file": ("a.png", b"pas une image", "image/png")}).status_code == 400
    )
    gros = png() + b"0" * (512 * 1024)
    assert client.post("/api/branding/logo", files={"file": ("a.png", gros, "image/png")}).status_code == 413
    assert client.get("/api/branding").json()["logo"] is None  # rien n'a été enregistré
