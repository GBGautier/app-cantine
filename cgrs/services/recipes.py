"""Coût d'une recette."""

from cgrs.services.prices import price_at


def recipe_cost(items, nb_mat, nb_elem, nb_adu, hist, day):
    """Estime le coût d'une recette pour les effectifs donnés (maternelles, élémentaires, adultes).

    items : ingrédients (product_id, qty_maternelle / qty_elementaire / qty_adulte en grammes par convive, unit_price) ;
    hist : historique des prix ; day : date de référence du prix. Rend None sans ingrédients, sinon le coût et le
    nombre d'ingrédients sans prix (non comptés). Les grammages sont en g : conversion en kg pour un prix en €/kg.
    """
    if not items:
        return None
    total = 0.0
    unpriced = 0
    for it in items:
        if not it["product_id"]:
            continue
        price = price_at(hist, it["product_id"], day, it["unit_price"])
        if price is None:
            unpriced += 1
            continue
        qty = (
            (it["qty_maternelle"] or 0) * nb_mat / 1000
            + (it["qty_elementaire"] or 0) * nb_elem / 1000
            + (it["qty_adulte"] or 0) * nb_adu / 1000
        )  # grammages en g → kg pour un prix en €/kg
        total += qty * price
    return {"cost": round(total, 2), "unpriced": unpriced}
