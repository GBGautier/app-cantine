"""Parcours utilisateur dans un vrai navigateur."""
import re

from .conftest import MOT_DE_PASSE, aller, champ

PAGES = ["Statistiques", "Réceptions", "Fournisseurs", "Produits", "Stocks", "Recettes", "Repas", "Grammages", "Paramètres"]


def connecter(page, identifiant, mot_de_passe):
    page.locator("#auth input[type=text]").fill(identifiant)
    page.locator("#auth input[type=password]").first.fill(mot_de_passe)
    page.locator("#auth button.p").click()


def espaces(texte):
    return re.sub(r"\s+", " ", texte.replace(" ", " ").replace("\xa0", " ")).strip()


def test_premiere_utilisation_cree_le_compte_administrateur(page):
    page.goto(page.base)
    page.get_by_text("Première utilisation").wait_for()
    page.locator("#auth input[type=text]").fill("admin")
    pw = page.locator("#auth input[type=password]")
    pw.nth(0).fill(MOT_DE_PASSE)
    pw.nth(1).fill("autre-chose")
    page.get_by_role("button", name="Créer le compte").click()
    page.get_by_text("Les deux mots de passe ne correspondent pas").wait_for()
    pw.nth(1).fill(MOT_DE_PASSE)
    page.get_by_role("button", name="Créer le compte").click()
    page.locator("#me").get_by_text("admin").wait_for()
    assert {t.strip() for t in page.locator("#nav a").all_inner_texts()} == set(PAGES)


def test_connexion_refusee_puis_acceptee_puis_deconnexion(page, api):
    api.post("/api/auth/setup", {"username": "admin", "password": MOT_DE_PASSE})
    api.post("/api/auth/logout")
    page.goto(page.base)
    connecter(page, "admin", "mauvais")
    page.get_by_text("Identifiant ou mot de passe incorrect").wait_for()
    connecter(page, "admin", MOT_DE_PASSE)
    page.locator("#nav").wait_for()
    page.get_by_role("button", name="Déconnexion").click()
    page.locator("#auth input[type=password]").wait_for()
    assert page.locator("#shell").is_hidden()


def test_fournisseur_creation_modification_suppression(admin):
    page = admin
    aller(page, "Fournisseurs")
    page.get_by_role("button", name="+ Fournisseur").click()
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.get_by_text("Le nom est obligatoire").wait_for()                     # refus lisible, la fenêtre reste ouverte
    champ(page, "Nom *").fill("Ferme du Test")
    champ(page, "Contact").fill("Mme Dupont")
    page.locator(".modal .chk", has_text="Lun").click()
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    ligne = page.locator("tr.clickable", has_text="Ferme du Test")
    ligne.wait_for()
    assert "Mme Dupont" in ligne.inner_text() and "Lun" in ligne.inner_text()

    ligne.get_by_title("Modifier").click()
    champ(page, "Nom *").fill("Ferme du Test 2")
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.locator("tr.clickable", has_text="Ferme du Test 2").wait_for()

    page.once("dialog", lambda d: d.accept())
    page.locator("tr.clickable", has_text="Ferme du Test 2").get_by_title("Supprimer").click()
    page.get_by_text("Aucun fournisseur").wait_for()


def test_produit_creation_et_recherche(admin, api):
    page = admin
    api.post("/api/suppliers", {"name": "Fournisseur A"})
    aller(page, "Produits")
    page.get_by_role("button", name="+ Produit").click()
    champ(page, "Nom *").fill("Carottes")
    champ(page, "Fournisseur").select_option(label="Fournisseur A")
    champ(page, "Prix unitaire HT (€)").fill("2.5")
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    ligne = page.locator("tr", has_text="Carottes")
    ligne.wait_for()
    assert "Fournisseur A" in ligne.inner_text()
    assert "2,50" in espaces(ligne.inner_text())
    page.get_by_placeholder("Rechercher un produit").fill("zzz")
    ligne.wait_for(state="hidden")


def test_reception_manuelle_calcule_le_total_et_met_a_jour_le_prix(admin, api):
    page = admin
    fid = api.post("/api/suppliers", {"name": "Fournisseur B"})["id"]
    api.post("/api/products", {"name": "Pommes", "supplier_id": fid, "unit": "kg", "unit_price": 1.0})
    aller(page, "Réceptions")
    page.get_by_role("button", name="+ Saisie manuelle").click()
    champ(page, "Fournisseur").select_option(label="Fournisseur B")
    champ(page, "Référence").fill("BL-001")
    ligne = page.locator(".modal tbody tr").first
    ligne.locator("select").select_option(label="Pommes")
    ligne.locator("input[type=number]").nth(0).fill("3")          # quantité
    ligne.locator("input[type=number]").nth(1).fill("2")          # prix unitaire
    assert ligne.locator("input[type=number]").nth(2).input_value() == "6.00"      # total de la ligne
    assert champ(page, "Total HT (€)").input_value() == "6.00"
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    ligne_liste = page.locator("tr.clickable", has_text="BL-001")
    ligne_liste.wait_for()
    assert "6,00" in espaces(ligne_liste.inner_text())
    page.get_by_text("Prix mis à jour").wait_for()                # le nouveau prix du produit est signalé
    aller(page, "Produits")
    assert "2,00" in espaces(page.locator("tr", has_text="Pommes").inner_text())


def test_toutes_les_pages_s_affichent_sans_erreur(admin, api):
    page = admin
    fid = api.post("/api/suppliers", {"name": "Fournisseur C"})["id"]
    pid = api.post("/api/products", {"name": "Lentilles", "supplier_id": fid})["id"]
    api.post("/api/meals", {"date": "2030-01-15", "plat": "Dahl de lentilles", "nb_adultes": 3,
                            "items": [{"product_id": pid, "qty": 2}]})
    api.post("/api/recipes", {"name": "Soupe test", "items": [{"product_id": pid, "qty_servi": 1}]})
    for nom in PAGES:
        aller(page, nom)
        page.wait_for_load_state("networkidle")
        assert "Erreur :" not in page.locator("#app").inner_text(), f"page {nom}"
    aller(page, "Repas")
    page.get_by_text("Dahl de lentilles").wait_for()
    aller(page, "Recettes")
    page.get_by_text("Soupe test").wait_for()


def test_utilisateur_en_lecture_seule_ne_peut_rien_modifier(admin, api, page):
    aller(page, "Paramètres")
    page.get_by_role("button", name="+ Utilisateur").click()
    champ(page, "Identifiant").fill("lecteur")
    champ(page, "Profil").select_option(value="reader")
    champ(page, "Mot de passe (8 caractères minimum)").fill(MOT_DE_PASSE)
    page.locator(".modal").get_by_role("button", name="Enregistrer").click()
    page.locator("tr.clickable", has_text="lecteur").wait_for()

    api.post("/api/auth/logout")
    page.reload()
    connecter(page, "lecteur", MOT_DE_PASSE)
    page.locator("#nav").wait_for()
    assert "Paramètres" not in page.locator("#nav").inner_text()
    aller(page, "Fournisseurs")
    assert page.get_by_role("button", name="+ Fournisseur").count() == 0
    aller(page, "Produits")
    assert page.get_by_role("button", name="+ Produit").count() == 0


def test_sauvegarde_telechargeable(admin):
    page = admin
    aller(page, "Paramètres")
    with page.expect_download() as dl:
        page.get_by_role("button", name="Sauvegarder toutes les données").click()
    assert dl.value.suggested_filename.endswith(".zip")
    import zipfile
    with zipfile.ZipFile(dl.value.path()) as z:
        assert "cantine.db" in z.namelist()


def test_navigation_par_adresse_et_page_inconnue(admin):
    page = admin
    page.goto(page.base + "/#products")
    page.locator("#nav a.on", has_text="Produits").wait_for()
    page.goto(page.base + "/#nimporte-quoi")                      # page inconnue : retour à la première page autorisée
    page.locator("#nav a.on", has_text="Statistiques").wait_for()
