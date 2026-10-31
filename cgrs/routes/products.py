"""Produits, fiches techniques et prix."""

from datetime import date as date_cls
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from cgrs import db
from cgrs.config import UPLOADS
from cgrs.pricing import add_history, load_history, price_at
from cgrs.security import READ, WRITE
from cgrs.uploads import save_upload
from cgrs.utils import convert, insert, update


router = APIRouter()


class Product(BaseModel):
    ref: Optional[str] = None
    name: str
    supplier_id: Optional[int] = None
    category: Optional[str] = None
    gamme: Optional[str] = None
    label_egalim: str = "bio"
    label_detail: Optional[str] = None
    provenance: Optional[str] = None
    direct_producteur: int = 0
    avoid: int = 0            # « à éviter » : produit signalé (affiché en orange dans la liste)
    favorite: int = 0         # produit favori (étoile)
    unit: Optional[str] = "kg"
    unit_price: Optional[float] = None
    notes: Optional[str] = None


@router.get("/api/products")
def products(user: dict = READ):
    return db.rows(
        "SELECT p.*, s.name AS supplier_name FROM products p "
        "LEFT JOIN suppliers s ON s.id=p.supplier_id ORDER BY p.name")


def fill_unpriced_lines(product_id):
    """Un prix saisi sur la fiche produit complète les lignes de réception restées sans prix (bon de livraison importé
    sans prix). Les lignes déjà chiffrées ne bougent pas : un changement de prix ne réécrit jamais les anciennes factures."""
    p = db.one("SELECT unit, unit_price FROM products WHERE id=?", (product_id,))
    if not p or not p["unit_price"]:
        return
    touched = set()
    for l in db.rows("SELECT id, order_id, qty, unit FROM order_lines WHERE product_id=? AND (unit_price IS NULL OR unit_price=0) "
                     "AND (total_ht IS NULL OR total_ht=0) AND qty > 0", (product_id,)):
        q = convert(l["qty"], l["unit"] or p["unit"], p["unit"] or l["unit"])
        if q is None:
            continue
        price_line = round(p["unit_price"] * q / l["qty"], 4)
        db.execute("UPDATE order_lines SET unit_price=?, total_ht=? WHERE id=?", (price_line, round(q * p["unit_price"], 2), l["id"]))
        touched.add(l["order_id"])
    for oid in touched:   # total de la réception : recalculé seulement s'il était vide ou égal à la somme des lignes
        o = db.one("SELECT total_ht FROM orders WHERE id=?", (oid,))
        s_all = db.one("SELECT COALESCE(SUM(total_ht),0) AS s FROM order_lines WHERE order_id=?", (oid,))["s"]
        if not o["total_ht"]:
            db.execute("UPDATE orders SET total_ht=? WHERE id=?", (round(s_all, 2), oid))


@router.post("/api/products")
@db.atomic
def create_product(p: Product, user: dict = WRITE):
    pid = insert("products", p)
    if p.unit_price is not None:
        add_history(pid, date_cls.today().isoformat(), p.unit_price, p.unit, None, "manuel")
        fill_unpriced_lines(pid)
    return {"id": pid}


@router.put("/api/products/{id}")
@db.atomic
def edit_product(id: int, p: Product, user: dict = WRITE):
    old = db.one("SELECT unit_price FROM products WHERE id=?", (id,))
    if not old:
        raise HTTPException(404)
    update("products", id, p)
    if p.unit_price is not None and (old["unit_price"] is None or abs(old["unit_price"] - p.unit_price) > 1e-9):
        add_history(id, date_cls.today().isoformat(), p.unit_price, p.unit, None, "manuel")
    fill_unpriced_lines(id)
    return {"ok": True}


@router.delete("/api/products/{id}")
def delete_product(id: int, user: dict = WRITE):
    db.execute("DELETE FROM products WHERE id=?", (id,))
    return {"ok": True}


@router.post("/api/products/{id}/favorite")
def toggle_favorite(id: int, user: dict = WRITE):
    """Bascule l'étoile « favori » d'un produit, sans passer par la fiche complète."""
    p = db.one("SELECT id FROM products WHERE id=?", (id,))
    if not p:
        raise HTTPException(404)
    db.execute("UPDATE products SET favorite = 1 - COALESCE(favorite, 0) WHERE id=?", (id,))
    return {"favorite": db.one("SELECT favorite FROM products WHERE id=?", (id,))["favorite"]}


@router.get("/api/products/{id}/prices")
def product_prices(id: int, user: dict = READ):
    return db.rows(
        "SELECT h.id, h.date, h.price, h.unit, h.source, o.ref AS order_ref, o.kind AS order_kind "
        "FROM price_history h LEFT JOIN orders o ON o.id=h.order_id WHERE h.product_id=? "
        "ORDER BY h.date DESC, h.id DESC", (id,))


@router.get("/api/products/prices-at")
def prices_at_date(date: str, user: dict = READ):
    """Prix de tous les produits à une date donnée (dernier relevé ≤ date)."""
    hist = load_history()
    prods = db.rows("SELECT id, unit_price FROM products")
    return {str(p["id"]): price_at(hist, p["id"], date, p["unit_price"]) for p in prods}


@router.post("/api/products/{id}/datasheet")
async def upload_datasheet(id: int, file: UploadFile = File(...), user: dict = WRITE):
    if not db.one("SELECT 1 AS x FROM products WHERE id=?", (id,)):
        raise HTTPException(404)
    name = await save_upload(file, prefix="fiche_")
    db.execute("UPDATE products SET datasheet=? WHERE id=?", (name, id))
    return {"datasheet": name}


@router.delete("/api/products/{id}/datasheet")
def delete_datasheet(id: int, user: dict = WRITE):
    r = db.one("SELECT datasheet FROM products WHERE id=?", (id,))
    if r and r["datasheet"]:
        (UPLOADS / Path(r["datasheet"]).name).unlink(missing_ok=True)
    db.execute("UPDATE products SET datasheet=NULL WHERE id=?", (id,))
    return {"ok": True}
