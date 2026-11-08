"""Bilan des approvisionnements d'une période (page Statistiques) : indicateurs du CRT comparés aux engagements du candidat.

Les engagements sont ceux du CRT du marché de restauration de Saffré (offre de base et variante 1, sauf mention contraire) ;
ils sont fixés ici et non paramétrables. Chaque indicateur est calculé sur la période demandée, sans cumul.
"""

from datetime import date

from cgrs import db
from cgrs.constants import GAMMES, PROVENANCES
from cgrs.routes.meals import meals_metrics
from cgrs.services.bilan import (
    EPICERIE,
    FAMILLES_FRAIS,
    FAMILLES_LABELS,
    FAMILLES_ORIGINE,
    FAMILLES_DIRECT,
    FAMILLES_ZONES,
    FRANCE,
    MOIS,
    PECHE,
    _part,
    _total,
    fr,
    mois_suivant,
)
from cgrs.services.stats import load_lines, metric_pred, price_per_meal as compute_price_per_meal

TOUTES = "Toutes denrées"
# Part de produits AB par grandes familles (CRT, § « Les labels de qualité »)
ENG_BIO = {
    "Légumes et fruits": 95,
    "Pommes, poires et kiwis frais": 100,
    "Viandes et volailles": 90,
    "Produits laitiers": 80,
    "Ovoproduits": 75,
    "Épicerie": 60,
    "Pain": 100,
    TOUTES: 85,
}
BIO_HORS_MER = 100  # variante 2 « libre » et objectif du PAR : 100 % de bio hors produits de la mer
# Part de produits EGalim par grandes familles
ENG_EGALIM = {
    "Légumes et fruits": 95,
    "Pommes, poires et kiwis frais": 100,
    "Viandes et volailles": 100,
    "Produits laitiers": 90,
    "Ovoproduits": 100,
    "Épicerie": 70,
    "Pain": 100,
    TOUTES: 90,
}
LOCAL = 80  # produits locaux : objectif du projet alimentaire de référence
# Approvisionnement direct de producteurs, en % de la valeur des achats : engagements au 1/09/2025 puis au 1/09/2026
ENG_DIRECT = {
    2025: {
        "Légumes": 70,
        "Fruits": 35,
        "Viandes et volailles": 96,
        "Produits laitiers": 57,
        "Ovoproduits": 67,
        "Épicerie": 12,
        "Pain": 100,
        TOUTES: 55,
    },
    2026: {
        "Légumes": 80,
        "Fruits": 50,
        "Viandes et volailles": 96,
        "Produits laitiers": 80,
        "Ovoproduits": 80,
        "Épicerie": 30,
        "Pain": 100,
        TOUTES: 75,
    },
}
# Part de produits frais (1re gamme) par catégorie
ENG_FRAIS = {
    "Bœuf": 100,
    "Porc": 100,
    "Volailles": 100,
    "Poisson": 95,
    "Légumes": 70,
    "Fruits": 80,
    "Œufs": 67,
    "Produits laitiers": 100,
    TOUTES: 82,
}
ENG_GAMME1 = {"hors": 90, "avec": 82}
ENG_MSC = 100  # 100 % des achats de poissons frais sous label MSC


def _ligne(nom, lignes, pred, cats=None, cible=None):
    v = _part(lignes, pred, cats)
    return {
        "nom": nom,
        "total_ht": _total(lignes, cats),
        "engagement": cible,
        "valeur": v,
        "respecte": None if cible is None or v is None else v >= cible,
    }


def _par_famille(familles, lignes, pred, cibles):
    return [_ligne(nom, lignes, pred, cats, cibles.get(nom)) for nom, cats in [*familles, (TOUTES, None)]]


def _zones(lignes):
    rows = []
    for nom, cats in FAMILLES_ZONES:
        zones = [_part(lignes, lambda r, k=k: r["provenance"] == k, cats) for k in PROVENANCES]
        zones.append(_part(lignes, lambda r: r["provenance"] not in PROVENANCES, cats))
        rows.append({"nom": nom, "total_ht": _total(lignes, cats), "valeurs": zones})
    return {"colonnes": ["Famille", "Total HT", *PROVENANCES.values(), "Non renseignée"], "lignes": rows}


def _sections(lignes, reference):
    pred = metric_pred
    annee = 2026 if reference >= f"{2026}-09-01" else 2025
    hors_ep = [r for r in lignes if r["category"] not in EPICERIE]
    sections = [
        {
            "titre": "Labels",
            "note": "Parts calculées sur le montant HT des achats.",
            "lignes": [
                _ligne("Part de bio, toutes denrées", lignes, pred("bio"), cible=ENG_BIO[TOUTES]),
                _ligne("Part bio + autres labels", lignes, pred("egalim"), cible=ENG_EGALIM[TOUTES]),
                _ligne(
                    "Part de bio hors produits de la mer",
                    [r for r in lignes if r["category"] != PECHE],
                    pred("bio"),
                    cible=BIO_HORS_MER,
                ),
            ],
        },
        {
            "titre": "Produits bio par famille",
            "total": True,
            "lignes": _par_famille(FAMILLES_LABELS, lignes, pred("bio"), ENG_BIO),
        },
        {
            "titre": "Produits EGalim par famille",
            "note": "Bio et autres labels de qualité.",
            "total": True,
            "lignes": _par_famille(FAMILLES_LABELS, lignes, pred("egalim"), ENG_EGALIM),
        },
        {
            "titre": "Origine des approvisionnements",
            "lignes": [
                _ligne("Origine France (local compris)", lignes, lambda r: r["provenance"] in FRANCE),
                _ligne("Produits locaux", lignes, pred("local"), cible=LOCAL),
                *(_ligne("· " + nom, lignes, lambda r, k=k: r["provenance"] == k) for k, nom in PROVENANCES.items()),
            ],
        },
        {
            "titre": "Origine par famille de produits",
            "note": "Part de la valeur achetée dans chaque zone.",
            "matrice": _zones(lignes),
        },
        {
            "titre": "Qualité par catégorie",
            "note": "Origine France, sauf le poisson (label MSC).",
            "lignes": [
                *(_ligne(nom, lignes, lambda r: r["provenance"] in FRANCE, cats) for nom, cats in FAMILLES_ORIGINE),
                _ligne(
                    "Poisson sous label MSC",
                    lignes,
                    lambda r: "msc" in (r.get("label_detail") or "").lower(),
                    [PECHE],
                    ENG_MSC,
                ),
            ],
        },
        {
            "titre": "Approvisionnement direct de producteurs",
            "note": f"Engagements au 1er septembre {annee}.",
            "total": True,
            "lignes": _par_famille(FAMILLES_DIRECT, lignes, pred("direct"), ENG_DIRECT[annee]),
        },
        {
            "titre": "Produits frais par catégorie",
            "note": "Part de produits de 1re gamme (frais et bruts).",
            "total": True,
            "lignes": _par_famille(FAMILLES_FRAIS, lignes, pred("gamme:1"), ENG_FRAIS),
        },
        {
            "titre": "Répartition par gamme",
            "note": "Part de chaque gamme, hors épicerie puis toutes denrées. Engagement sur la 1re gamme.",
            "lignes": [
                *(
                    _ligne(
                        f"{nom} (hors épicerie)",
                        hors_ep,
                        lambda r, k=k: r["gamme"] == k,
                        cible=ENG_GAMME1["hors"] if k == "1" else None,
                    )
                    for k, nom in GAMMES.items()
                ),
                *(
                    _ligne(
                        f"{nom} (avec épicerie)",
                        lignes,
                        lambda r, k=k: r["gamme"] == k,
                        cible=ENG_GAMME1["avec"] if k == "1" else None,
                    )
                    for k, nom in GAMMES.items()
                ),
            ],
        },
    ]
    return sections


def _synthese(sections):
    """Quelques phrases : ce qui est tenu, ce qui ne l'est pas, et les familles qui s'écartent le plus."""
    par = {s["titre"]: s for s in sections}
    pts = []

    def pct(v):
        return "—" if v is None else fr(v, 2) + " %"

    bio, eg = par["Labels"]["lignes"][0], par["Labels"]["lignes"][1]
    ok = [x["respecte"] for x in (bio, eg) if x["respecte"] is not None]
    pts.append(
        f"Labels : {pct(bio['valeur'])} de produits bio (engagement {bio['engagement']} %) et {pct(eg['valeur'])} de bio + autres labels "
        f"(engagement {eg['engagement']} %). "
        + ("Engagements respectés." if ok and all(ok) else "Engagement non atteint." if ok else "")
    )
    ori = par["Origine des approvisionnements"]["lignes"]
    pts.append(
        f"Origine : {pct(ori[0]['valeur'])} d'origine France, {pct(ori[1]['valeur'])} de produits locaux (engagement {LOCAL} %). "
        + (
            "Objectif local respecté."
            if ori[1]["respecte"]
            else "Objectif local non atteint."
            if ori[1]["respecte"] is False
            else ""
        )
    )
    for titre, nom in (
        ("Approvisionnement direct de producteurs", "Approvisionnement direct"),
        ("Produits frais par catégorie", "Produits frais"),
    ):
        t = par[titre]["lignes"][-1]
        pts.append(
            f"{nom} : {pct(t['valeur'])} (engagement {t['engagement']} %). "
            + ("Objectif respecté." if t["respecte"] else "Objectif non atteint." if t["respecte"] is False else "")
        )
    ecarts = []
    for titre in (
        "Produits bio par famille",
        "Produits EGalim par famille",
        "Approvisionnement direct de producteurs",
        "Produits frais par catégorie",
    ):
        for r in par[titre]["lignes"][:-1]:
            if r["respecte"] is False and r["total_ht"]:
                ecarts.append(
                    (
                        r["valeur"] - r["engagement"],
                        f"{r['nom']} ({titre.lower()} : {fr(r['valeur'], 1)} % pour {r['engagement']} %)",
                    )
                )
    if ecarts:
        pts.append("Points d'attention : " + ", ".join(t for _, t in sorted(ecarts)[:5]) + ".")
    return [p.strip() for p in pts]


def _evolution(d1, d2):
    """Mois compris dans la période : achats, repas et indicateurs clés."""
    debut = d1 or (db.one("SELECT MIN(date) AS d FROM orders") or {}).get("d")
    fin = d2 or date.today().isoformat()
    if not debut or debut > fin:
        return []
    a, m = int(debut[:4]), int(debut[5:7])
    fa, fm = int(fin[:4]), int(fin[5:7])
    out = []
    while (a, m) <= (fa, fm) and len(out) < 36:
        mois = f"{a:04d}-{m:02d}"
        borne_d = max(debut, f"{mois}-01")
        borne_f = min(fin, f"{mois}-31")
        lignes = load_lines(borne_d, borne_f)
        valorises, _cout, _convives, prix = compute_price_per_meal(meals_metrics(borne_d, borne_f))
        out.append(
            {
                "libelle": f"{MOIS[m - 1]} {a}",
                "achats_ht": round(sum(r["spend"] for r in lignes), 2),
                "repas": len(valorises),
                "prix_par_repas": prix,
                "bio": _part(lignes, metric_pred("bio")),
                "egalim": _part(lignes, metric_pred("egalim")),
                "local": _part(lignes, metric_pred("local")),
                "direct": _part(lignes, metric_pred("direct")),
                "frais": _part(lignes, metric_pred("gamme:1")),
            }
        )
        a, m = mois_suivant(a, m)
    return out


def bilan_periode(date_from=None, date_to=None, masquer_prix=False):
    lignes = load_lines(date_from, date_to)
    sections = _sections(lignes, date_to or date.today().isoformat())
    res = {
        "periode": [date_from, date_to],
        "synthese": _synthese(sections),
        "sections": sections,
        "evolution": _evolution(date_from, date_to),
        "prix_masques": bool(masquer_prix),
    }
    if masquer_prix:  # profil « statistiques » : aucun montant ni prix
        for s in sections:
            for r in s.get("lignes", []) + s.get("matrice", {}).get("lignes", []):
                r["total_ht"] = None
        for e in res["evolution"]:
            e["achats_ht"] = e["prix_par_repas"] = None
    return res
