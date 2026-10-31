"""Stocks : reçu - sorti + ajustements d'inventaire."""

from datetime import date as date_cls
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cgrs import db
from cgrs.security import READ, WRITE
from cgrs.services.stock import stock_rows


router = APIRouter()


def compute_stock():
    prods = {
        p["id"]: p
        for p in db.rows(
            "SELECT p.*, s.name AS supplier_name FROM products p LEFT JOIN suppliers s ON s.id=p.supplier_id"
        )
    }
    return stock_rows(
        prods,
        db.rows("SELECT product_id, qty, unit FROM order_lines WHERE product_id IS NOT NULL"),
        db.rows("SELECT product_id, qty, unit FROM meal_items"),
        db.rows("SELECT product_id, qty, unit FROM stock_adjustments"),
    )


class StockAdjust(BaseModel):
    product_id: int
    unit: Optional[str] = None
    target_qty: float
    reason: Optional[str] = None


@router.get("/api/stock")
def stock(user: dict = READ):
    adj = db.rows(
        "SELECT a.id, a.date, a.qty, a.unit, a.reason, a.username, p.name AS product_name "
        "FROM stock_adjustments a JOIN products p ON p.id=a.product_id ORDER BY a.date DESC, a.id DESC LIMIT 50"
    )
    return {"rows": compute_stock(), "adjustments": adj}


@router.post("/api/stock/adjust")
def stock_adjust(a: StockAdjust, user: dict = WRITE):
    """Inventaire : on saisit la quantité réellement présente, l'écart devient un ajustement."""
    p = db.one("SELECT * FROM products WHERE id=?", (a.product_id,))
    if not p:
        raise HTTPException(404)
    unit = a.unit or p["unit"] or "kg"
    current = next((r["stock"] for r in compute_stock() if r["product_id"] == a.product_id and r["unit"] == unit), 0.0)
    delta = round(a.target_qty - current, 3)
    if delta == 0:
        return {"delta": 0}
    db.execute(
        "INSERT INTO stock_adjustments (product_id, date, qty, unit, reason, username) VALUES (?,?,?,?,?,?)",
        (a.product_id, date_cls.today().isoformat(), delta, unit, a.reason, user["username"]),
    )
    return {"delta": delta}


@router.delete("/api/stock/adjustments/{id}")
def delete_adjustment(id: int, user: dict = WRITE):
    db.execute("DELETE FROM stock_adjustments WHERE id=?", (id,))
    return {"ok": True}
