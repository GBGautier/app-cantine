"""Routes pour les stocks (endpoint /api/stock).

Ce module fournit un endpoint pour récupérer les stocks actuels.
Différent de /api/stocks qui gère les ajustements.
"""

from fastapi import APIRouter, Depends

from src.backend.utils import READ
from src.backend.db import rows

router = APIRouter(prefix="/api/stock", tags=["Stocks"])


@router.get("/")
@router.get("")
async def get_stock(user: dict = Depends(READ)):
    """Retourne les stocks actuels."""
    # Cette route est appelée par le frontend pour afficher les stocks
    # On retourne les données au format attendu par le frontend
    result = rows(
        "SELECT p.id, p.name, p.category, p.supplier_id, "
        "COALESCE(SUM(CASE WHEN o.kind='livraison' THEN ol.qty ELSE 0 END), 0) - "
        "COALESCE(SUM(CASE WHEN o.kind='facture' THEN ol.qty ELSE 0 END), 0) + "
        "COALESCE(SUM(sa.qty), 0) AS stock, "
        "p.unit "
        "FROM products p "
        "LEFT JOIN order_lines ol ON ol.product_id = p.id "
        "LEFT JOIN orders o ON o.id = ol.order_id "
        "LEFT JOIN stock_adjustments sa ON sa.product_id = p.id "
        "GROUP BY p.id, p.name, p.category, p.supplier_id, p.unit"
    )
    
    # Formater le résultat comme attendu par le frontend
    return {
        "rows": [
            {
                "product_id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "supplier_id": r["supplier_id"],
                "stock": float(r["stock"] or 0),
                "unit": r["unit"] or "kg"
            }
            for r in result
        ]
    }
