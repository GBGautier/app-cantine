"""Coût matière des repas et liste de courses."""

from cgrs.constants import CATEGORIES, LOCAL
from cgrs.services.prices import price_at
from cgrs.services.units import convert


def meal_metrics(meals, items, hist):
    """Une ligne par repas : coût matière, coût par convive, parts bio et locales.

    meals : repas (id, date, effectifs, guests, menu…) ; items : lignes sorties pour ces repas (meal_id, product_id,
    qty, unit, prix_reel, mdate, punit, unit_price, label_egalim, provenance) ; hist : historique des prix.
    Le prix d'une ligne est le prix réel saisi à la main, à défaut le prix du produit à la date du repas.
    Une ligne sans prix ou dont l'unité n'est pas convertible n'est pas comptée (elle figure dans « unpriced »).
    """
    acc = {m["id"]: {"cost": 0.0, "bio": 0.0, "local": 0.0, "n": 0, "unpriced": 0} for m in meals}
    for it in items:
        a = acc[it["meal_id"]]
        a["n"] += 1
        # Prix réel saisi manuellement > historique calculé
        if it["prix_reel"] is not None:
            price = it["prix_reel"]
        else:
            price = price_at(hist, it["product_id"], it["mdate"], it["unit_price"])
        qty = convert(it["qty"], it["unit"] or it["punit"], it["punit"] or it["unit"])
        if price is None or qty is None:
            a["unpriced"] += 1
            continue
        c = qty * price
        a["cost"] += c
        if it["label_egalim"] == "bio":
            a["bio"] += c
        if it["provenance"] in LOCAL:
            a["local"] += c
    out = []
    for m in meals:
        a = acc[m["id"]]
        cost = round(a["cost"], 2)
        out.append(
            {
                "id": m["id"],
                "date": m["date"],
                "nb_maternelles": m["nb_maternelles"] or 0,
                "nb_elementaires": m["nb_elementaires"] or 0,
                "nb_adultes": m["nb_adultes"] or 0,
                "guests": m["guests"],
                "notes": m["notes"],
                "entree": m["entree"],
                "plat": m["plat"],
                "accompagnement": m["accompagnement"],
                "laitage": m["laitage"],
                "dessert": m["dessert"],
                "commentaire_post": m["commentaire_post"],
                "statut": m["statut"] or "prevu",
                "modif_prevu": bool(m["modif_prevu"]),
                "nb_items": a["n"],
                "unpriced": a["unpriced"],
                "cost": cost,
                "per_guest": round(cost / m["guests"], 2) if cost and m["guests"] else None,
                "pct_bio": round(100 * a["bio"] / a["cost"], 1) if a["cost"] else None,
                "pct_local": round(100 * a["local"] / a["cost"], 1) if a["cost"] else None,
            }
        )
    return out


def shopping_list(rows):
    """Liste de courses : quantités par produit (et unité), triées par catégorie puis par nom.

    rows : lignes sorties (product_id, qty, unit, name, category, punit). Les quantités sont ramenées à l'unité du
    produit ; si l'unité de la ligne est incompatible, la ligne est gardée telle quelle, dans son unité.
    """
    acc = {}
    for r in rows:
        pu = r["punit"] or r["unit"] or "kg"
        q = convert(r["qty"], r["unit"] or pu, pu)
        u = pu
        if q is None:  # unité incompatible avec celle du produit : gardée telle quelle
            q, u = r["qty"], r["unit"] or pu
        a = acc.setdefault(
            (r["product_id"], u),
            {
                "product_id": r["product_id"],
                "label": r["name"],
                "category": r["category"] or "Autre",
                "unit": u,
                "qty": 0.0,
            },
        )
        a["qty"] += q
    out = sorted(
        acc.values(),
        key=lambda a: (
            CATEGORIES.index(a["category"]) if a["category"] in CATEGORIES else len(CATEGORIES),
            a["category"].lower(),
            a["label"].lower(),
        ),
    )
    for a in out:
        a["qty"] = round(a["qty"], 3)
    return out
