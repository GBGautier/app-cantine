"""Routes pour l'export des données."""

from fastapi import APIRouter, Depends

from src.backend.services.dolibarr import (
    products_csv,
    suppliers_csv,
    orders_csv,
    meals_csv,
)
from src.backend.utils import READ
from src.backend.db import rows

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("/dolibarr/suppliers")
async def export_dolibarr_suppliers(user: dict = Depends(READ)):
    """Exporte les fournisseurs au format CSV pour Dolibarr."""
    return suppliers_csv(rows)


@router.get("/dolibarr/products")
async def export_dolibarr_products(user: dict = Depends(READ)):
    """Exporte les produits au format CSV pour Dolibarr."""
    return products_csv(rows)


@router.get("/dolibarr/orders")
async def export_dolibarr_orders(user: dict = Depends(READ)):
    """Exporte les commandes au format CSV pour Dolibarr."""
    return orders_csv(rows)


@router.get("/dolibarr/meals")
async def export_dolibarr_meals(user: dict = Depends(READ)):
    """Exporte les repas au format CSV pour Dolibarr."""
    return meals_csv(rows)
