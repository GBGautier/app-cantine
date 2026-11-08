"""Bilan CRT de la période (page Statistiques) : indicateurs sur la période choisie, comparés aux engagements fixes du CRT."""

import pytest

from cgrs.services.bilan_periode import bilan_periode


@pytest.fixture(scope="module")
def jeu(client):
    """Octobre 2050 : légumes bio locaux directs (60 €, gamme 1) et bœuf UE sans label (40 €, gamme 3)."""
    f = client.post("/api/suppliers", json={"name": "Période Fournisseur"}).json()["id"]

    def produit(nom, categorie, label, provenance, gamme, direct):
        return client.post(
            "/api/products",
            json={
                "name": nom,
                "supplier_id": f,
                "unit": "kg",
                "unit_price": 1,
                "category": categorie,
                "label_egalim": label,
                "provenance": provenance,
                "gamme": gamme,
                "direct_producteur": direct,
            },
        ).json()["id"]

    legume = produit("Période légume", "Légumes", "bio", "loire_atlantique", "1", 1)
    boeuf = produit("Période boeuf", "Viande de boeuf", "sans", "ue", "3", 0)
    for jour, produit_id, qte in (("2050-10-05", legume, 60), ("2050-10-06", boeuf, 40), ("2050-11-05", legume, 100)):
        client.post(
            "/api/orders",
            json={
                "supplier_id": f,
                "kind": "facture",
                "date": jour,
                "lines": [{"product_id": produit_id, "qty": qte, "unit": "kg", "unit_price": 1}],
            },
        )


def _ligne(b, section, nom):
    s = next(s for s in b["sections"] if s["titre"] == section)
    return next(r for r in s["lignes"] if r["nom"] == nom)


def test_la_periode_choisie_decide_des_valeurs(jeu):
    octobre = bilan_periode("2050-10-01", "2050-10-31")
    assert _ligne(octobre, "Labels", "Part de bio, toutes denrées")["valeur"] == 60.0
    deux_mois = bilan_periode("2050-10-01", "2050-11-30")
    assert _ligne(deux_mois, "Labels", "Part de bio, toutes denrées")["valeur"] == 80.0  # 160 € bio sur 200 €


def test_engagements_du_crt_et_badges(jeu):
    b = bilan_periode("2050-10-01", "2050-10-31")
    bio = _ligne(b, "Labels", "Part de bio, toutes denrées")
    assert (bio["engagement"], bio["respecte"]) == (85, False)
    assert _ligne(b, "Labels", "Part bio + autres labels")["engagement"] == 90
    assert _ligne(b, "Labels", "Part de bio hors produits de la mer")["engagement"] == 100
    assert _ligne(b, "Produits bio par famille", "Pain")["engagement"] == 100
    assert _ligne(b, "Produits EGalim par famille", "Épicerie")["engagement"] == 70
    # engagements directs : 80 % pour les légumes depuis le 1er septembre 2026 (70 % avant)
    legumes = _ligne(b, "Approvisionnement direct de producteurs", "Légumes")
    assert (legumes["engagement"], legumes["valeur"], legumes["respecte"]) == (80, 100.0, True)
    assert (
        _ligne(bilan_periode("2026-01-01", "2026-02-01"), "Approvisionnement direct de producteurs", "Légumes")[
            "engagement"
        ]
        == 70
    )
    assert _ligne(b, "Produits frais par catégorie", "Légumes")["engagement"] == 70
    assert _ligne(b, "Origine des approvisionnements", "Produits locaux")["engagement"] == 80


def test_lignes_retirees_et_pas_de_cumul(jeu):
    b = bilan_periode("2050-10-01", "2050-10-31")
    labels = [r["nom"] for r in next(s for s in b["sections"] if s["titre"] == "Labels")["lignes"]]
    assert labels == ["Part de bio, toutes denrées", "Part bio + autres labels", "Part de bio hors produits de la mer"]
    origine = [
        r["nom"] for r in next(s for s in b["sections"] if s["titre"] == "Origine des approvisionnements")["lignes"]
    ]
    assert "Hors France" not in origine
    titres = [s["titre"] for s in b["sections"]]
    assert "Origine par famille de produits" in titres and not any(
        "cumul" in t.lower() or "ce mois" in t.lower() for t in titres
    )
    assert "cumul" not in str(b).lower() and "saison" not in str(b).lower()


def test_matrice_origine_et_evolution(jeu):
    b = bilan_periode("2050-10-01", "2050-11-30")
    matrice = next(s for s in b["sections"] if s.get("matrice"))["matrice"]
    assert matrice["colonnes"][-1] == "Non renseignée"
    legumes = next(r for r in matrice["lignes"] if r["nom"] == "Légumes")
    assert legumes["valeurs"][1] == 100.0  # Loire-Atlantique
    assert [e["libelle"] for e in b["evolution"]] == ["octobre 2050", "novembre 2050"]
    assert b["synthese"] and b["synthese"][0].startswith("Labels")


def test_masque_pour_le_profil_stats(jeu, client):
    b = bilan_periode("2050-10-01", "2050-10-31", masquer_prix=True)
    assert b["prix_masques"] and all(r["total_ht"] is None for s in b["sections"] for r in s.get("lignes", []))
    assert all(e["achats_ht"] is None for e in b["evolution"])
    assert client.get("/api/bilan/periode?date_from=2050-10-01&date_to=2050-10-31").status_code == 200


def test_engagements_gammes_qualite_et_origine(jeu):
    b = bilan_periode("2050-10-01", "2050-10-31")
    gamme1 = _ligne(b, "Répartition par gamme", "1 - frais et brut (hors épicerie)")
    assert (gamme1["engagement"], gamme1["sens"], gamme1["valeur"], gamme1["respecte"]) == (90, "min", 60.0, False)
    gammes = next(s for s in b["sections"] if s["titre"] == "Répartition par gamme")["lignes"]
    assert [(r["engagement"], r["sens"]) for r in gammes[:6]] == [
        (90, "min"),
        (7, "max"),
        (3, "max"),
        (0, "max"),
        (0, "max"),
        (0, "max"),
    ]
    assert [r["engagement"] for r in gammes[6:]] == [82, 6, 3, 1, 1, 7]
    assert _ligne(b, "Qualité par catégorie", "Légumes")["engagement"] == 95
    assert _ligne(b, "Qualité par catégorie", "Fruits")["engagement"] == 80
    matrice = next(s for s in b["sections"] if s.get("matrice"))["matrice"]["lignes"]
    assert next(r for r in matrice if r["nom"] == "Légumes")["engagements"] == [50, 15, 20, 10, 5, 0]
    assert next(r for r in matrice if r["nom"] == "Produits de la pêche")["engagements"] is None


def test_locaux_manger_bio_comptes_en_direct(client):
    f = client.post("/api/suppliers", json={"name": "Manger Bio Pays de la Loire"}).json()["id"]
    autre = client.post("/api/suppliers", json={"name": "Grossiste quelconque"}).json()["id"]

    def reception(fournisseur, nom, provenance):
        p = client.post(
            "/api/products",
            json={
                "name": nom,
                "supplier_id": fournisseur,
                "unit": "kg",
                "unit_price": 1,
                "category": "Légumes",
                "label_egalim": "bio",
                "provenance": provenance,
                "gamme": "1",
                "direct_producteur": 0,
            },
        ).json()["id"]
        client.post(
            "/api/orders",
            json={
                "supplier_id": fournisseur,
                "kind": "facture",
                "date": "2060-03-10",
                "lines": [{"product_id": p, "qty": 10, "unit": "kg", "unit_price": 1}],
            },
        )

    reception(f, "MB local", "loire_atlantique")
    reception(f, "MB hors région", "ue")
    reception(autre, "Autre local", "loire_atlantique")

    def direct():
        return _ligne(bilan_periode("2060-03-01", "2060-03-31"), "Approvisionnement direct de producteurs", "Légumes")[
            "valeur"
        ]

    assert client.get("/api/settings").json()["local_manger_bio_direct"] is False
    assert direct() == 0.0
    client.put("/api/settings", json={"client_names": "", "local_manger_bio_direct": True})
    assert client.get("/api/settings").json()["local_manger_bio_direct"] is True
    assert direct() == 33.33  # seul le produit local de Manger Bio passe en direct (10 € sur 30 €)
    client.put("/api/settings", json={"client_names": "", "local_manger_bio_direct": False})
    assert direct() == 0.0
