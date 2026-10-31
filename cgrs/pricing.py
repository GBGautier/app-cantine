"""Historique des prix des produits."""

from cgrs import db


def add_history(product_id, day, price, unit, order_id, source):
    db.execute(
        "INSERT INTO price_history (product_id, date, price, unit, order_id, source) VALUES (?,?,?,?,?,?)",
        (product_id, day, price, unit, order_id, source),
    )


def refresh_product_price(product_id):
    """Le prix courant d'un produit = dernier prix de son historique."""
    last = db.one(
        "SELECT price FROM price_history WHERE product_id=? ORDER BY date DESC, id DESC LIMIT 1", (product_id,)
    )
    if last:
        db.execute("UPDATE products SET unit_price=? WHERE id=?", (last["price"], product_id))


def load_history():
    h = {}
    for r in db.rows("SELECT product_id, date, price FROM price_history ORDER BY date, id"):
        h.setdefault(r["product_id"], []).append((r["date"] or "", r["price"]))
    return h


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
