"""Coût des repas, liste de courses, stocks, coût d'une recette : règles de calcul sans base ni serveur."""

import pytest

from cgrs.services.meals import meal_metrics, shopping_list
from cgrs.services.recipes import recipe_cost
from cgrs.services.stock import stock_rows


def repas(id=1, guests=10, **kw):
    base = {
        "id": id,
        "date": "2026-05-10",
        "nb_maternelles": 0,
        "nb_elementaires": None,
        "nb_adultes": 0,
        "guests": guests,
        "notes": None,
        "entree": None,
        "plat": "Dahl",
        "accompagnement": None,
        "laitage": None,
        "dessert": None,
        "commentaire_post": None,
        "statut": None,
        "modif_prevu": 0,
    }
    return {**base, **kw}


def sortie(meal_id=1, product_id=1, qty=1.0, unit="kg", **kw):
    base = {
        "meal_id": meal_id,
        "product_id": product_id,
        "qty": qty,
        "unit": unit,
        "prix_reel": None,
        "mdate": "2026-05-10",
        "punit": "kg",
        "unit_price": 2.0,
        "label_egalim": "sans",
        "provenance": None,
    }
    return {**base, **kw}


# ---------- coût des repas ----------


def test_cout_d_un_repas_et_cout_par_convive():
    [m] = meal_metrics(
        [repas()], [sortie(qty=3, unit="kg"), sortie(product_id=2, qty=500, unit="g", unit_price=4.0)], {}
    )
    assert m["cost"] == 8.0  # 3 kg x 2 € + 0,5 kg x 4 €
    assert m["per_guest"] == 0.8
    assert (m["nb_items"], m["unpriced"]) == (2, 0)
    assert m["statut"] == "prevu" and m["nb_elementaires"] == 0  # valeurs par défaut


def test_prix_reel_prime_sur_l_historique_et_le_prix_courant():
    hist = {1: [("2026-01-01", 5.0)]}
    [m] = meal_metrics([repas()], [sortie(qty=2, prix_reel=1.5)], hist)
    assert m["cost"] == 3.0
    [m] = meal_metrics([repas()], [sortie(qty=2)], hist)
    assert m["cost"] == 10.0  # historique (5 €) plutôt que le prix courant (2 €)


def test_ligne_sans_prix_ou_en_unite_incompatible_n_est_pas_comptee():
    items = [sortie(qty=1), sortie(product_id=2, qty=1, unit_price=None), sortie(product_id=3, qty=2, unit="l")]
    [m] = meal_metrics([repas()], items, {})
    assert m["cost"] == 2.0
    assert (m["nb_items"], m["unpriced"]) == (3, 2)


def test_parts_bio_et_locale_en_pourcentage_du_cout():
    items = [
        sortie(qty=1, label_egalim="bio"),  # 2 €
        sortie(product_id=2, qty=1, unit_price=6.0, provenance="pays_loire"),  # 6 €
    ]
    [m] = meal_metrics([repas()], items, {})
    assert (m["pct_bio"], m["pct_local"]) == (25.0, 75.0)


def test_repas_sans_ligne_ni_convives():
    [m] = meal_metrics([repas(guests=0)], [], {})
    assert (m["cost"], m["per_guest"], m["pct_bio"], m["pct_local"]) == (0.0, None, None, None)


def test_les_lignes_vont_au_bon_repas():
    r = meal_metrics([repas(1), repas(2)], [sortie(meal_id=2, qty=5)], {})
    assert [x["cost"] for x in r] == [0.0, 10.0]


# ---------- liste de courses ----------


def ligne_courses(product_id, name, qty, unit, category="Légumes", punit="kg"):
    return {"product_id": product_id, "name": name, "qty": qty, "unit": unit, "category": category, "punit": punit}


def test_liste_de_courses_additionne_et_convertit_dans_l_unite_du_produit():
    r = shopping_list([ligne_courses(1, "Carottes", 500, "g"), ligne_courses(1, "Carottes", 1.25, "kg")])
    assert r == [{"product_id": 1, "label": "Carottes", "category": "Légumes", "unit": "kg", "qty": 1.75}]


def test_liste_de_courses_unite_incompatible_gardee_a_part():
    r = shopping_list([ligne_courses(1, "Huile", 1, "kg", punit="l"), ligne_courses(1, "Huile", 2, "l", punit="l")])
    assert sorted((x["unit"], x["qty"]) for x in r) == [("kg", 1), ("l", 2)]


def test_liste_de_courses_triee_par_categorie_puis_nom():
    r = shopping_list(
        [
            ligne_courses(1, "zèbre", 1, "kg", category="Inconnue"),
            ligne_courses(2, "Beurre", 1, "kg", category=None),
            ligne_courses(3, "ail", 1, "kg", category="Légumes"),
            ligne_courses(4, "Zeste", 1, "kg", category="Légumes"),
        ]
    )
    # catégories connues dans l'ordre de CATEGORIES, puis les autres par ordre alphabétique ; nom sans tenir compte de la casse
    assert [(x["category"], x["label"]) for x in r] == [
        ("Légumes", "ail"),
        ("Légumes", "Zeste"),
        ("Autre", "Beurre"),
        ("Inconnue", "zèbre"),
    ]


# ---------- stock ----------


PRODUITS = {
    1: {
        "unit": "kg",
        "unit_price": 2.0,
        "ref": "R1",
        "name": "Riz",
        "category": "Épicerie",
        "supplier_id": 5,
        "supplier_name": "F",
    },
    2: {
        "unit": "l",
        "unit_price": None,
        "ref": None,
        "name": "Huile",
        "category": None,
        "supplier_id": None,
        "supplier_name": None,
    },
}


def mvt(product_id, qty, unit):
    return {"product_id": product_id, "qty": qty, "unit": unit}


def test_stock_recu_moins_sorti_plus_ajustements_avec_valeur():
    [r] = stock_rows(PRODUITS, [mvt(1, 10, "kg"), mvt(1, 500, "g")], [mvt(1, 4, "kg")], [mvt(1, -0.5, "kg")])
    assert (r["received"], r["used"], r["adjusted"], r["stock"], r["value"]) == (10.5, 4, -0.5, 6.0, 12.0)


def test_stock_unite_incompatible_suivie_a_part_sans_valeur():
    rows = stock_rows(PRODUITS, [mvt(1, 10, "kg"), mvt(1, 3, "l")], [], [])
    assert sorted((r["unit"], r["stock"], r["value"]) for r in rows) == [("kg", 10, 20.0), ("l", 3, None)]


def test_stock_ignore_produit_inconnu_et_quantite_absente_et_trie_par_nom():
    rows = stock_rows(PRODUITS, [mvt(99, 1, "kg"), mvt(1, None, "kg"), mvt(2, 1, None), mvt(1, 1, None)], [], [])
    assert [r["name"] for r in rows] == ["Huile", "Riz"]
    assert rows[0]["value"] is None  # pas de prix connu


# ---------- coût d'une recette ----------


def ingredient(product_id=1, mat=0, elem=0, adu=0, unit_price=10.0):
    return {
        "product_id": product_id,
        "qty_maternelle": mat,
        "qty_elementaire": elem,
        "qty_adulte": adu,
        "unit_price": unit_price,
    }


def test_cout_recette_grammages_en_grammes_par_convive():
    r = recipe_cost([ingredient(mat=50, elem=80, adu=100)], 20, 40, 5, {}, "2026-05-10")
    assert r == {"cost": 47.0, "unpriced": 0}  # (1 kg + 3,2 kg + 0,5 kg) x 10 €


def test_cout_recette_ingredient_sans_prix_compte_a_part():
    r = recipe_cost(
        [ingredient(elem=100), ingredient(product_id=2, elem=100, unit_price=None)], 0, 10, 0, {}, "2026-05-10"
    )
    assert r == {"cost": 10.0, "unpriced": 1}


def test_cout_recette_utilise_le_prix_a_la_date():
    hist = {1: [("2026-01-01", 1.0), ("2026-06-01", 3.0)]}
    assert recipe_cost([ingredient(elem=1000)], 0, 1, 0, hist, "2026-02-01")["cost"] == 1.0
    assert recipe_cost([ingredient(elem=1000)], 0, 1, 0, hist, "2026-07-01")["cost"] == 3.0


def test_cout_recette_sans_ingredient_ou_ligne_libre():
    assert recipe_cost([], 1, 1, 1, {}, "2026-05-10") is None
    assert recipe_cost([ingredient(product_id=None, elem=100)], 0, 10, 0, {}, "2026-05-10") == {
        "cost": 0.0,
        "unpriced": 0,
    }
    assert recipe_cost([ingredient(elem=100)], 0, 0, 0, {}, "2026-05-10") == {"cost": 0.0, "unpriced": 0}


@pytest.mark.parametrize("effectifs", [(0, 0, 0), (1, 0, 0)])
def test_cout_nul_sans_convives(effectifs):
    r = recipe_cost([ingredient(elem=100)], *effectifs, {}, "2026-05-10")
    assert r["cost"] == 0.0
