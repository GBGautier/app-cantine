"""Prix d'un produit à une date donnée, d'après son historique."""


def price_at(hist, pid, day, fallback):
    """Prix d'un produit à une date (dernier relevé connu à cette date), à défaut le prix courant."""
    seq = hist.get(pid)
    if not seq:
        return fallback
    best = None
    for d, p in seq:
        if d <= (day or ""):
            best = p
        else:
            break
    return best if best is not None else seq[0][1]
