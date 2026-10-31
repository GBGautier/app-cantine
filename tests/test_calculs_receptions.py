"""Réceptions : références, totaux, doublons, prix, rapprochement bon de livraison / facture. Sans base ni serveur."""

from types import SimpleNamespace as NS

import pytest

from cgrs.services.orders import (
    find_duplicate_in,
    invoice_price_day,
    order_total,
    price_differs,
    price_in_product_unit,
    rank_candidates,
    ref_key,
)


@pytest.mark.parametrize(
    "ref, attendu",
    [
        ("BL-2026/0042", "20260042"),
        ("bl 42", "42"),
        ("FAC 0042", "0042"),
        ("FA0042", "0042"),
        ("FC-9", "9"),
        ("BC123", "123"),
        ("0042", "0042"),
        ("", ""),
        (None, ""),
    ],
)
def test_cle_de_reference(ref, attendu):
    assert ref_key(ref) == attendu


def reception(total_ht=None, *lignes):
    return NS(total_ht=total_ht, lines=[NS(**{"total_ht": None, "qty": None, "unit_price": None, **l}) for l in lignes])


def test_total_saisi_prime_meme_s_il_est_nul():
    assert order_total(reception(0, {"qty": 2, "unit_price": 5})) == 0


def test_total_calcule_depuis_les_lignes():
    r = reception(None, {"total_ht": 10.5}, {"qty": 3, "unit_price": 1.1}, {"qty": 4}, {})
    assert order_total(r) == 13.8  # 10,5 + 3,3 ; sans prix ou sans rien : 0
    assert order_total(reception(None)) == 0


@pytest.mark.parametrize(
    "prix, unite_ligne, unite_produit, attendu",
    [
        (6.0, "kg", "kg", 6.0),
        (3.0, "kg", "g", 0.003),  # 3 €/kg = 0,003 €/g
        (0.002, "g", "kg", 2.0),  # 0,002 €/g = 2 €/kg
        (5.0, None, "kg", 5.0),  # unité de la ligne absente : prix repris tel quel
        (5.0, "kg", "", 5.0),
        (5.0, "kg", "l", None),  # unités incompatibles
        (5.0, "pièce", "kg", None),
    ],
)
def test_prix_dans_l_unite_du_produit(prix, unite_ligne, unite_produit, attendu):
    assert price_in_product_unit(prix, unite_ligne, unite_produit) == attendu


def test_difference_de_prix_tolere_les_arrondis():
    assert not price_differs(1.0, 1.0 + 1e-12)
    assert price_differs(1.0, 1.01)


COMMANDES = [
    {"id": 1, "ref": "BL-0042", "kind": "livraison", "supplier_id": 5},
    {"id": 2, "ref": "FAC-0042", "kind": "facture", "supplier_id": 5},
    {"id": 3, "ref": "0099", "kind": "livraison", "supplier_id": None},
]


def test_doublon_meme_reference_meme_type():
    assert find_duplicate_in(COMMANDES, "bl 0042", "livraison", 5)["id"] == 1  # casse et ponctuation ignorées
    assert find_duplicate_in(COMMANDES, "FAC-0042", "facture", 5)["id"] == 2
    assert find_duplicate_in(COMMANDES, "BL-0042", "facture", 5) is None  # même référence mais autre type
    assert find_duplicate_in(COMMANDES, "0042", "livraison", 5) is None  # le préfixe BL fait partie de la référence
    assert (
        find_duplicate_in(COMMANDES, "BL-0042", "livraison", 5, exclude_id=1) is None
    )  # pas de comparaison à soi-même


def test_doublon_fournisseur_different_ou_inconnu():
    assert find_duplicate_in(COMMANDES, "BL-0042", "livraison", 6) is None  # autre fournisseur : pas un doublon
    assert find_duplicate_in(COMMANDES, "0099", "livraison", 6)["id"] == 3  # fournisseur inconnu : on signale
    assert find_duplicate_in(COMMANDES, "BL-0042", "livraison", None)["id"] == 1  # fournisseur non choisi : on signale


def test_pas_de_doublon_sans_reference():
    assert find_duplicate_in(COMMANDES, "", "livraison", 5) is None
    assert find_duplicate_in(COMMANDES, None, "livraison", 5) is None
    assert find_duplicate_in(COMMANDES, "---", "livraison", 5) is None


def bon(id, ref, total):
    return {"id": id, "ref": ref, "total_ht": total}


def test_rapprochement_ref_citee_ou_meme_montant_en_premier():
    cands = [bon(1, "BL-7", 50.0), bon(2, "BL-8", 120.0), bon(3, "BL-9", 120.004), bon(4, None, None)]
    r = rank_candidates(cands, ["BL 9", "FAC 777"], 120.0)
    assert [c["id"] for c in r] == [2, 3, 1, 4]  # 2 : même montant ; 3 : cité ET même montant ; 1 et 4 : aucun lien
    par_id = {c["id"]: c for c in r}
    assert par_id[3]["reason"] == "cité sur la facture, même montant"
    assert par_id[2]["reason"] == "même montant" and par_id[2]["match"] is True
    assert par_id[1]["match"] is False and par_id[1]["reason"] == ""


def test_rapprochement_limite_a_25_resultats():
    assert len(rank_candidates([bon(i, f"BL-{i}", 1.0) for i in range(40)], [], None)) == 25


@pytest.mark.parametrize(
    "type_, livraison_actuelle, remplaces, attendu",
    [
        ("facture", None, ["2026-03-10", "2026-03-05"], "2026-03-05"),
        ("facture", "2026-02-01", ["2026-03-05"], "2026-02-01"),
        ("facture", None, [], None),
        ("facture", None, None, None),
        ("livraison", "2026-02-01", ["2026-03-05"], None),  # un bon de livraison garde sa propre date
    ],
)
def test_date_des_releves_de_prix(type_, livraison_actuelle, remplaces, attendu):
    assert invoice_price_day(type_, livraison_actuelle, remplaces) == attendu
