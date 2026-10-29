"""Routes pour la gestion des commandes et réceptions."""

import json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.backend.models.orders import OrderCreate, OrderEdit, OrderOut
from src.backend.utils import (
    EDIT,
    READ,
    log_action,
    now_iso,
)
from src.backend.db import one, execute, rows
from src.backend.services.pdf_parser import parse_pdf
from src.backend.config import get_uploads_dir

router = APIRouter(prefix="/api/orders", tags=["Commandes et Réceptions"])


@router.get("/", response_model=list[OrderOut])
async def list_orders(
    supplier_id: int | None = None,
    kind: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user: dict = Depends(READ)
):
    """Liste toutes les commandes avec filtres."""
    where = []
    args = []
    if supplier_id is not None:
        where.append("o.supplier_id=?")
        args.append(supplier_id)
    if kind is not None:
        where.append("o.kind=?")
        args.append(kind)
    if date_from is not None:
        where.append("o.date >= ?")
        args.append(date_from)
    if date_to is not None:
        where.append("o.date <= ?")
        args.append(date_to)
    
    w = " AND ".join(where) if where else "1=1"
    return rows(
        f"SELECT o.*, s.name AS supplier_name FROM orders o LEFT JOIN suppliers s ON s.id=o.supplier_id "
        f"WHERE {w} ORDER BY o.date DESC, o.id DESC"
    )


@router.get("/{id}", response_model=OrderOut)
async def get_order(id: int, user: dict = Depends(READ)):
    """Récupère une commande par son ID."""
    order = one(
        "SELECT o.*, s.name AS supplier_name FROM orders o LEFT JOIN suppliers s ON s.id=o.supplier_id "
        "WHERE o.id=?",
        (id,)
    )
    if not order:
        raise HTTPException(404)
    
    order["lines"] = rows(
        "SELECT l.*, p.name AS product_name, p.unit AS product_unit FROM order_lines l "
        "LEFT JOIN products p ON p.id=l.product_id WHERE l.order_id=? ORDER BY l.id",
        (id,)
    )
    return order


@router.post("/parse-pdf")
async def parse_order_pdf(
    file: UploadFile = File(...),
    user: dict = Depends(EDIT)
):
    """Parse un PDF de commande/réception."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Fichier PDF attendu")
    
    # Sauvegarder le fichier temporairement
    uploads_dir = get_uploads_dir()
    import secrets
    from pathlib import Path
    name = f"{secrets.token_hex(6)}_{file.filename}"
    dest = uploads_dir / name
    
    size = 0
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 25 * 1024 * 1024:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "Fichier trop volumineux (25 Mo maximum)")
            f.write(chunk)
    
    # Parser le PDF
    suppliers = rows("SELECT * FROM suppliers")
    products = rows("SELECT * FROM products")
    client_names = []
    
    try:
        docs = parse_pdf(str(dest), suppliers, products, client_names)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, f"Lecture du PDF impossible : {e}")
    
    # Nettoyer le fichier temporaire
    dest.unlink(missing_ok=True)
    
    return {"documents": docs, "source_file": name}


@router.post("/", response_model=dict)
async def create_order(order_data: OrderCreate, user: dict = Depends(EDIT)):
    """Crée une nouvelle commande."""
    oid = execute(
        "INSERT INTO orders (supplier_id, ref, kind, date, delivery_date, total_ht, source_file, notes) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            order_data.supplier_id,
            order_data.ref,
            order_data.kind.value,
            order_data.date,
            order_data.delivery_date,
            order_data.total_ht,
            order_data.source_file,
            order_data.notes,
        )
    )
    
    # Insérer les lignes
    for line in order_data.lines:
        execute(
            "INSERT INTO order_lines (order_id, product_id, ref, label, qty, unit, unit_price, total_ht) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                oid,
                line.product_id,
                line.ref,
                line.label,
                line.qty,
                line.unit,
                line.unit_price,
                line.total_ht,
            )
        )
        
        # Mettre à jour le prix du produit
        if line.product_id and line.unit_price:
            execute(
                "UPDATE products SET unit_price=? WHERE id=?",
                (line.unit_price, line.product_id)
            )
        
        # Enregistrer dans l'historique des prix
        if line.product_id and line.unit_price and line.qty:
            execute(
                "INSERT INTO price_history (product_id, date, price, unit, order_id, source) "
                "VALUES (?,?,?,?,?,?)",
                (
                    line.product_id,
                    order_data.date or order_data.delivery_date,
                    line.unit_price,
                    line.unit,
                    oid,
                    "reception"
                )
            )
    
    log_action(user, "create", "order", oid, f"Création commande : {order_data.ref or 'sans ref'}")
    return {"id": oid}


@router.put("/{id}", response_model=dict)
async def edit_order(
    id: int,
    order_data: OrderEdit,
    user: dict = Depends(EDIT)
):
    """Modifie une commande."""
    if not one("SELECT 1 AS x FROM orders WHERE id=?", (id,)):
        raise HTTPException(404)
    
    # Mettre à jour la commande
    fields = []
    values = []
    if order_data.supplier_id is not None:
        fields.append("supplier_id=?")
        values.append(order_data.supplier_id)
    if order_data.ref is not None:
        fields.append("ref=?")
        values.append(order_data.ref)
    if order_data.kind is not None:
        fields.append("kind=?")
        values.append(order_data.kind.value)
    if order_data.date is not None:
        fields.append("date=?")
        values.append(order_data.date)
    if order_data.delivery_date is not None:
        fields.append("delivery_date=?")
        values.append(order_data.delivery_date)
    if order_data.total_ht is not None:
        fields.append("total_ht=?")
        values.append(order_data.total_ht)
    if order_data.source_file is not None:
        fields.append("source_file=?")
        values.append(order_data.source_file)
    if order_data.notes is not None:
        fields.append("notes=?")
        values.append(order_data.notes)
    
    if fields:
        values.append(id)
        execute(f"UPDATE orders SET {','.join(fields)} WHERE id=?", values)
    
    # Mettre à jour les lignes si fournies
    if order_data.lines is not None:
        # Supprimer les anciennes lignes
        execute("DELETE FROM order_lines WHERE order_id=?", (id,))
        
        # Insérer les nouvelles lignes
        for line in order_data.lines:
            lid = execute(
                "INSERT INTO order_lines (order_id, product_id, ref, label, qty, unit, unit_price, total_ht) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    id,
                    line.product_id,
                    line.ref,
                    line.label,
                    line.qty,
                    line.unit,
                    line.unit_price,
                    line.total_ht,
                )
            )
            
            # Mettre à jour le prix du produit
            if line.product_id and line.unit_price:
                execute(
                    "UPDATE products SET unit_price=? WHERE id=?",
                    (line.unit_price, line.product_id)
                )
    
    log_action(user, "update", "order", id, "Modification commande")
    return {"ok": True}


@router.delete("/{id}", response_model=dict)
async def delete_order(id: int, user: dict = Depends(EDIT)):
    """Supprime une commande."""
    order = one("SELECT ref FROM orders WHERE id=?", (id,))
    if not order:
        raise HTTPException(404)
    
    log_action(user, "delete", "order", id, f"Suppression commande : {order['ref']!r}")
    execute("DELETE FROM orders WHERE id=?", (id,))
    return {"ok": True}
