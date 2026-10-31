"""Calculs des statistiques d'achats : répartitions, pourcentages Egalim / local, statut des engagements.

Les « lignes » sont des dictionnaires issus des réceptions, avec au minimum `spend` (montant HT) et, selon le calcul,
`label_egalim`, `provenance`, `gamme`, `category`, `direct_producteur`, `supplier`.
"""

from cgrs.constants import LOCAL


def breakdown(rows_, key, labels=None):
    """Répartition des dépenses selon `key` : montant et part (%) de chaque valeur, de la plus grosse à la plus petite."""
    total = sum(r["spend"] for r in rows_) or 0
    agg = {}
    for r in rows_:
        k = r[key] if r[key] not in (None, "") else "non renseigné"
        agg[k] = agg.get(k, 0) + r["spend"]
    out = []
    for k, v in sorted(agg.items(), key=lambda kv: -kv[1]):
        out.append(
            {
                "key": k,
                "label": (labels or {}).get(k, k),
                "amount": round(v, 2),
                "pct": round(100 * v / total, 1) if total else 0,
            }
        )
    return out


def metric_pred(metric):
    """Retourne le prédicat correspondant à un indicateur."""
    kind, _, key = metric.partition(":")
    preds = {
        "bio": lambda r: r["label_egalim"] == "bio",
        "egalim": lambda r: r["label_egalim"] in ("bio", "autre"),
        "local": lambda r: r["provenance"] in LOCAL,
        "direct": lambda r: bool(r["direct_producteur"]),
        "label": lambda r: r["label_egalim"] == key,
        "provenance": lambda r: r["provenance"] == key,
        "gamme": lambda r: r["gamme"] == key,
    }
    return preds.get(kind)


def lines_metric(lines, metric, category=None):
    """Calcul pour un seul indicateur / une seule catégorie (compatibilité ancienne API)."""
    subset = [r for r in lines if not category or r["category"] == category]
    total = sum(r["spend"] for r in subset)
    if not total:
        return None
    pred = metric_pred(metric)
    if not pred:
        return None
    return round(100 * sum(r["spend"] for r in subset if pred(r)) / total, 1)


def lines_metric_multi(lines, metrics, categories=None, gammes=None):
    """Calcul pour plusieurs indicateurs, catégories et/ou gammes.

    - Si plusieurs indicateurs : on vérifie qu'une ligne respecte AU MOINS UN des indicateurs (union).
    - Si des catégories sont précisées : on ne garde que les lignes de ces catégories.
    - Si des gammes sont précisées : on filtre supplémentairement sur ces gammes.
    Le résultat est le % de dépenses satisfaisant au moins un indicateur sur l'assiette filtrée.
    """
    subset = lines
    if categories:
        subset = [r for r in subset if r["category"] in categories]
    if gammes:
        subset = [r for r in subset if r["gamme"] in gammes]
    total = sum(r["spend"] for r in subset)
    if not total:
        return None
    if not metrics:
        return None
    preds = [p for p in (metric_pred(m) for m in metrics) if p is not None]
    if not preds:
        return None
    return round(100 * sum(r["spend"] for r in subset if any(p(r) for p in preds)) / total, 1)


def fill_spend(lines):
    """Complète le montant (`spend`) des lignes sans prix, en place.

    Lignes sans montant (bon de livraison sans prix) : si le total HT de la réception est connu, l'écart avec les
    lignes chiffrées est réparti sur ces lignes (au prorata des quantités) pour que les achats soient bien comptés.
    Chaque ligne doit porter `order_id`, `order_total`, `qty` et `spend` (None ou 0 = sans montant).
    """
    by_order = {}
    for r in lines:
        by_order.setdefault(r["order_id"], []).append(r)
    for rs in by_order.values():
        open_ = [r for r in rs if not r["spend"]]
        known = sum(r["spend"] or 0 for r in rs)
        rest = (rs[0]["order_total"] or 0) - known
        if open_ and rest > 0.005:
            weights = [r["qty"] or 0 for r in open_]
            tw = sum(weights)
            for r, wgt in zip(open_, weights):
                r["spend"] = rest * (wgt / tw if tw else 1 / len(open_))
    for r in lines:
        r["spend"] = r["spend"] or 0


def share_of_spend(lines, pred, total):
    """Part (%) des dépenses dont les lignes vérifient `pred` ; 0 si le total est nul."""
    return round(100 * sum(r["spend"] for r in lines if pred(r)) / total, 1) if total else 0


def price_per_meal(meals):
    """Coût matière total, nombre de convives et prix par repas, sur les repas chiffrés (coût et convives > 0).

    Rend (repas chiffrés, coût total, convives des repas chiffrés, prix par repas ou None).
    """
    priced = [m for m in meals if m["cost"] > 0 and m["guests"] > 0]
    cost_total = round(sum(m["cost"] for m in priced), 2)
    guests_priced = sum(m["guests"] for m in priced)
    return priced, cost_total, guests_priced, round(cost_total / guests_priced, 2) if guests_priced else None


def commitment_status(actual, mode, target):
    """« nodata » sans résultat, sinon « ok » / « ko » selon que l'objectif (minimum, ou maximum si mode « max ») est tenu."""
    if actual is None:
        return "nodata"
    if mode == "max":
        return "ok" if actual <= target else "ko"
    return "ok" if actual >= target else "ko"


PRICE_FIELDS = ("total_ht", "cost_total", "price_per_meal", "daily", "nb_lines")
BREAKDOWNS = ("by_label", "by_provenance", "by_gamme", "by_category", "by_supplier")


def hide_prices(result):
    """Profil « stats » : retire, en place, tout ce qui révèle un prix (montants, prix par repas, engagements de prix)."""
    for k in PRICE_FIELDS:
        result.pop(k, None)
    for k in BREAKDOWNS:
        for row in result[k]:
            row.pop("amount", None)
    result["commitments"] = [
        c for c in result["commitments"] if "price_per_meal" not in c.get("metrics", [c.get("metric", "")])
    ]
    result["prices_hidden"] = True
    return result
