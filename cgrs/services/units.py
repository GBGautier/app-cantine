"""Unités de mesure et conversions."""

UNITS = {
    "kg": ("mass", 1),
    "g": ("mass", 0.001),
    "l": ("vol", 1),
    "litre": ("vol", 1),
    "litres": ("vol", 1),
    "ml": ("vol", 0.001),
    "cl": ("vol", 0.01),
    "dl": ("vol", 0.1),
    "unité": ("count", 1),
    "unités": ("count", 1),
    "pièce": ("count", 1),
    "pièces": ("count", 1),
    "u": ("count", 1),
    "pc": ("count", 1),
    "colis": ("colis", 1),
    "botte": ("botte", 1),
    "barquette": ("barquette", 1),
    "bidon": ("bidon", 1),
    "boite": ("boite", 1),
}
# Écritures courantes d'une même unité (saisies à la main ou lues dans un PDF) : sans cela, « 2 pce » sur un produit
# en « pièce » était suivi à part, et le stock du produit ne diminuait pas.
ALIASES = {
    "kilo": "kg",
    "kilos": "kg",
    "kgs": "kg",
    "gr": "g",
    "grs": "g",
    "gramme": "g",
    "grammes": "g",
    "lt": "l",
    "ltr": "l",
    "pce": "pc",
    "pces": "pc",
    "pcs": "pc",
    "piece": "pièce",
    "pieces": "pièces",
    "unite": "unité",
    "unites": "unités",
    "boîte": "boite",
    "boîtes": "boite",
    "boites": "boite",
}


def unit_info(u):
    u = (u or "").strip().lower().rstrip(".").strip()
    if not u:
        return None
    u = ALIASES.get(u, u)
    return UNITS.get(u) or ("x:" + u, 1)


def convert(qty, from_u, to_u):
    """Convertit une quantité d'une unité à l'autre ; None si incompatibles. Unité inconnue = même unité."""
    if qty is None:
        return None
    a, b = unit_info(from_u), unit_info(to_u)
    if a is None or b is None:
        return qty
    if a[0] != b[0]:
        return None
    return qty * a[1] / b[1]
