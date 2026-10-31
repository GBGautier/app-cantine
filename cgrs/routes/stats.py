"""Statistiques."""

from typing import Optional

from fastapi import APIRouter

from cgrs import db
from cgrs.constants import GAMMES, LOCAL, PROVENANCES
from cgrs.routes.commitments import commitment_out
from cgrs.routes.meals import meals_metrics
from cgrs.routes.meta import metric_options
from cgrs.security import ANY
from cgrs.services.stats import (
    breakdown,
    commitment_status,
    fill_spend,
    hide_prices,
    lines_metric_multi,
    price_per_meal as compute_price_per_meal,
    share_of_spend,
)


router = APIRouter()


@router.get("/api/stats")
def stats(date_from: Optional[str] = None, date_to: Optional[str] = None, user: dict = ANY):
    """Statistiques sur la période. Le prix par repas = coûts matières des repas ÷ nombre de convives.

    Pour le profil « stats », tout ce qui révèle un prix est retiré de la réponse côté serveur.
    """
    where, args = ["1=1"], []
    if date_from:
        where.append("o.date >= ?")
        args.append(date_from)
    if date_to:
        where.append("o.date <= ?")
        args.append(date_to)
    w = " AND ".join(where)
    lines = db.rows(
        "SELECT l.order_id, o.total_ht AS order_total, l.qty, COALESCE(l.total_ht, l.qty*l.unit_price) AS spend, "
        "p.label_egalim, p.provenance, p.gamme, p.category, p.direct_producteur, s.name AS supplier "
        "FROM order_lines l JOIN orders o ON o.id=l.order_id "
        "LEFT JOIN products p ON p.id=l.product_id LEFT JOIN suppliers s ON s.id=o.supplier_id "
        f"WHERE {w}",
        args,
    )
    fill_spend(lines)
    total = round(sum(r["spend"] for r in lines), 2)

    def pct(pred):
        return share_of_spend(lines, pred, total)

    mm = meals_metrics(date_from, date_to)
    priced, cost_total, guests_priced, price_per_meal = compute_price_per_meal(mm)
    daily = sorted(
        (
            {
                "date": m["date"],
                "guests": m["guests"],
                "cost": m["cost"],
                "per_guest": m["per_guest"],
                "pct_bio": m["pct_bio"],
                "pct_local": m["pct_local"],
            }
            for m in mm
        ),
        key=lambda d: d["date"],
    )

    labels = dict(metric_options())
    engagements = []
    for c in [commitment_out(r) for r in db.rows("SELECT * FROM commitments ORDER BY id")]:
        metrics = c["metrics"]
        categories = c["categories"] or None
        gammes = c["gammes"] or None
        if "price_per_meal" in metrics:
            actual = price_per_meal
        else:
            actual = lines_metric_multi(lines, metrics, categories, gammes)
        status = commitment_status(actual, c["mode"], c["target"])
        metric_label = " + ".join(labels.get(m, m) for m in metrics)
        engagements.append({**c, "metric_label": metric_label, "actual": actual, "status": status})

    result = {
        "commitments": engagements,
        "total_ht": total,
        "nb_lines": len(lines),
        "meals": len(mm),
        "meals_priced": len(priced),
        "guests": sum(m["guests"] for m in mm),
        "cost_total": cost_total,
        "price_per_meal": price_per_meal,
        "pct_bio": pct(lambda r: r["label_egalim"] == "bio"),
        "pct_egalim": pct(lambda r: r["label_egalim"] in ("bio", "autre")),
        "pct_local": pct(lambda r: r["provenance"] in LOCAL),
        "pct_direct": pct(lambda r: r["direct_producteur"]),
        "by_label": breakdown(lines, "label_egalim", {"bio": "Bio", "autre": "Autre label", "sans": "Sans label"}),
        "by_provenance": breakdown(lines, "provenance", PROVENANCES),
        "by_gamme": breakdown(lines, "gamme", GAMMES),
        "by_category": breakdown(lines, "category"),
        "by_supplier": breakdown(lines, "supplier"),
        "daily": daily,
        "prices_hidden": False,
    }
    if user["role"] == "stats":
        hide_prices(result)
    return result
