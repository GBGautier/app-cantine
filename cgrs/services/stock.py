"""Stock : reçu - sorti + ajustements d'inventaire."""

from cgrs.services.units import convert


def stock_rows(products, receipts, usages, adjustments):
    """Stock de chaque produit (et unité) : quantités reçues, sorties, ajustées, stock et valeur.

    products : dictionnaire {id: produit} ; receipts / usages / adjustments : lignes (product_id, qty, unit) des
    réceptions, des sorties pour les repas et des ajustements d'inventaire. Les quantités sont ramenées à l'unité du
    produit ; une unité incompatible est suivie à part, dans sa propre unité. Un produit inconnu est ignoré.
    """
    prods = products
    acc = {}

    def add(pid, field, qty, unit):
        p = prods.get(pid)
        if not p or qty is None:
            return
        pu = p["unit"] or "kg"
        q, u = convert(qty, unit or pu, pu), pu
        if q is None:  # unité incompatible avec celle du produit : suivie à part
            q, u = qty, unit
        r = acc.setdefault((pid, u), {"in": 0.0, "out": 0.0, "adj": 0.0})
        r[field] += q

    for l in receipts:
        add(l["product_id"], "in", l["qty"], l["unit"])
    for i in usages:
        add(i["product_id"], "out", i["qty"], i["unit"])
    for a in adjustments:
        add(a["product_id"], "adj", a["qty"], a["unit"])
    rows_ = []
    for (pid, unit), r in acc.items():
        p = prods[pid]
        stock = round(r["in"] - r["out"] + r["adj"], 3)
        value = (
            round(stock * p["unit_price"], 2) if p["unit_price"] is not None and unit == (p["unit"] or "kg") else None
        )
        rows_.append(
            {
                "product_id": pid,
                "ref": p["ref"],
                "name": p["name"],
                "category": p["category"],
                "supplier_id": p["supplier_id"],
                "supplier_name": p["supplier_name"],
                "unit": unit,
                "received": round(r["in"], 3),
                "used": round(r["out"], 3),
                "adjusted": round(r["adj"], 3),
                "stock": stock,
                "value": value,
            }
        )
    rows_.sort(key=lambda r: (r["name"] or "").lower())
    return rows_
