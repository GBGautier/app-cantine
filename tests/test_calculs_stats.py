"""Statistiques d'achats : règles de calcul, sans base ni serveur."""

import pytest

from cgrs.constants import LOCAL
from cgrs.services import stats


def ligne(spend, **kw):
    base = {
        "spend": spend,
        "label_egalim": "sans",
        "provenance": None,
        "gamme": None,
        "category": None,
        "direct_producteur": 0,
        "supplier": None,
    }
    return {**base, **kw}


def test_repartition_triee_par_montant_avec_part_en_pourcentage():
    lignes = [ligne(30, supplier="A"), ligne(10, supplier="B"), ligne(60, supplier="A"), ligne(0, supplier=None)]
    r = stats.breakdown(lignes, "supplier")
    assert [(x["key"], x["amount"], x["pct"]) for x in r] == [
        ("A", 90, 90.0),
        ("B", 10, 10.0),
        ("non renseigné", 0, 0.0),
    ]


def test_repartition_libelles_et_total_nul():
    r = stats.breakdown([ligne(5, label_egalim="bio")], "label_egalim", {"bio": "Bio"})
    assert r == [{"key": "bio", "label": "Bio", "amount": 5, "pct": 100.0}]
    assert stats.breakdown([ligne(0, label_egalim="bio")], "label_egalim")[0]["pct"] == 0
    assert stats.breakdown([], "supplier") == []


def test_indicateurs():
    bio, autre, sans = ligne(1, label_egalim="bio"), ligne(1, label_egalim="autre"), ligne(1)
    assert [stats.metric_pred("bio")(r) for r in (bio, autre, sans)] == [True, False, False]
    assert [stats.metric_pred("egalim")(r) for r in (bio, autre, sans)] == [True, True, False]
    assert stats.metric_pred("direct")(ligne(1, direct_producteur=1)) is True
    assert stats.metric_pred("label:autre")(autre) is True
    assert stats.metric_pred("gamme:4")(ligne(1, gamme="4")) is True
    assert stats.metric_pred("provenance:x")(ligne(1, provenance="x")) is True
    local = sorted(LOCAL)[0]
    assert stats.metric_pred("local")(ligne(1, provenance=local)) is True
    assert stats.metric_pred("inconnu") is None


def test_pourcentage_multi_indicateurs_est_une_union():
    lignes = [ligne(50, label_egalim="bio"), ligne(30, direct_producteur=1), ligne(20)]
    assert stats.lines_metric_multi(lignes, ["bio"]) == 50.0
    assert (
        stats.lines_metric_multi(lignes, ["bio", "direct"]) == 80.0
    )  # une ligne compte si elle vérifie l'un OU l'autre
    assert stats.lines_metric_multi(lignes, ["inconnu"]) is None
    assert stats.lines_metric_multi(lignes, []) is None


def test_pourcentage_filtre_par_categorie_et_gamme():
    lignes = [
        ligne(40, category="Fruits", label_egalim="bio", gamme="g1"),
        ligne(40, category="Fruits", gamme="g2"),
        ligne(20, category="Viandes", label_egalim="bio", gamme="g1"),
    ]
    assert stats.lines_metric_multi(lignes, ["bio"], categories=["Fruits"]) == 50.0
    assert stats.lines_metric_multi(lignes, ["bio"], categories=["Fruits"], gammes=["g1"]) == 100.0
    assert stats.lines_metric_multi(lignes, ["bio"], categories=["Poissons"]) is None  # aucune dépense dans l'assiette
    assert stats.lines_metric(lignes, "bio", "Viandes") == 100.0


def reception(order_id, total, *lignes):
    return [{"order_id": order_id, "order_total": total, "qty": q, "spend": s} for q, s in lignes]


def test_montant_manquant_reparti_au_prorata_des_quantites():
    lignes = reception(1, 100, (1, 40), (1, None), (3, None))  # 60 € restants pour 1 + 3 unités
    stats.fill_spend(lignes)
    assert [r["spend"] for r in lignes] == [40, pytest.approx(15), pytest.approx(45)]


def test_montant_manquant_sans_total_ou_sans_ecart_reste_a_zero():
    sans_total = reception(1, None, (1, 10), (1, None))
    stats.fill_spend(sans_total)
    assert [r["spend"] for r in sans_total] == [10, 0]
    ecart_nul = reception(2, 10.004, (1, 10), (1, None))  # écart de 0,4 centime : ignoré
    stats.fill_spend(ecart_nul)
    assert [r["spend"] for r in ecart_nul] == [10, 0]


def test_montant_manquant_quantites_nulles_partage_egal():
    lignes = reception(1, 10, (0, None), (None, None))
    stats.fill_spend(lignes)
    assert [r["spend"] for r in lignes] == [5, 5]


def test_montants_manquants_traites_reception_par_reception():
    lignes = reception(1, 20, (1, None)) + reception(2, 7, (2, None), (2, None))
    stats.fill_spend(lignes)
    assert [r["spend"] for r in lignes] == [20, 3.5, 3.5]


def test_part_des_depenses():
    lignes = [ligne(75, label_egalim="bio"), ligne(25)]
    assert stats.share_of_spend(lignes, lambda r: r["label_egalim"] == "bio", 100) == 75.0
    assert stats.share_of_spend(lignes, lambda r: True, 0) == 0


def test_prix_par_repas_ignore_les_repas_sans_cout_ou_sans_convives():
    repas = [
        {"cost": 100.0, "guests": 50},
        {"cost": 30.0, "guests": 10},
        {"cost": 0, "guests": 40},  # pas chiffré
        {"cost": 12.0, "guests": 0},  # pas de convives
    ]
    priced, cost, guests, prix = stats.price_per_meal(repas)
    assert (len(priced), cost, guests, prix) == (2, 130.0, 60, 2.17)
    assert stats.price_per_meal([])[3] is None


@pytest.mark.parametrize(
    "reel, mode, cible, attendu",
    [
        (None, "min", 20, "nodata"),
        (20, "min", 20, "ok"),  # objectif tenu pile
        (19.9, "min", 20, "ko"),
        (20, "max", 20, "ok"),
        (20.1, "max", 20, "ko"),
        (0, "min", 0, "ok"),  # un résultat de 0 n'est pas « pas de données »
    ],
)
def test_statut_d_un_engagement(reel, mode, cible, attendu):
    assert stats.commitment_status(reel, mode, cible) == attendu


def test_profil_stats_ne_voit_aucun_prix():
    resultat = {
        "total_ht": 1,
        "cost_total": 2,
        "price_per_meal": 3,
        "daily": [],
        "nb_lines": 4,
        "pct_bio": 50,
        "by_label": [{"key": "bio", "amount": 9, "pct": 100}],
        "by_provenance": [],
        "by_gamme": [],
        "by_category": [],
        "by_supplier": [{"key": "A", "amount": 9, "pct": 100}],
        "commitments": [{"metrics": ["bio"]}, {"metrics": ["price_per_meal"]}],
    }
    stats.hide_prices(resultat)
    assert not {"total_ht", "cost_total", "price_per_meal", "daily", "nb_lines"} & resultat.keys()
    assert resultat["by_label"] == [{"key": "bio", "pct": 100}]
    assert resultat["commitments"] == [{"metrics": ["bio"]}]
    assert resultat["prices_hidden"] is True and resultat["pct_bio"] == 50
