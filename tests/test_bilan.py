"""Bilan mensuel : un mois comparé au cumul depuis le 1er septembre."""

from datetime import date

import pytest

from cgrs.services import bilan as svc


@pytest.fixture(scope="module")
def jeu(client):
    """Septembre et octobre 2040 : deux produits, deux repas. Septembre 50 % bio / local / direct, octobre 40 %."""
    f = client.post("/api/suppliers", json={"name": "Bilan Fournisseur"}).json()["id"]
    p1 = client.post(
        "/api/products",
        json={
            "name": "Bilan légume bio local",
            "supplier_id": f,
            "unit": "kg",
            "unit_price": 2,
            "category": "Légumes",
            "label_egalim": "bio",
            "provenance": "loire_atlantique",
            "gamme": "1",
            "direct_producteur": 1,
        },
    ).json()["id"]
    p2 = client.post(
        "/api/products",
        json={
            "name": "Bilan boeuf UE",
            "supplier_id": f,
            "unit": "kg",
            "unit_price": 4,
            "category": "Viande de boeuf",
            "label_egalim": "sans",
            "provenance": "ue",
            "gamme": "3",
            "direct_producteur": 0,
        },
    ).json()["id"]
    for jour, produit, qte, prix in (
        ("2040-09-05", p1, 100, 2),
        ("2040-09-06", p2, 50, 4),
        ("2040-10-05", p1, 20, 2),
        ("2040-10-06", p2, 15, 4),
    ):
        r = client.post(
            "/api/orders",
            json={
                "supplier_id": f,
                "kind": "facture",
                "date": jour,
                "ref": f"BIL-{jour}",
                "lines": [{"product_id": produit, "qty": qte, "unit": "kg", "unit_price": prix}],
            },
        )
        assert r.status_code == 200, r.text
    for jour, produit in (("2040-09-12", p1), ("2040-10-10", p2)):
        r = client.post(
            "/api/meals",
            json={
                "date": jour,
                "nb_elementaires": 10,
                "statut": "passe",
                "items": [{"product_id": produit, "qty": 10, "unit": "kg"}],
            },
        )
        assert r.status_code == 200, r.text
    st = client.get("/api/settings").json()
    client.put("/api/settings", json={"client_names": st["client_names"], "tarif_repas": 2.04})
    return {"f": f, "p1": p1, "p2": p2}


def test_bornes_annee_de_cantine():
    assert svc.bornes("2040-10") == ("2040-10-01", "2040-10-31", "2040-09-01")
    assert svc.bornes("2041-01") == ("2041-01-01", "2041-01-31", "2040-09-01")  # janvier : année commencée en septembre
    assert svc.bornes("2040-09")[2] == "2040-09-01"
    assert svc.bornes("2040-02")[1] == "2040-02-29"
    for mauvais in ("2040", "2040-13", "abc", "2040-00", ""):
        with pytest.raises(svc.MoisInvalide):
            svc.bornes(mauvais)


def test_mois_compare_au_cumul(client, jeu):
    b = client.get("/api/bilan", params={"mois": "2040-10"}).json()
    assert b["libelle"] == "Octobre 2040" and b["periode_cumul"] == ["2040-09-01", "2040-10-31"]
    bio = b["labels"]["bio"]
    assert (bio["mois"], bio["cumul"]) == (40.0, 48.0)  # octobre : 40 / 100 ; cumul : 240 / 500
    assert b["labels"]["egalim"]["mois"] == 40.0 and b["labels"]["sans_label"]["mois"] == 60.0
    assert (b["origine"]["local"]["mois"], b["origine"]["france"]["mois"], b["origine"]["hors_france"]["mois"]) == (
        40.0,
        40.0,
        60.0,
    )
    assert {r["cle"]: r["mois"] for r in b["origine"]["repartition"]}["ue"] == 60.0
    toutes = b["direct"][-1]
    assert (toutes["nom"], toutes["total_ht"], toutes["mois"], toutes["cumul"]) == ("Toutes denrées", 100.0, 40.0, 48.0)
    legumes = next(r for r in b["direct"] if r["nom"] == "Légumes")
    assert (legumes["total_ht"], legumes["mois"]) == (40.0, 100.0)
    assert next(r for r in b["frais"] if r["nom"] == "Bœuf")["mois"] == 0.0
    assert next(r for r in b["frais"] if r["nom"] == "Légumes")["mois"] == 100.0
    assert next(r for r in b["categories_france"] if r["nom"] == "Légumes")["mois"] == 100.0
    assert next(r for r in b["gammes"] if r["nom"].startswith("3"))["mois"] == 60.0
    bio_t = next(t for t in b["tendance"] if t["indicateur"] == "Part de bio")
    assert (bio_t["mois"], bio_t["cumul"], bio_t["ecart_points"]) == (40.0, 48.0, -8.0)
    assert any(s.startswith("Labels : 40,00 % de produits bio") for s in b["synthese"])


def test_prix_par_repas_et_deficit(client, jeu):
    b = client.get("/api/bilan", params={"mois": "2040-10"}).json()
    assert b["tarif_repas"] == 2.04
    m, c = b["prix"]["mois"], b["prix"]["cumul"]
    assert (m["repas"], m["convives"], m["prix_par_repas"]) == (1, 10, 4.0)  # 10 kg de boeuf à 4 € pour 10 convives
    assert (m["deficit_par_repas"], m["deficit_total"]) == (1.96, 19.6)
    assert (c["repas"], c["convives"], c["prix_par_repas"]) == (2, 20, 3.0)  # (20 € + 40 €) / 20 convives
    assert (c["deficit_par_repas"], c["deficit_total"]) == (0.96, 19.2)
    assert b["prix"]["jours"] == [{"date": "2040-10-10", "prix": 4.0, "convives": 10}]
    sept = client.get("/api/bilan", params={"mois": "2040-09"}).json()
    assert (
        sept["prix"]["mois"]["prix_par_repas"] == 2.0 and sept["prix"]["mois"]["deficit_total"] == 0
    )  # sous le tarif : pas de déficit
    assert sept["prix"]["mois"]["achats_ht"] == 400.0
    assert sept["prix"]["cumul"] == sept["prix"]["mois"]  # en septembre, le cumul est le mois lui-même


def test_evolution_mois_par_mois(client, jeu):
    b = client.get("/api/bilan", params={"mois": "2040-10"}).json()
    assert [e["mois"] for e in b["evolution"]] == ["2040-09", "2040-10"]
    sept, octo = b["evolution"]
    assert (sept["libelle"], sept["achats_ht"], sept["bio"], sept["direct"], sept["prix_par_repas"]) == (
        "septembre 2040",
        400.0,
        50.0,
        50.0,
        2.0,
    )
    assert (octo["achats_ht"], octo["bio"], octo["prix_par_repas"]) == (100.0, 40.0, 4.0)
    janvier = client.get("/api/bilan", params={"mois": "2041-01"}).json()
    assert [e["mois"] for e in janvier["evolution"]][:2] == ["2040-09", "2040-10"] and len(janvier["evolution"]) == 5


def test_engagements_du_marche_dans_le_bilan(client, jeu):
    cible = next(
        c["target"] for c in client.get("/api/commitments").json() if c["metrics"] == ["bio"] and not c["categories"]
    )
    b = client.get("/api/bilan", params={"mois": "2040-10"}).json()
    assert b["labels"]["bio"]["engagement"] == cible
    e = next(e for e in b["engagements"] if e["indicateur"] == "bio")
    assert (e["mois"]["reel"], e["cumul"]["reel"], e["mois"]["statut"]) == (40.0, 48.0, "ko")


def test_mois_invalide_et_mois_par_defaut(client, jeu):
    assert client.get("/api/bilan", params={"mois": "n'importe quoi"}).status_code == 422
    d = client.get("/api/bilan")  # sans mois : le dernier mois (jusqu'à aujourd'hui) avec des achats ou des repas
    assert d.status_code == 200 and d.json()["mois"] <= date.today().isoformat()[:7]


def test_profil_stats_sans_prix(client, jeu):
    b = svc.bilan("2040-10", masquer_prix=True)
    assert b["prix_masques"] and b["prix"]["mois"] == {"repas": 1} and b["prix"]["jours"] == []
    assert all(r["total_ht"] is None for r in b["direct"] + b["frais"])
    assert all(e["achats_ht"] is None and e["prix_par_repas"] is None for e in b["evolution"])
    assert "price_per_meal" not in [e["indicateur"] for e in b["engagements"]]
    assert b["labels"]["bio"]["mois"] == 40.0  # les parts restent visibles


def test_tarif_repas_reglable(client, jeu):
    st = client.get("/api/settings").json()
    assert st["tarif_repas"] == 2.04
    assert client.put("/api/settings", json={"client_names": st["client_names"], "tarif_repas": 3.5}).status_code == 200
    b = client.get("/api/bilan", params={"mois": "2040-10"}).json()
    assert b["tarif_repas"] == 3.5 and b["prix"]["mois"]["deficit_par_repas"] == 0.5
    assert client.put("/api/settings", json={"client_names": st["client_names"], "tarif_repas": 0}).status_code == 422
    assert client.get("/api/settings").json()["tarif_repas"] == 3.5  # refus : rien n'est modifié
    client.put("/api/settings", json={"client_names": st["client_names"]})  # sans tarif : inchangé
    assert client.get("/api/settings").json()["tarif_repas"] == 3.5
    client.put("/api/settings", json={"client_names": st["client_names"], "tarif_repas": 2.04})


def test_labels_et_origine_par_famille_et_gammes(client, jeu):
    b = svc.bilan("2040-10")
    bio = {r["nom"]: r for r in b["bio_familles"]}
    assert (bio["Légumes et fruits"]["mois"], bio["Légumes et fruits"]["cumul"]) == (100.0, 100.0)
    assert bio["Viandes et volailles"]["mois"] == 0.0 and bio["Toutes denrées"]["mois"] == 40.0
    assert bio["Légumes et fruits"]["total_ht"] == 40
    assert bio["Épicerie"]["mois"] is None  # aucune dépense dans la famille : pas de pourcentage
    assert [r["nom"] for r in b["egalim_familles"]][-1] == "Toutes denrées"
    zones = {r["nom"]: {z["cle"]: z for z in r["zones"]} for r in b["zones"]}
    assert zones["Légumes"]["loire_atlantique"]["mois"] == 100.0 and zones["Légumes"]["ue"]["mois"] == 0.0
    assert zones["Viande bovine"]["ue"]["mois"] == 100.0 and zones["Viande bovine"]["ue"]["cumul"] == 100.0
    assert zones["Fruits"]["ue"]["mois"] is None  # famille sans achat
    assert zones["Légumes"]["inconnue"]["mois"] == 0.0
    g = {x["nom"].split(" - ")[0]: x for x in b["gammes"]}
    assert g["1"]["mois"] == 40.0 and g["3"]["mois"] == 60.0
    assert g["1"]["hors_epicerie"]["mois"] == 40.0  # pas d'épicerie dans le jeu : mêmes valeurs
