"""Régénère le PDF de présentation « Guide de l'application » (docs/guide-application.pdf).

L'application est lancée sur une base jetable remplie de données de démonstration ; chaque page est photographiée
par un vrai navigateur (Chromium) et les captures sont assemblées en diapositives (même charte verte que la
présentation d'origine). Aucune donnée réelle n'est utilisée.

    pip install playwright && playwright install chromium
    python docs/generer_guide.py

Pour faire évoluer la présentation : modifier DIAPOSITIVES ci-dessous (texte, capture associée) puis relancer.
"""

import base64
import datetime
import hashlib
import html
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "docs" / "guide-application.pdf"
EMPREINTE = RACINE / "docs" / "guide-application.empreinte"
MOT_DE_PASSE = "Motdepasse1"
H = {"X-Requested-With": "cgrs"}
MOIS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]

# ---------------------------------------------------------------------------------------------------------------
# Contenu : (rubrique, titre, capture, [(intitulé, texte), ...], légende)
#   capture : nom d'une capture produite par prendre_captures(), ou None (diapositive sans image)
# ---------------------------------------------------------------------------------------------------------------
DIAPOSITIVES = [
    (
        "PRÉSENTATION",
        "À quoi sert l’application ?",
        None,
        [
            (
                "Centraliser le quotidien de la cantine",
                "Fournisseurs, produits et prix, réceptions, repas et recettes, stocks, statistiques.",
            ),
            (
                "Lire les bons de livraison PDF",
                "Import de PDF, y compris les pages scannées (OCR), rattachement aux produits.",
            ),
            (
                "Suivre les prix et nos engagements",
                "Historique des prix ; bilan de la période comparé à nos engagements.",
            ),
            ("Calculer le coût matières", "Par repas et par convive, avec la part de bio et de local."),
            (
                "Interroger l’assistant IA",
                "Questions en langage courant sur les achats, simulation de remplacement de produits.",
            ),
        ],
        "",
    ),
    (
        "CONNEXION",
        "Connexion et profils",
        None,
        [
            ("Administrateur", "Tous les droits : gère les utilisateurs et les paramètres."),
            ("Lecture et écriture", "Mêmes droits que l’administrateur, sauf la modification des paramètres."),
            ("Lecture seule", "Consulte tout sans rien modifier."),
            ("Statistiques", "Accès à la seule page Statistiques, sans aucun prix."),
        ],
        "",
    ),
    (
        "FOURNISSEURS",
        "Tous les fournisseurs d’un coup d’œil",
        "fournisseurs",
        [
            ("Livraisons", "Jours de livraison et franco de chaque fournisseur."),
            ("Prise de commande", "Internet (lien direct), téléphone ou e-mail."),
            ("Catégories vendues", "Ce que fournit chacun : fruits, légumes, pêche…"),
            ("Produits et réceptions", "Leur nombre, par fournisseur."),
        ],
        "",
    ),
    (
        "FOURNISSEURS",
        "La fiche fournisseur",
        "fiche_fournisseur",
        [
            ("Contact et livraison", "Coordonnées, jours de livraison, franco (montant minimum)."),
            ("Prise de commande", "Lien vers le site, téléphone ou e-mail."),
            ("Catalogue", "Catégories vendues, provenance par défaut, direct producteur."),
            ("Avancé", "Mots-clés propres au fournisseur pour reconnaître ses PDF."),
        ],
        "Un fournisseur bien renseigné = des bons de livraison lus plus fiablement.",
    ),
    (
        "PRODUITS",
        "La liste des produits",
        "produits",
        [
            ("Recherche", "Par nom, référence ou fournisseur."),
            ("Filtres", "Catégorie (dont « À compléter » en rouge), fournisseur, favoris."),
            ("Tri par colonne", "Prix, catégorie, label…"),
            ("Favori en un clic", "L’étoile de la première colonne."),
        ],
        "",
    ),
    (
        "PRODUITS",
        "La fiche produit",
        "fiche_produit",
        [
            ("Identité et classement", "Référence, nom, fournisseur, catégorie et gamme."),
            ("Label et provenance", "EGalim (bio, label rouge…) ; de CC Nozay à l’international."),
            ("Prix", "Unité et prix unitaire HT, mis à jour par les réceptions."),
            ("Fiche technique", "PDF ou image liée au produit, consultable sans quitter l’application."),
        ],
        "Toute fiche s’ouvre en consultation : « Modifier » pour la déverrouiller.",
    ),
    (
        "PRODUITS",
        "L’historique des prix",
        "historique_prix",
        [
            ("Un relevé par réception", "Graphique et tableau : date, prix HT, origine de la réception."),
            ("Mise à jour automatique", "Le prix de la fiche change à l’enregistrement d’une réception."),
            ("Jamais saisi deux fois", "Le prix alimente la fiche produit, les statistiques et le coût des repas."),
        ],
        "",
    ),
    (
        "RÉCEPTIONS",
        "Les réceptions : bons de livraison et factures",
        "receptions",
        [
            ("Importer un PDF", "Lecture automatique des tableaux, des fournisseurs connus, OCR si page scannée."),
            ("Rattachement", "Référence reconnue : produit existant, sinon création en un clic."),
            (
                "Bon ou facture",
                "Le bon est provisoire ; la facture est définitive et remplace les bons correspondants.",
            ),
            ("Aucun double comptage", "Une facture déjà enregistrée n’est pas importée une seconde fois."),
        ],
        "",
    ),
    (
        "RÉCEPTIONS",
        "Chaque réception garde son PDF",
        "reception",
        [
            ("Lignes rattachées", "Référence, produit, nom, quantité, unité, prix HT et total."),
            ("PDF d’origine", "Consultable en un clic depuis la réception."),
            ("Saisie manuelle", "Un bon sans PDF se saisit ligne par ligne."),
            ("Prix mis à jour", "Le prix du produit est actualisé à l’enregistrement."),
        ],
        "",
    ),
    (
        "RÉCEPTIONS",
        "La saisie manuelle",
        "saisie",
        [
            ("Un bon sans PDF", "Saisi ligne par ligne, avec un PDF joint si vous en avez un."),
            ("Chaque ligne", "Référence, produit rattaché, nom, quantité, unité, prix HT et total."),
            ("Bon de livraison ou facture", "Le type se choisit en haut du formulaire."),
            ("Suppression possible", "D’une réception saisie par erreur."),
        ],
        "",
    ),
    (
        "RECETTES",
        "Les recettes",
        "recettes",
        [
            ("Catégorie et convives", "De l’entrée au dessert, avec les effectifs de référence."),
            ("Ingrédient principal", "À cocher, avec son intitulé de grammage GEMRCN."),
            ("Quantités calculées", "À servir et à commander, coût estimé selon les effectifs."),
            ("Reliée aux repas", "Alimente le menu et la liste de courses."),
        ],
        "",
    ),
    (
        "REPAS",
        "Le suivi des repas",
        "repas",
        [
            ("Date, statut, convives", "Prévu, en cours ou passé ; maternelles, élémentaires, adultes."),
            ("Coût matières", "Total et € par convive, avec le % de bio et de local."),
            ("Repas modifié", "Surligné en orange (case « Modification du repas »)."),
            ("Liste de courses PDF", "Exportable une fois les coûts estimés, pour passer commande."),
        ],
        "",
    ),
    (
        "REPAS",
        "Du menu à la commande",
        "repas_fiche",
        [
            ("1 · Menu", "Chaque poste (entrée, plat, accompagnement, laitage, dessert) est relié à une recette."),
            (
                "2 · Estimation des coûts",
                "Quantités calculées depuis les grammages ; la liste de courses se déduit de l’estimation.",
            ),
            ("3 · Bilan", "Quantités réellement sorties, coût réel, case « Finalisé » et observations."),
            ("Import du menu", "Le bouton « Importer PDF menu » crée tous les repas d’un coup."),
        ],
        "",
    ),
    (
        "GRAMMAGES",
        "Grammages GEMRCN",
        "grammages",
        [
            ("Adaptés à notre cantine", "Affichés à côté des recommandations GEMRCN (tolérance ± 10 %)."),
            ("Calcul pour chaque recette", "Ils servent à calculer les quantités à servir et à commander."),
            ("Convives et coefficient cru/cuit", "Maternelles, élémentaires, adultes."),
            ("Quatre onglets", "Entrées, plats + accompagnements, fromages, desserts + laitages."),
        ],
        "",
    ),
    (
        "STOCKS",
        "Les stocks",
        "stocks",
        [
            ("Entrées", "Les réceptions."),
            ("Sorties", "Les repas."),
            ("Solde par produit", "Mis à jour automatiquement, avec la valeur du stock."),
            ("Inventaire", "Le bouton « Inventaire » corrige le stock avec un motif facultatif."),
        ],
        "Aucune saisie : le stock se calcule tout seul à partir des réceptions et des repas.",
    ),
    (
        "STOCKS",
        "Corriger le stock par inventaire",
        "inventaire",
        [
            ("Stock calculé", "Affiché pour rappel, avant la correction."),
            ("Quantité réelle", "Vous saisissez ce qui est réellement présent."),
            ("Écart enregistré", "Comme un ajustement, avec un motif facultatif (ex. inventaire du 18/10)."),
        ],
        "Le bouton « Inventaire » de chaque ligne ouvre cette fenêtre.",
    ),
    (
        "STATISTIQUES",
        "Les chiffres clés de la période",
        "stats_haut",
        [
            ("Période du / au", "S’applique à toute la page : synthèse, bilan et graphiques."),
            ("Achats HT et prix par repas", "Repas et convives sur la période."),
            ("Part du bio et des labels", "% bio, % EGalim, % local, % direct producteur."),
            ("Exporter en PDF", "La page complète, prête à distribuer (mairie, C.G.R.S.)."),
        ],
        "",
    ),
    (
        "STATISTIQUES",
        "Le bilan de la période vis-à-vis de nos engagements",
        "stats_bilan",
        [
            ("Calculé sur la période choisie", "Aucun cumul : seuls les achats de la période comptent."),
            (
                "Nos engagements",
                "Bio, EGalim, local, direct producteur, produits frais, origine… : cible et réalisé pour chaque indicateur.",
            ),
            ("Badges", "« Respecté » ou « Non respecté » pour chaque indicateur."),
            ("Réglage", "Le local de Manger Bio peut compter comme direct producteur (Paramètres)."),
        ],
        "",
    ),
    (
        "STATISTIQUES",
        "Origine des produits par famille",
        "stats_repartitions",
        [
            (
                "Origine par famille",
                "Pour chaque famille de produits, la part de chaque provenance ; « Non renseigné » repère les produits à compléter.",
            ),
            ("Calculé sur la période", "Seuls les achats de la période choisie sont comptés."),
            ("Autres répartitions", "Label, gamme, catégorie et fournisseur sont présentés en haut de la page."),
        ],
        "",
    ),
    (
        "STATISTIQUES",
        "Coût matières par repas",
        "stats_cout",
        [
            ("Graphique et tableau", "Le coût matières de chaque repas de la période, et le coût par convive."),
            ("Une barre par repas", "Les dates des repas de la période choisie."),
            ("Export PDF", "Le bouton « Exporter en PDF » reprend toute la page."),
        ],
        "",
    ),
    (
        "ASSISTANT IA",
        "Interroger l’assistant",
        "assistant",
        [
            (
                "Questions en langage courant",
                "« Quels légumes sont d’origine UE ? », « Quels produits nous mettent en défaut ? »",
            ),
            ("Produits en défaut", "Liste ce qui éloigne la cantine de ses objectifs, indicateur par indicateur."),
            (
                "Simulation",
                "« Si je remplace les frites surgelées UE par des pommes de terre fraîches France… » : prix, volumes et indicateurs recalculés.",
            ),
            ("Actions validées par vous", "Toute écriture proposée par l’assistant demande votre confirmation."),
        ],
        "Fournisseurs possibles : Gemini, Mistral, Groq ou Ollama (local).",
    ),
    (
        "ASSISTANT IA",
        "L’assistant peut aussi créer",
        "assistant_creation",
        [
            ("Recettes", "« Crée une recette de gratin de courgettes pour 120 convives »."),
            (
                "Repas, produits, fournisseurs",
                "Création d’un repas, d’un produit ou d’un fournisseur à partir d’une simple demande.",
            ),
            ("Réceptions et sorties", "Saisie d’une réception ou des produits sortis pour un repas."),
            (
                "Toujours validé par vous",
                "Rien n’est enregistré avant votre clic sur « Valider » ; vous pouvez refuser.",
            ),
        ],
        "Les profils en lecture seule ne peuvent que consulter.",
    ),
    (
        "PARAMÈTRES",
        "Réglages de la cantine",
        "parametres",
        [
            ("Convives par défaut", "Proposés pour les nouveaux repas, recettes et le calculateur."),
            ("Nom de la cantine", "Plusieurs noms possibles : l’import PDF ne le prendra jamais pour un fournisseur."),
            ("Direct producteur", "Case : compter les produits locaux de Manger Bio comme du direct producteur."),
            ("Utilisateurs et personnalisation", "Comptes et profils, logo et couleurs, tarif de vente d’un repas."),
        ],
        "",
    ),
    (
        "PARAMÈTRES",
        "Sauvegarde et assistant",
        "parametres_bas",
        [
            ("Tout sauvegarder", "Base de données, PDF importés et fiches techniques."),
            ("Restaurer", "Remplace les données actuelles ; une copie de sécurité reste sur le serveur."),
            ("Archive sensible", "Mots de passe chiffrés : à conserver en lieu sûr."),
            ("Journal des actions", "Consigné dans logs/cgrs.log (plus affiché dans Paramètres)."),
        ],
        "À faire régulièrement : c’est la seule protection contre la perte de données.",
    ),
    (
        "POUR FINIR",
        "Bon à savoir",
        None,
        [
            (
                "Tout est centralisé",
                "Fournisseurs, produits, réceptions, repas, stocks et statistiques au même endroit.",
            ),
            ("Consultation d’abord", "Toute fiche s’ouvre en lecture : « Modifier » pour déverrouiller."),
            ("Prix saisis une fois", "Mis à jour par les réceptions, jamais saisis deux fois."),
            ("PDF d’origine conservé", "Chaque réception garde son document source."),
        ],
        "",
    ),
]


# ---------------------------------------------------------------------------------------------------------------
# Application de démonstration
# ---------------------------------------------------------------------------------------------------------------
def port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def lancer_appli(dossier: Path):
    code = dossier / "code"
    shutil.copytree(
        RACINE,
        code,
        ignore=shutil.ignore_patterns(
            ".git",
            "__pycache__",
            "*.db",
            "uploads",
            "sauvegardes-auto",
            "logs",
            "venv",
            ".venv",
            "tests",
            "build",
            "dist",
            ".*cache",
            "docs",
        ),
    )
    (code / "uploads").mkdir(exist_ok=True)
    port = port_libre()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", str(port), "--log-level", "warning"],
        cwd=code,
        env={**os.environ, "CGRS_BACKUP_INTERVAL_HOURS": "0"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(150):
        try:
            urllib.request.urlopen(base + "/api/auth/status", timeout=1)
            return proc, base
        except Exception:
            time.sleep(0.1)
    proc.kill()
    raise SystemExit("L'application n'a pas démarré : " + proc.stdout.read().decode(errors="replace")[-1500:])


# (nom, fournisseur, catégorie, unité, prix, label, provenance, gamme)
PRODUITS = [
    ("Carottes bio", "Ferme du Verger", "Légumes", "kg", 1.8, "bio", "cc_nozay", "1"),
    ("Pommes de terre", "Ferme du Verger", "Légumes", "kg", 1.1, "", "france", "1"),
    ("Courgettes", "Ferme du Verger", "Légumes", "kg", 2.4, "", "france", "1"),
    ("Pommes", "Ferme du Verger", "Fruits", "kg", 2.0, "bio", "pays_de_la_loire", "1"),
    ("Poires", "Ferme du Verger", "Fruits", "kg", 2.6, "", "france", "1"),
    ("Bananes", "Biocoop Restauration", "Fruits", "kg", 2.2, "bio", "international", "1"),
    ("Lentilles vertes", "Biocoop Restauration", "Épicerie sèche", "kg", 3.4, "bio", "france", "6"),
    ("Riz basmati", "Biocoop Restauration", "Épicerie sèche", "kg", 3.1, "bio", "international", "6"),
    ("Yaourt nature", "Laiterie du Bocage", "Produits laitiers", "pièce", 0.45, "bio", "pays_de_la_loire", "2"),
    ("Fromage blanc", "Laiterie du Bocage", "Produits laitiers", "kg", 3.9, "", "france", "2"),
    ("Sauté de poulet", "Boucherie Martin", "Volailles", "kg", 11.5, "label_rouge", "france", "1"),
    ("Rôti de porc", "Boucherie Martin", "Porc", "kg", 9.8, "", "france", "1"),
    ("Steak haché", "Boucherie Martin", "Bœuf", "kg", 12.9, "", "ue", "1"),
    ("Filet de colin", "Poissonnerie de l’Atlantique", "Poisson", "kg", 13.4, "msc", "france", "1"),
    ("Frites surgelées", "Grossiste Froid Service", "Légumes", "kg", 2.3, "", "ue", "3"),
]
MENUS = [
    ("Salade de carottes", "Sauté de poulet", "Riz basmati", "Yaourt nature", "Pommes"),
    ("Soupe de courgettes", "Filet de colin", "Pommes de terre", "Fromage blanc", "Poires"),
    ("Salade de lentilles", "Rôti de porc", "Courgettes", "Yaourt nature", "Bananes"),
    ("Carottes râpées", "Steak haché", "Frites surgelées", "Fromage blanc", "Pommes"),
]


def preparer_donnees(base: str, p) -> None:
    ctx = p.request.new_context(base_url=base, extra_http_headers=H)

    def post(chemin, corps=None):
        r = ctx.post(chemin, data=corps)
        assert r.ok, f"POST {chemin} -> {r.status} {r.text()}"
        return r.json()

    post("/api/auth/setup", {"username": "admin", "password": MOT_DE_PASSE})
    four = {}
    infos = {
        "Ferme du Verger": (["lun", "jeu"], ["Fruits", "Légumes"], 1, "Marie Dupont", "02 40 00 00 01", "internet"),
        "Biocoop Restauration": (
            ["mar"],
            ["Épicerie sèche", "Fruits"],
            0,
            "Service clients",
            "02 40 00 00 02",
            "internet",
        ),
        "Laiterie du Bocage": (["mer"], ["Produits laitiers"], 0, "Paul Martin", "02 40 00 00 03", "telephone"),
        "Boucherie Martin": (["jeu"], ["Viandes"], 0, "Luc Martin", "02 40 00 00 04", "telephone"),
        "Poissonnerie de l’Atlantique": (["ven"], ["Poisson"], 0, "Anne Lebon", "02 40 00 00 05", "email"),
        "Grossiste Froid Service": (["mar"], ["Surgelés"], 0, "Commandes", "02 40 00 00 06", "email"),
    }
    for nom, (jours, cats, direct, contact, tel, mode) in infos.items():
        corps = {
            "name": nom,
            "direct_producteur": direct,
            "delivery_days": jours,
            "categories": cats,
            "contact": contact,
            "phone": tel,
            "order_method": mode,
            "franco": 150,
        }
        four[nom] = post("/api/suppliers", corps)["id"]
    prods = {}
    for nom, f, cat, unite, prix, label, prov, gamme in PRODUITS:
        corps = {
            "name": nom,
            "supplier_id": four[f],
            "unit": unite,
            "unit_price": prix,
            "category": cat,
            "provenance": prov,
            "gamme": gamme,
        }
        if label:
            corps["label_egalim"] = label
        prods[nom] = post("/api/products", corps)["id"]
    # réceptions : septembre et octobre 2026
    par_four: dict[str, list] = {}
    for nom, f, *_ in PRODUITS:
        par_four.setdefault(f, []).append(nom)
    num = 1
    for mois in (9, 10):
        for f, noms in par_four.items():
            lignes = []
            for i, nom in enumerate(noms):
                pu = next(x[4] for x in PRODUITS if x[0] == nom)
                unite = next(x[3] for x in PRODUITS if x[0] == nom)
                lignes.append(
                    {
                        "product_id": prods[nom],
                        "qty": 20 + 7 * i + mois,
                        "unit": unite,
                        "unit_price": round(pu * (1.06 if mois == 10 else 1), 2),
                    }
                )
            post(
                "/api/orders",
                {
                    "supplier_id": four[f],
                    "kind": "facture",
                    "ref": f"FC_{num:05d}",
                    "date": f"2026-{mois:02d}-{8 + num % 10:02d}",
                    "lines": lignes,
                },
            )
            num += 1
    # recettes et repas
    for i, (_entree, plat, acc, _lait, _dessert) in enumerate(MENUS):
        for nom, cat in ((plat, "plat"), (acc, "accompagnement")):
            if nom in prods:
                post(
                    "/api/recipes",
                    {
                        "name": nom + (" rôti" if cat == "plat" else " vapeur") if i == 0 else nom + f" ({cat})",
                        "categorie": cat,
                        "nb_maternelles": 20,
                        "nb_elementaires": 60,
                        "nb_adultes": 8,
                        "items": [
                            {
                                "product_id": prods[nom],
                                "qty_servi": 0.1,
                                "qty_commander": 8.8,
                                "unit": "kg",
                                "principal": True,
                            }
                        ],
                    },
                )
    for i, (entree, plat, acc, lait, dessert) in enumerate(MENUS * 3):
        jour = 1 + i * 2
        post(
            "/api/meals",
            {
                "date": f"2026-10-{jour:02d}",
                "nb_maternelles": 20,
                "nb_elementaires": 60,
                "nb_adultes": 8,
                "entree": entree,
                "plat": plat,
                "accompagnement": acc,
                "laitage": lait,
                "dessert": dessert,
                "statut": "passe",
                "modif_prevu": i == 3,
                "items": [{"product_id": prods[plat], "qty": 8}, {"product_id": prods[acc], "qty": 7}],
            },
        )
    ctx.dispose()


# ---------------------------------------------------------------------------------------------------------------
# Captures
# ---------------------------------------------------------------------------------------------------------------
def aller(page, nom):
    page.locator("#nav a", has_text=nom).click()
    page.locator("#nav a.on", has_text=nom).wait_for()
    page.wait_for_timeout(700)


def png(page, **kw) -> str:
    return "data:image/png;base64," + base64.b64encode(page.screenshot(**kw)).decode()


def fermer(page):
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    if page.locator(".modal").count():
        for b in (
            page.locator(".modal button", has_text="Fermer").all()
            + page.locator(".modal button", has_text="Annuler").all()
        ):
            try:
                b.click(timeout=500)
                break
            except Exception:
                pass


def ouvrir_premiere_fiche(page):
    page.locator("main tr.clickable").first.click()
    page.locator(".modal").first.wait_for()
    page.wait_for_timeout(500)


def defiler_vers(page, texte: str) -> str:
    """Capture de la page défilée pour que la rubrique contenant ce texte soit en haut de l'écran."""
    el = page.get_by_text(texte).first
    el.wait_for()
    page.evaluate("e => window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 90)", el.element_handle())
    page.wait_for_timeout(500)
    return png(page)


QUESTION = "Quels produits nous mettent en défaut pour atteindre nos objectifs ?"
REPONSE = (
    "Deux produits pèsent sur les indicateurs de la période : le steak haché (origine UE, hors objectif France) et "
    "les frites surgelées (origine UE, gamme 3, hors produits frais). Voulez-vous simuler leur remplacement ?"
)


QUESTION_2 = "Crée une recette de gratin de courgettes pour 120 convives"
ATTENTE = [
    {
        "id": "a1",
        "resume": "Créer la recette « Gratin de courgettes » (120 convives)",
        "arguments": {"name": "Gratin de courgettes", "categorie": "plat", "nb_elementaires": 120},
    }
]


def capture_assistant(page) -> tuple[str, str]:
    """Le modèle de langage n'est pas appelé : les échanges affichés sont des exemples écrits pour la présentation."""
    cas = {
        QUESTION: ("produits_en_defaut", REPONSE, []),
        QUESTION_2: ("creer_recette", "", ATTENTE),
    }

    def etat(route):
        route.fulfill(json={"configure": True, "fournisseur": "Mistral", "peut_ecrire": True})

    def chat(route):
        msgs = route.request.post_data_json["messages"]
        outil, texte, attente = cas[next(m["content"] for m in reversed(msgs) if m["role"] == "user")]
        appel = {"id": "x", "type": "function", "function": {"name": outil, "arguments": "{}"}}
        msgs = msgs + [{"role": "assistant", "content": "", "tool_calls": [appel]}]
        if texte:
            msgs.append({"role": "assistant", "content": texte})
        route.fulfill(json={"messages": msgs, "attente": attente, "ecritures": False})

    page.route("**/api/assistant/etat", etat)
    page.route("**/api/assistant/chat", chat)
    images = []
    for question in (QUESTION, QUESTION_2):
        page.locator("#assistant-btn").click()
        page.locator("#assistant-panel button", has_text="Nouvelle").click()
        page.locator("#assistant-panel textarea").fill(question)
        page.locator("#assistant-panel button.p").click()
        page.locator("#assistant-panel .as-tool").wait_for()
        page.wait_for_timeout(400)
        images.append(png(page))
        page.locator("#assistant-panel button[title=Fermer]").click()
    page.unroute("**/api/assistant/etat")
    page.unroute("**/api/assistant/chat")
    return images[0], images[1]


def prendre_captures(base: str, navigateur) -> dict[str, str]:
    ctx = navigateur.new_context(locale="fr-FR", viewport={"width": 1280, "height": 760}, device_scale_factor=2)
    page = ctx.new_page()
    page.goto(base)
    if page.locator("#nav").count() == 0 or not page.locator("#nav a").count():
        page.locator("input[type=text], input:not([type])").first.fill("admin")
        page.locator("input[type=password]").first.fill(MOT_DE_PASSE)
        page.keyboard.press("Enter")
    page.locator("#nav a").first.wait_for()
    c: dict[str, str] = {}

    aller(page, "Fournisseurs")
    c["fournisseurs"] = png(page)
    ouvrir_premiere_fiche(page)
    c["fiche_fournisseur"] = png(page)
    fermer(page)

    aller(page, "Produits")
    c["produits"] = png(page)
    ouvrir_premiere_fiche(page)
    c["fiche_produit"] = png(page)
    page.evaluate(
        "document.querySelectorAll('.modal, .modal *').forEach(e => { if (e.scrollHeight > e.clientHeight + 5) e.scrollTop = e.scrollHeight })"
    )
    page.wait_for_timeout(400)
    c["historique_prix"] = png(page)
    fermer(page)

    aller(page, "Réceptions")
    c["receptions"] = png(page)
    ouvrir_premiere_fiche(page)
    c["reception"] = png(page)
    fermer(page)
    page.get_by_role("button", name="+ Saisie manuelle").click()
    page.locator(".modal").first.wait_for()
    page.wait_for_timeout(400)
    c["saisie"] = png(page)
    fermer(page)

    aller(page, "Recettes")
    c["recettes"] = png(page)

    aller(page, "Repas")
    c["repas"] = png(page)
    ouvrir_premiere_fiche(page)
    c["repas_fiche"] = png(page)
    fermer(page)

    aller(page, "Grammages")
    c["grammages"] = png(page)

    aller(page, "Stocks")
    c["stocks"] = png(page)
    page.get_by_role("button", name="Inventaire").first.click()
    page.locator(".modal").first.wait_for()
    page.wait_for_timeout(400)
    c["inventaire"] = png(page)
    fermer(page)

    aller(page, "Statistiques")
    page.evaluate("store.set('cgrs.sf', '2026-10-01'); store.set('cgrs.st', '2026-10-31'); render()")
    page.get_by_text("Synthèse de la période").wait_for()
    page.wait_for_timeout(800)
    c["stats_haut"] = png(page)
    c["assistant"], c["assistant_creation"] = capture_assistant(page)
    c["stats_bilan"] = defiler_vers(page, "Part de bio, toutes denrées")
    c["stats_repartitions"] = defiler_vers(page, "Origine par famille de produits")
    c["stats_cout"] = defiler_vers(page, "Coût matières par repas")

    aller(page, "Paramètres")
    page.get_by_text("Assistant IA").first.wait_for()
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    c["parametres"] = png(page)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)
    c["parametres_bas"] = png(page)
    ctx.close()
    return c


# ---------------------------------------------------------------------------------------------------------------
# Assemblage du PDF
# ---------------------------------------------------------------------------------------------------------------
CSS = """
@page { size: 960px 540px; margin: 0 }
* { box-sizing: border-box; margin: 0; padding: 0 }
body { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: #1f2d27 }
.d { width: 960px; height: 540px; position: relative; overflow: hidden; page-break-after: always; background: #fff; padding: 36px 48px }
.d:last-child { page-break-after: auto }
.rub { display: flex; align-items: center; gap: 12px; font-size: 12px; font-weight: 700; letter-spacing: .04em; color: #234d3a }
.rub i { width: 34px; height: 34px; border-radius: 50%; background: #235a43; display: inline-block }
h1 { font-family: Georgia, "Times New Roman", serif; font-size: 40px; color: #1f3a2e; margin: 18px 0 18px }
.corps { display: flex; gap: 32px; align-items: flex-start }
.img { flex: 0 0 560px; height: 332px; border-radius: 8px; box-shadow: 0 4px 18px rgba(0,0,0,.22); overflow: hidden; border: 1px solid #d8dfda }
.img img { display: block; width: 100%; height: 100%; object-fit: cover; object-position: top }
.liste { flex: 1; display: flex; flex-direction: column; gap: 14px }
.liste.large { columns: 2; display: block }
.liste.large div { break-inside: avoid; margin-bottom: 18px }
.liste b { display: block; font-size: 15px; color: #1f3a2e; margin-bottom: 2px }
.liste span { font-size: 13px; color: #4a5a52; line-height: 1.35 }
.leg { margin-top: 6px; padding-top: 10px; border-top: 1px solid #d8dfda; font-size: 12.5px; font-style: italic; color: #4a5a52 }
.pied { position: absolute; left: 48px; right: 48px; bottom: 18px; display: flex; justify-content: space-between; font-size: 10px; color: #6b7a72 }
.couv { background: #1f4d3a; color: #fff; padding: 0 }
.couv h1 { color: #fff; font-size: 46px; margin: 0 0 18px }
.couv .t { position: absolute; left: 48px; top: 150px; width: 400px }
.couv p { font-size: 17px; line-height: 1.4; color: #dbe8e0 }
.couv .a, .couv .b { position: absolute; border-radius: 8px; overflow: hidden; box-shadow: 0 6px 22px rgba(0,0,0,.4) }
.couv .a { left: 500px; top: 30px; width: 420px }
.couv .b { left: 440px; top: 250px; width: 440px }
.couv img { display: block; width: 100% }
.couv .m { position: absolute; left: 48px; bottom: 28px; font-size: 12px; color: #a9c4b5 }
"""


def empreinte() -> str:
    """Résumé de l'interface (pages, styles, ce script) : si elle change, le PDF doit être régénéré.
    tests/test_guide.py compare ce résumé à celui enregistré lors de la dernière génération."""
    h = hashlib.sha256()
    fichiers = sorted((RACINE / "static").glob("js/*.js")) + sorted((RACINE / "static").glob("css/*.css"))
    fichiers += [RACINE / "static" / "index.html", Path(__file__)]
    for f in fichiers:
        h.update(f.name.encode() + f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def date_fr(d: datetime.date) -> str:
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


def construire_html(c: dict[str, str], jour: datetime.date) -> str:
    e = html.escape
    parts = [
        '<div class="d couv">'
        f'<div class="a"><img src="{c["stats_haut"]}"></div><div class="b"><img src="{c["repas"]}"></div>'
        '<div class="t"><h1>Suivi des achats et des repas de la cantine</h1>'
        "<p>Guide de l’application : prise en main et fonctionnalités</p></div>"
        f'<div class="m">Mis à jour le {date_fr(jour)}</div></div>'
    ]
    n = 2
    for rub, titre, capture, items, legende in DIAPOSITIVES:
        liste = "".join(f"<div><b>{e(t)}</b><span>{e(x)}</span></div>" for t, x in items)
        if legende:
            liste += f'<div class="leg">{e(legende)}</div>'
        if capture:
            corps = f'<div class="corps"><div class="img"><img src="{c[capture]}"></div><div class="liste">{liste}</div></div>'
        else:
            corps = f'<div class="liste large" style="margin-top:30px">{liste}</div>'
        parts.append(
            f'<div class="d"><div class="rub"><i></i>{e(rub)}</div><h1>{e(titre)}</h1>{corps}'
            f'<div class="pied"><span>CGRS · Guide de l’application · mis à jour le {date_fr(jour)}</span><span>{n}</span></div></div>'
        )
        n += 1
    return f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>{''.join(parts)}</body>"


def main() -> None:
    from playwright.sync_api import sync_playwright

    dossier = Path(tempfile.mkdtemp(prefix="cgrs-guide-"))
    proc = None
    try:
        proc, base = lancer_appli(dossier)
        with sync_playwright() as p:
            preparer_donnees(base, p)
            nav = p.chromium.launch()
            captures = prendre_captures(base, nav)
            page = nav.new_page()
            page.set_content(construire_html(captures, datetime.date.today()))
            page.pdf(path=str(SORTIE), width="960px", height="540px", print_background=True)
            nav.close()
        EMPREINTE.write_text(empreinte() + "\n", encoding="utf-8")
        print(f"{SORTIE.relative_to(RACINE)} généré ({len(DIAPOSITIVES) + 1} diapositives).")
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=10)
        shutil.rmtree(dossier, ignore_errors=True)


if __name__ == "__main__":
    main()
