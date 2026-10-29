"""Routes pour la gestion des stocks."""

from fastapi import APIRouter, Depends, HTTPException

from src.backend.models.stocks import StockAdjustmentCreate, StockAdjustmentEdit, StockOut
from src.backend.utils import (
    EDIT,
    READ,
    log_action,
    convert,
)
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])


def compute_stock():
    """Calcule les stocks actuels."""
    prods = {p["id"]: p for p in rows(
        "SELECT p.*, s.name AS supplier_name FROM products p LEFT JOIN suppliers s ON s.id=p.supplier_id")}
    acc = {}

    def add(pid, field, qty, unit):
        p = prods.get(pid)
        if not p or qty is None:
            return
        pu = p["unit"] or "kg"
        q, u = convert(qty, unit or pu, pu), pu
        if q is None:
            q, u = qty, unit
        r = acc.setdefault((pid, u), {"in": 0.0, "out": 0.0, "adj": 0.0})
        r[field] += q

    for l in rows("SELECT product_id, qty, unit FROM order_lines WHERE product_id IS NOT NULL"):
        add(l["product_id"], "in", l["qty"], l["unit"])
    for i in rows("SELECT product_id, qty, unit FROM meal_items"):
        add(i["product_id"], "out", i["qty"], i["unit"])
    for a in rows("SELECT product_id, qty, unit FROM stock_adjustments"):
        add(a["product_id"], "adj", a["qty"], a["unit"])
    
    rows_ = []
    for (pid, unit), r in acc.items():
        p = prods[pid]
        stock = round(r["in"] - r["out"] + r["adj"], 3)
        value = round(stock * p["unit_price"], 2) if p["unit_price"] is not None and unit == (p["unit"] or "kg") else None
        rows_.append({
            "product_id": pid,
            "ref": p["ref"],
            "name": p["name"],
            "category": p["category"],
            "unit": unit,
            "stock": stock,
            "value": value,
            "in_qty": round(r["in"], 3),
            "out_qty": round(r["out"], 3),
            "adj_qty": round(r["adj"], 3),
        })
    return rows_


@router.get("/", response_model=list[StockOut])
async def get_stocks(user: dict = Depends(READ)):
    """Récupère les stocks actuels."""
    return compute_stock()


@router.get("/adjustments")
async def list_adjustments(user: dict = Depends(READ)):
    """Liste tous les ajustements de stock."""
    return rows(
        "SELECT sa.*, p.name AS product_name, p.unit AS product_unit "
        "FROM stock_adjustments sa JOIN products p ON p.id=sa.product_id "
        "ORDER BY sa.date DESC, sa.id DESC"
    )


@router.post("/adjustments", response_model=dict)
async def create_adjustment(
    adjustment_data: StockAdjustmentCreate,
    user: dict = Depends(EDIT)
):
    """Crée un nouvel ajustement de stock."""
    aid = execute(
        "INSERT INTO stock_adjustments (product_id, date, qty, unit, reason, username) VALUES (?,?,?,?,?,?)",
        (
            adjustment_data.product_id,
            adjustment_data.date,
            adjustment_data.qty,
            adjustment_data.unit,
            adjustment_data.reason,
            user["username"]
        )
    )
    log_action(
        user,
        "create",
        "stock_adjustment",
        aid,
        f"Ajustement stock : {adjustment_data.qty} {adjustment_data.unit}"
    )
    return {"id": aid}


@router.put("/adjustments/{id}", response_model=dict)
async def edit_adjustment(
    id: int,
    adjustment_data: StockAdjustmentEdit,
    user: dict = Depends(EDIT)
):
    """Modifie un ajustement de stock."""
    if not one("SELECT 1 AS x FROM stock_adjustments WHERE id=?", (id,)):
        raise HTTPException(404)
    
    fields = []
    values = []
    if adjustment_data.date is not None:
        fields.append("date=?")
        values.append(adjustment_data.date)
    if adjustment_data.qty is not None:
        fields.append("qty=?")
        values.append(adjustment_data.qty)
    if adjustment_data.unit is not None:
        fields.append("unit=?")
        values.append(adjustment_data.unit)
    if adjustment_data.reason is not None:
        fields.append("reason=?")
        values.append(adjustment_data.reason)
    
    if fields:
        values.append(id)
        execute(f"UPDATE stock_adjustments SET {','.join(fields)} WHERE id=?", values)
        log_action(user, "update", "stock_adjustment", id, "Modification ajustement stock")
    
    return {"ok": True}


@router.delete("/adjustments/{id}", response_model=dict)
async def delete_adjustment(id: int, user: dict = Depends(EDIT)):
    """Supprime un ajustement de stock."""
    if not one("SELECT 1 AS x FROM stock_adjustments WHERE id=?", (id,)):
        raise HTTPException(404)
    log_action(user, "delete", "stock_adjustment", id, "Suppression ajustement stock")
    execute("DELETE FROM stock_adjustments WHERE id=?", (id,))
    return {"ok": True}
