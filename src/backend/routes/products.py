"""Routes pour la gestion des produits."""

from fastapi import APIRouter, Depends, HTTPException

from src.backend.models.products import ProductCreate, ProductEdit, ProductOut
from src.backend.utils import (
    EDIT,
    READ,
    log_action,
    now_iso,
)
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/products", tags=["Produits"])


@router.get("/", response_model=list[ProductOut])
async def list_products(
    supplier_id: int | None = None,
    category: str | None = None,
    search: str | None = None,
    user: dict = Depends(READ)
):
    """Liste tous les produits avec filtres."""
    where = []
    args = []
    if supplier_id is not None:
        where.append("p.supplier_id=?")
        args.append(supplier_id)
    if category is not None:
        where.append("p.category=?")
        args.append(category)
    if search is not None:
        where.append("(p.name LIKE ? OR p.ref LIKE ? OR p.label_detail LIKE ?)")
        search_pattern = f"%{search}%"
        args.extend([search_pattern, search_pattern, search_pattern])
    
    w = " AND ".join(where) if where else "1=1"
    return rows(
        f"SELECT p.*, s.name AS supplier_name FROM products p LEFT JOIN suppliers s ON s.id=p.supplier_id "
        f"WHERE {w} ORDER BY p.name"
    )


@router.get("/{id}", response_model=ProductOut)
async def get_product(id: int, user: dict = Depends(READ)):
    """Récupère un produit par son ID."""
    product = one(
        "SELECT p.*, s.name AS supplier_name FROM products p LEFT JOIN suppliers s ON s.id=p.supplier_id "
        "WHERE p.id=?",
        (id,)
    )
    if not product:
        raise HTTPException(404)
    return product


@router.post("/", response_model=dict)
async def create_product(product_data: ProductCreate, user: dict = Depends(EDIT)):
    """Crée un nouveau produit."""
    pid = execute(
        "INSERT INTO products (ref, name, supplier_id, category, gamme, label_egalim, label_detail, "
        "provenance, direct_producteur, commerce_equitable, avoid, favorite, unit, unit_price, "
        "datasheet, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            product_data.ref,
            product_data.name,
            product_data.supplier_id,
            product_data.category,
            product_data.gamme.value if product_data.gamme else None,
            product_data.label_egalim.value,
            product_data.label_detail,
            product_data.provenance.value if product_data.provenance else None,
            int(product_data.direct_producteur),
            int(product_data.commerce_equitable),
            int(product_data.avoid),
            int(product_data.favorite),
            product_data.unit,
            product_data.unit_price,
            product_data.datasheet,
            product_data.notes,
        )
    )
    log_action(user, "create", "product", pid, f"Création produit : {product_data.name!r}")
    return {"id": pid}


@router.put("/{id}", response_model=dict)
async def edit_product(
    id: int,
    product_data: ProductEdit,
    user: dict = Depends(EDIT)
):
    """Modifie un produit."""
    if not one("SELECT 1 AS x FROM products WHERE id=?", (id,)):
        raise HTTPException(404)
    
    # Construction dynamique de la requête UPDATE
    fields = []
    values = []
    if product_data.ref is not None:
        fields.append("ref=?")
        values.append(product_data.ref)
    if product_data.name is not None:
        fields.append("name=?")
        values.append(product_data.name)
    if product_data.supplier_id is not None:
        fields.append("supplier_id=?")
        values.append(product_data.supplier_id)
    if product_data.category is not None:
        fields.append("category=?")
        values.append(product_data.category)
    if product_data.gamme is not None:
        fields.append("gamme=?")
        values.append(product_data.gamme.value)
    if product_data.label_egalim is not None:
        fields.append("label_egalim=?")
        values.append(product_data.label_egalim.value)
    if product_data.label_detail is not None:
        fields.append("label_detail=?")
        values.append(product_data.label_detail)
    if product_data.provenance is not None:
        fields.append("provenance=?")
        values.append(product_data.provenance.value)
    if product_data.direct_producteur is not None:
        fields.append("direct_producteur=?")
        values.append(int(product_data.direct_producteur))
    if product_data.commerce_equitable is not None:
        fields.append("commerce_equitable=?")
        values.append(int(product_data.commerce_equitable))
    if product_data.avoid is not None:
        fields.append("avoid=?")
        values.append(int(product_data.avoid))
    if product_data.favorite is not None:
        fields.append("favorite=?")
        values.append(int(product_data.favorite))
    if product_data.unit is not None:
        fields.append("unit=?")
        values.append(product_data.unit)
    if product_data.unit_price is not None:
        fields.append("unit_price=?")
        values.append(product_data.unit_price)
    if product_data.datasheet is not None:
        fields.append("datasheet=?")
        values.append(product_data.datasheet)
    if product_data.notes is not None:
        fields.append("notes=?")
        values.append(product_data.notes)
    
    if fields:
        values.append(id)
        execute(f"UPDATE products SET {','.join(fields)} WHERE id=?", values)
        log_action(user, "update", "product", id, "Modification produit")
    
    return {"ok": True}


@router.delete("/{id}", response_model=dict)
async def delete_product(id: int, user: dict = Depends(EDIT)):
    """Supprime un produit."""
    product = one("SELECT name FROM products WHERE id=?", (id,))
    if not product:
        raise HTTPException(404)
    
    # Vérifier qu'il n'y a pas de lignes de commande ou de repas liés
    if one("SELECT 1 AS x FROM order_lines WHERE product_id=?", (id,)):
        raise HTTPException(400, "Ce produit a des lignes de commande associées, suppression impossible")
    if one("SELECT 1 AS x FROM meal_items WHERE product_id=?", (id,)):
        raise HTTPException(400, "Ce produit a des éléments de repas associés, suppression impossible")
    
    log_action(user, "delete", "product", id, f"Suppression produit : {product['name']!r}")
    execute("DELETE FROM products WHERE id=?", (id,))
    return {"ok": True}
