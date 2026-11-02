"""Personnalisation : nom, sous-titre et logo choisis dans Paramètres s'affichent partout, y compris avant connexion."""

from playwright.sync_api import expect

from .conftest import aller
from .images_factices import png_minimal


def carte(page):
    return page.locator(".card", has_text="Nom, sous-titre et logo de votre cantine")


def champ_carte(page, libelle):
    return carte(page).locator(f"xpath=.//label[normalize-space()='{libelle}']/following-sibling::input")


def test_ecran_de_connexion_neutre_par_defaut(page):
    page.goto(page.base)
    page.get_by_text("Première utilisation").wait_for()
    assert page.title() == "Cantine"
    assert page.locator("#auth h2").inner_text() == "Cantine"
    assert page.locator("#auth img.authlogo").get_attribute("src").endswith("/static/img/icone.svg")


def test_nom_et_sous_titre_partout(admin):
    page = admin
    aller(page, "Paramètres")
    champ_carte(page, "Nom").fill("Cantine du Port")
    champ_carte(page, "Sous-titre (facultatif)").fill("Ville de Test")
    carte(page).get_by_role("button", name="Enregistrer le nom et le sous-titre").click()
    # on attend le résultat lui-même (et non un message « Enregistré », qui figure aussi dans d'autres textes de la page)
    expect(page.locator("header .brand")).to_have_text("Cantine du Port")
    expect(page).to_have_title("Cantine du Port")

    page.reload()  # le choix est conservé
    page.locator("header .brand").wait_for()
    assert page.locator("header .brand").inner_text() == "Cantine du Port"

    page.get_by_role("button", name="Déconnexion").click()  # et visible avant toute connexion
    page.locator("#auth h2").wait_for()
    assert page.locator("#auth h2").inner_text() == "Cantine du Port"
    page.get_by_text("Ville de Test").wait_for()


def test_logo_envoye_puis_retire(admin, tmp_path):
    page = admin
    fichier = tmp_path / "logo.png"
    fichier.write_bytes(png_minimal())
    aller(page, "Paramètres")
    carte(page).locator("input[type=file]").set_input_files(str(fichier))
    page.wait_for_function("document.querySelector('header .logo').src.includes('/api/branding/logo')")
    # l'image est bien chargée (elle arrive après l'attribut src : on attend, sans lire trop tôt)
    page.wait_for_function("document.querySelector('header .logo').naturalWidth === 40")
    assert "/api/branding/logo" in page.locator("#favicon").get_attribute("href")

    carte(page).get_by_role("button", name="Retirer le logo").click()
    page.wait_for_function("document.querySelector('header .logo').src.endsWith('/static/img/icone.svg')")


def test_un_fichier_qui_n_est_pas_une_image_est_refuse(admin, tmp_path):
    page = admin
    faux = tmp_path / "faux.png"
    faux.write_text("<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>")
    aller(page, "Paramètres")
    with page.expect_event("dialog") as d:
        carte(page).locator("input[type=file]").set_input_files(str(faux))
    assert "PNG, JPEG ou WebP" in d.value.message
    d.value.accept()
    assert page.evaluate("document.querySelector('header .logo').src").endswith("/static/img/icone.svg")
