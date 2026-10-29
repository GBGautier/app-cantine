"""Routes pour les statistiques.

Ce module fournit les endpoints pour générer des statistiques.
"""

from fastapi import APIRouter, Depends, Request

from src.backend.utils import READ
from src.backend.db import rows

router = APIRouter(prefix="/api/stats", tags=["Statistiques"])


@router.get("/")
@router.get("")
async def get_stats(request: Request, user: dict = Depends(READ)):
    """Retourne des statistiques globales."""
    # Récupérer les paramètres de la requête
    query_params = dict(request.query_params)
    
    # Par défaut, retourner des statistiques de base
    # (À compléter selon les besoins réels de l'application)
    return {
        "total_orders": len(rows("SELECT id FROM orders")),
        "total_products": len(rows("SELECT id FROM products")),
        "total_suppliers": len(rows("SELECT id FROM suppliers")),
    }
