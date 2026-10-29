"""Routes pour la gestion des fournisseurs."""

from fastapi import APIRouter, Depends, HTTPException

from src.backend.models.suppliers import SupplierCreate, SupplierEdit, SupplierOut
from src.backend.utils import (
    EDIT,
    READ,
    log_action,
    now_iso,
)
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/suppliers", tags=["Fournisseurs"])


@router.get("/", response_model=list[SupplierOut])
async def list_suppliers(user: dict = Depends(READ)):
    """Liste tous les fournisseurs."""
    return rows(
        "SELECT s.*, COUNT(p.id) AS product_count FROM suppliers s LEFT JOIN products p ON p.supplier_id=s.id "
        "GROUP BY s.id ORDER BY s.name"
    )


@router.get("/{id}", response_model=SupplierOut)
async def get_supplier(id: int, user: dict = Depends(READ)):
    """Récupère un fournisseur par son ID."""
    supplier = one("SELECT * FROM suppliers WHERE id=?", (id,))
    if not supplier:
        raise HTTPException(404)
    return supplier


@router.post("/", response_model=dict)
async def create_supplier(supplier_data: SupplierCreate, user: dict = Depends(EDIT)):
    """Crée un nouveau fournisseur."""
    sid = execute(
        "INSERT INTO suppliers (name, contact, email, phone, address, siret, delivery_days, "
        "franco, order_method, order_url, categories, local_default, direct_producteur, "
        "parser_regex, keywords, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            supplier_data.name,
            supplier_data.contact,
            supplier_data.email,
            supplier_data.phone,
            supplier_data.address,
            supplier_data.siret,
            supplier_data.delivery_days,
            supplier_data.franco,
            supplier_data.order_method,
            supplier_data.order_url,
            supplier_data.categories,
            supplier_data.local_default,
            int(supplier_data.direct_producteur),
            supplier_data.parser_regex,
            supplier_data.keywords,
            supplier_data.notes,
        )
    )
    log_action(user, "create", "supplier", sid, f"Création fournisseur : {supplier_data.name!r}")
    return {"id": sid}


@router.put("/{id}", response_model=dict)
async def edit_supplier(
    id: int,
    supplier_data: SupplierEdit,
    user: dict = Depends(EDIT)
):
    """Modifie un fournisseur."""
    if not one("SELECT 1 AS x FROM suppliers WHERE id=?", (id,)):
        raise HTTPException(404)
    
    # Construction dynamique de la requête UPDATE
    fields = []
    values = []
    if supplier_data.name is not None:
        fields.append("name=?")
        values.append(supplier_data.name)
    if supplier_data.contact is not None:
        fields.append("contact=?")
        values.append(supplier_data.contact)
    if supplier_data.email is not None:
        fields.append("email=?")
        values.append(supplier_data.email)
    if supplier_data.phone is not None:
        fields.append("phone=?")
        values.append(supplier_data.phone)
    if supplier_data.address is not None:
        fields.append("address=?")
        values.append(supplier_data.address)
    if supplier_data.siret is not None:
        fields.append("siret=?")
        values.append(supplier_data.siret)
    if supplier_data.delivery_days is not None:
        fields.append("delivery_days=?")
        values.append(supplier_data.delivery_days)
    if supplier_data.franco is not None:
        fields.append("franco=?")
        values.append(supplier_data.franco)
    if supplier_data.order_method is not None:
        fields.append("order_method=?")
        values.append(supplier_data.order_method)
    if supplier_data.order_url is not None:
        fields.append("order_url=?")
        values.append(supplier_data.order_url)
    if supplier_data.categories is not None:
        fields.append("categories=?")
        values.append(supplier_data.categories)
    if supplier_data.local_default is not None:
        fields.append("local_default=?")
        values.append(supplier_data.local_default)
    if supplier_data.direct_producteur is not None:
        fields.append("direct_producteur=?")
        values.append(int(supplier_data.direct_producteur))
    if supplier_data.parser_regex is not None:
        fields.append("parser_regex=?")
        values.append(supplier_data.parser_regex)
    if supplier_data.keywords is not None:
        fields.append("keywords=?")
        values.append(supplier_data.keywords)
    if supplier_data.notes is not None:
        fields.append("notes=?")
        values.append(supplier_data.notes)
    
    if fields:
        values.append(id)
        execute(f"UPDATE suppliers SET {','.join(fields)} WHERE id=?", values)
        log_action(user, "update", "supplier", id, "Modification fournisseur")
    
    return {"ok": True}


@router.delete("/{id}", response_model=dict)
async def delete_supplier(id: int, user: dict = Depends(EDIT)):
    """Supprime un fournisseur."""
    supplier = one("SELECT name FROM suppliers WHERE id=?", (id,))
    if not supplier:
        raise HTTPException(404)
    
    # Vérifier qu'il n'y a pas de produits liés
    if one("SELECT 1 AS x FROM products WHERE supplier_id=?", (id,)):
        raise HTTPException(400, "Ce fournisseur a des produits associés, suppression impossible")
    
    log_action(user, "delete", "supplier", id, f"Suppression fournisseur : {supplier['name']!r}")
    execute("DELETE FROM suppliers WHERE id=?", (id,))
    return {"ok": True}
