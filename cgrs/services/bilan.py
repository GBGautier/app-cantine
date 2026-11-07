"""Bilan mensuel des approvisionnements : un mois comparé au cumul depuis le début de l'année de cantine (1er septembre).

Reprend les rubriques du « Suivi des approvisionnements » : prix par repas et déficit, labels, origine, qualité par catégorie,
approvisionnement direct par famille, produits frais par catégorie, engagements du marché, évolution mois par mois.
Chaque indicateur est calculé deux fois : sur le mois (« mois ») et sur le cumul depuis septembre (« cumul »).
"""

import calendar
from datetime import date

from cgrs import db
from cgrs.constants import GAMMES, LOCAL, PROVENANCES
from cgrs.routes.commitments import commitment_out
from cgrs.routes.meals import meals_metrics
from cgrs.routes.settings import get_tarif_repas
from cgrs.services.stats import (
    commitment_status,
    lines_metric_multi,
    load_lines,
    metric_pred,
    price_per_meal as compute_price_per_meal,
)

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
FRANCE = ("france", *LOCAL)  # provenances d'origine France (le local en fait partie)
PECHE = "Produits de la pêche"

VIANDES = ["Viande de porc", "Viande de volaille", "Viande de boeuf"]
FRUITS = ["Fruits: pommes, poires, kiwis", "Fruits: autres"]
EPICERIE = ["Épicerie: légumineuses", "Épicerie: céréales", "Épicerie: autre"]

# (nom affiché, catégories) : mêmes familles que le modèle de suivi
FAMILLES_ORIGINE = [
    ("Viande (bœuf, porc, volaille)", VIANDES),
    ("Fruits", FRUITS),
    ("Légumes", ["Légumes"]),
    ("Produits laitiers", ["Produits laitiers"]),
    ("Ovoproduits", ["Ovoproduits"]),
]
FAMILLES_DIRECT = [
    ("Légumes", ["Légumes"]),
    ("Fruits", FRUITS),
    ("Viandes et volailles", VIANDES),
    ("Produits laitiers", ["Produits laitiers"]),
    ("Ovoproduits", ["Ovoproduits"]),
    ("Épicerie", EPICERIE),
    ("Pain", ["Pain"]),
]
FAMILLES_FRAIS = [
    ("Bœuf", ["Viande de boeuf"]),
    ("Porc", ["Viande de porc"]),
    ("Volailles", ["Viande de volaille"]),
    ("Poisson", [PECHE]),
    ("Légumes", ["Légumes"]),
    ("Fruits", FRUITS),
    ("Œufs", ["Ovoproduits"]),
    ("Produits laitiers", ["Produits laitiers"]),
]


class MoisInvalide(ValueError):
    pass


def fr(v, d=1):
    """Nombre à la française : 90,1."""
    return f"{v:.{d}f}".replace(".", ",")


def bornes(mois):
    """('AAAA-MM') -> (début du mois, fin du mois, début de l'année de cantine = 1er septembre)."""
    try:
        a, m = (int(x) for x in mois.split("-"))
        assert 1 <= m <= 12 and 2000 <= a <= 2200
    except (ValueError, AssertionError, AttributeError):
        raise MoisInvalide("Mois attendu au format AAAA-MM (ex. 2026-09).") from None
    debut = f"{a:04d}-{m:02d}-01"
    fin = f"{a:04d}-{m:02d}-{calendar.monthrange(a, m)[1]:02d}"
    rentree = f"{a if m >= 9 else a - 1:04d}-09-01"
    return debut, fin, rentree


def mois_suivant(a, m):
    return (a + 1, 1) if m == 12 else (a, m + 1)


def mois_par_defaut():
    """Dernier mois comportant des achats ou des repas, sinon le mois en cours."""
    r = db.one(
        "SELECT MAX(d) AS d FROM (SELECT MAX(date) AS d FROM orders UNION ALL SELECT MAX(date) AS d FROM meals) "
        "WHERE d IS NOT NULL AND d<=?",
        (date.today().isoformat(),),
    )
    return (r["d"] if r and r["d"] else date.today().isoformat())[:7]


def _part(lignes, pred, categories=None):
    sous = [r for r in lignes if not categories or r["category"] in categories]
    total = sum(r["spend"] for r in sous)
    return round(100 * sum(r["spend"] for r in sous if pred(r)) / total, 2) if total else None


def _total(lignes, categories=None):
    return round(sum(r["spend"] for r in lignes if not categories or r["category"] in categories), 2)


def _engagements_marche():
    return [
        c for c in (commitment_out(r) for r in db.rows("SELECT * FROM commitments ORDER BY id")) if c["level"] != "par"
    ]


def _engagement(engagements, metrics, categories=None):
    """Cible de l'engagement du marché portant exactement sur ces indicateurs et ces catégories (sinon None)."""
    for c in engagements:
        if (
            set(c["metrics"]) == set(metrics)
            and set(c["categories"] or []) == set(categories or [])
            and not c["gammes"]
        ):
            return c["target"]
    return None


def _periode(d1, d2):
    """Lignes d'achat et repas valorisés de la période."""
    lignes = load_lines(d1, d2)
    repas = meals_metrics(d1, d2)
    valorises, cout, convives, prix = compute_price_per_meal(repas)
    return {"lignes": lignes, "repas": valorises, "cout": cout, "convives": convives, "prix": prix}


def _paire(p_mois, p_cumul, fonction):
    """Valeur d'un indicateur sur le mois et sur le cumul."""
    return {"mois": fonction(p_mois["lignes"]), "cumul": fonction(p_cumul["lignes"])}


def _tableau(familles, p_mois, p_cumul, engagements, metrics, pred):
    """Une ligne par famille + « Toutes denrées » : total du mois, engagement, part du mois et du cumul."""
    rows = []
    for nom, cats in [*familles, ("Toutes denrées", None)]:
        rows.append(
            {
                "nom": nom,
                "total_ht": _total(p_mois["lignes"], cats),
                "engagement": _engagement(engagements, metrics, cats),
                **_paire(p_mois, p_cumul, lambda l, cats=cats: _part(l, pred, cats)),
            }
        )
    return rows


def _prix(p, tarif):
    """Prix par repas d'une période et déficit par rapport au tarif de vente."""
    prix = p["prix"]
    ecart = round(prix - tarif, 2) if prix is not None and prix > tarif else 0
    return {
        "repas": len(p["repas"]),
        "convives": p["convives"],
        "cout_matieres": p["cout"],
        "prix_par_repas": prix,
        "deficit_par_repas": ecart,
        "deficit_total": round(ecart * p["convives"], 2),
        "achats_ht": round(sum(r["spend"] for r in p["lignes"]), 2),
    }


def _statut_engagements(engagements, p):
    out = []
    for c in engagements:
        if "price_per_meal" in c["metrics"]:
            actual = p["prix"]
        else:
            actual = lines_metric_multi(p["lignes"], c["metrics"], c["categories"] or None, c["gammes"] or None)
        out.append((c, actual, commitment_status(actual, c["mode"], c["target"])))
    return out


def _points(b):
    """Texte de synthèse (français) : ce qui est tenu, ce qui ne l'est pas, et la tendance par rapport au cumul."""

    def eng(nom, reel, cible, sens="min"):
        if reel is None:
            return f"{nom} : pas de donnée."
        ok = reel <= cible if sens == "max" else reel >= cible
        return f"{nom} : {fr(reel, 2)} % pour un engagement de {fr(cible, 0)} %. " + (
            "Objectif respecté." if ok else "Objectif non atteint."
        )

    pts = []
    lab, ori, g = b["labels"], b["origine"], b["frais"][-1]
    bio, egalim = lab["bio"], lab["egalim"]
    txt = f"Labels : {fr(bio['mois'], 2) if bio['mois'] is not None else '—'} % de produits bio"
    if bio["engagement"] is not None:
        txt += f" (engagement {fr(bio['engagement'], 0)} %)"
    if egalim["mois"] is not None:
        txt += f" et {fr(egalim['mois'], 2)} % de produits bio + autres labels"
        if egalim["engagement"] is not None:
            txt += f" (engagement {fr(egalim['engagement'], 0)} %)"
    manques = [
        x
        for x in (bio, egalim)
        if x["engagement"] is not None and x["mois"] is not None and x["mois"] < x["engagement"]
    ]
    pts.append(
        txt
        + ". "
        + ("Engagement non atteint." if manques else "Engagements respectés." if bio["engagement"] is not None else "")
    )
    loc = ori["local"]
    txt = (
        f"Origine : {fr(ori['france']['mois'], 2)} % d'origine France"
        if ori["france"]["mois"] is not None
        else "Origine : pas de donnée"
    )
    if loc["mois"] is not None:
        txt += f" et {fr(loc['mois'], 2)} % de produits locaux"
        if loc["engagement"] is not None:
            txt += f" (engagement {fr(loc['engagement'], 0)} %). " + (
                "Objectif respecté." if loc["mois"] >= loc["engagement"] else "Objectif local non atteint."
            )
    pts.append(txt.rstrip() if txt.endswith(".") else txt + ".")
    direct = b["direct"][-1]
    if direct["engagement"] is not None:
        pts.append(eng("Approvisionnement direct", direct["mois"], direct["engagement"]))
    elif direct["mois"] is not None:
        pts.append(f"Approvisionnement direct : {fr(direct['mois'], 2)} %.")
    if g["engagement"] is not None:
        pts.append(eng("Produits frais", g["mois"], g["engagement"]))
    elif g["mois"] is not None:
        pts.append(f"Produits frais : {fr(g['mois'], 2)} %.")
    ecarts = []
    for rubrique, nom in ((b["direct"], "direct"), (b["frais"], "frais")):
        for r in rubrique[:-1]:
            if r["engagement"] is not None and r["mois"] is not None and r["mois"] < r["engagement"] and r["total_ht"]:
                ecarts.append(
                    (
                        r["mois"] - r["engagement"],
                        f"{r['nom']} ({nom} {fr(r['mois'], 1)} %, {fr(r['mois'] - r['engagement'], 1)} pts)",
                    )
                )
    if ecarts:
        pts.append("Points d'attention : " + ", ".join(t for _, t in sorted(ecarts)[:5]) + ".")
    return pts


def _tendance(b):
    """Écart du mois avec le cumul depuis septembre, pour les indicateurs clés."""
    cles = [
        ("Part de bio", b["labels"]["bio"]),
        ("Bio + autres labels", b["labels"]["egalim"]),
        ("Produits locaux", b["origine"]["local"]),
        ("Origine France", b["origine"]["france"]),
        ("Approvisionnement direct", b["direct"][-1]),
        ("Produits frais", b["frais"][-1]),
    ]
    out = []
    for nom, v in cles:
        if v["mois"] is not None and v["cumul"] is not None:
            out.append(
                {
                    "indicateur": nom,
                    "mois": v["mois"],
                    "cumul": v["cumul"],
                    "ecart_points": round(v["mois"] - v["cumul"], 1),
                }
            )
    return out


def bilan(mois, masquer_prix=False):
    """Bilan du mois « AAAA-MM » et comparaison avec le cumul depuis le 1er septembre de l'année de cantine."""
    d1, d2, rentree = bornes(mois)
    tarif = get_tarif_repas()
    engagements = _engagements_marche()
    p_mois, p_cumul = _periode(d1, d2), _periode(rentree, d2)

    def indicateur(metric, categories=None, hors=None):
        pred = metric_pred(metric)
        sous = (lambda l: [r for r in l if r["category"] != hors]) if hors else (lambda l: l)
        return {
            "engagement": _engagement(engagements, [metric], categories) if not hors else None,
            **_paire(p_mois, p_cumul, lambda l: _part(sous(l), pred, categories)),
        }

    def origine(cle, pred):
        return {
            "engagement": None,
            **_paire(p_mois, p_cumul, lambda l: _part(l, pred)),
            "cle": cle,
        }

    labels = {
        "bio": indicateur("bio"),
        "egalim": indicateur("egalim"),
        "bio_hors_mer": indicateur("bio", hors=PECHE),
        "autres_labels": {
            "engagement": None,
            **_paire(p_mois, p_cumul, lambda l: _part(l, lambda r: r["label_egalim"] == "autre")),
        },
        "sans_label": {
            "engagement": None,
            **_paire(p_mois, p_cumul, lambda l: _part(l, lambda r: r["label_egalim"] not in ("bio", "autre"))),
        },
    }
    ori = {
        "france": origine("france", lambda r: r["provenance"] in FRANCE),
        "local": indicateur("local"),
        "hors_france": origine("hors_france", lambda r: r["provenance"] in ("ue", "international")),
        "repartition": [
            {"cle": k, "nom": nom, **_paire(p_mois, p_cumul, lambda l, k=k: _part(l, lambda r: r["provenance"] == k))}
            for k, nom in PROVENANCES.items()
        ],
    }
    ori["france"]["engagement"] = _engagement(engagements, ["provenance:france"])
    categories_france = [
        {
            "nom": nom,
            "engagement": None,
            **_paire(p_mois, p_cumul, lambda l, cats=cats: _part(l, lambda r: r["provenance"] in FRANCE, cats)),
        }
        for nom, cats in FAMILLES_ORIGINE
    ]
    categories_france.append(
        {
            "nom": "Poisson sous label MSC",
            "engagement": None,
            **_paire(
                p_mois, p_cumul, lambda l: _part(l, lambda r: "msc" in (r.get("label_detail") or "").lower(), [PECHE])
            ),
        }
    )
    direct = _tableau(FAMILLES_DIRECT, p_mois, p_cumul, engagements, ["direct"], metric_pred("direct"))
    frais = _tableau(FAMILLES_FRAIS, p_mois, p_cumul, engagements, ["gamme:1"], metric_pred("gamme:1"))
    gammes = [
        {"nom": nom, **_paire(p_mois, p_cumul, lambda l, k=k: _part(l, lambda r: r["gamme"] == k))}
        for k, nom in GAMMES.items()
    ]

    statuts_m, statuts_c = _statut_engagements(engagements, p_mois), _statut_engagements(engagements, p_cumul)
    liste_engagements = [
        {
            "nom": c["label"],
            "indicateur": " + ".join(c["metrics"]) + (" · " + ", ".join(c["categories"]) if c["categories"] else ""),
            "objectif": c["target"],
            "sens": c["mode"],
            "mois": {"reel": a1, "statut": s1},
            "cumul": {"reel": a2, "statut": s2},
        }
        for (c, a1, s1), (_, a2, s2) in zip(statuts_m, statuts_c)
    ]

    evolution = []
    a, m = (int(x) for x in rentree.split("-")[:2])
    fin_a, fin_m = (int(x) for x in mois.split("-"))
    while (a, m) <= (fin_a, fin_m):
        di, df, _ = bornes(f"{a:04d}-{m:02d}")
        p = p_mois if (a, m) == (fin_a, fin_m) else _periode(di, df)
        evolution.append(
            {
                "mois": f"{a:04d}-{m:02d}",
                "libelle": f"{MOIS[m - 1]} {a}",
                "achats_ht": round(sum(r["spend"] for r in p["lignes"]), 2),
                "repas": len(p["repas"]),
                "prix_par_repas": p["prix"],
                "bio": _part(p["lignes"], metric_pred("bio")),
                "egalim": _part(p["lignes"], metric_pred("egalim")),
                "local": _part(p["lignes"], metric_pred("local")),
                "direct": _part(p["lignes"], metric_pred("direct")),
                "frais": _part(p["lignes"], metric_pred("gamme:1")),
            }
        )
        a, m = mois_suivant(a, m)

    jours = sorted(
        (
            {"date": r["date"], "prix": r["per_guest"], "convives": r["guests"]}
            for r in p_mois["repas"]
            if r.get("per_guest") is not None
        ),
        key=lambda j: j["date"],
    )
    res = {
        "mois": mois,
        "libelle": f"{MOIS[int(mois[5:]) - 1].capitalize()} {mois[:4]}",
        "periode_mois": [d1, d2],
        "periode_cumul": [rentree, d2],
        "libelle_cumul": f"depuis septembre {rentree[:4]}",
        "tarif_repas": tarif,
        "prix": {"mois": _prix(p_mois, tarif), "cumul": _prix(p_cumul, tarif), "jours": jours},
        "labels": labels,
        "origine": ori,
        "categories_france": categories_france,
        "direct": direct,
        "frais": frais,
        "gammes": gammes,
        "engagements": liste_engagements,
        "evolution": evolution,
    }
    res["synthese"] = _points(res)
    res["tendance"] = _tendance(res)
    res["prix_masques"] = False
    if masquer_prix:  # profil « statistiques » : aucun montant ni prix
        res["prix"] = {
            "mois": {"repas": res["prix"]["mois"]["repas"]},
            "cumul": {"repas": res["prix"]["cumul"]["repas"]},
            "jours": [],
        }
        for r in res["direct"] + res["frais"]:
            r["total_ht"] = None
        for e in res["evolution"]:
            e["achats_ht"] = e["prix_par_repas"] = None
        res["engagements"] = [e for e in res["engagements"] if "price_per_meal" not in e["indicateur"]]
        res["prix_masques"] = True
    return res
