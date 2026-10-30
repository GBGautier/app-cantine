"""Exports CSV pour Dolibarr."""

from fastapi import APIRouter

import db
import dolibarr
from cgrs.security import READ


router = APIRouter()


# ---------- Export Dolibarr (CSV pour l'assistant d'import) ----------
@router.get("/api/export/dolibarr/suppliers")
def export_dolibarr_suppliers(user: dict = READ):
    return dolibarr.suppliers_csv(db)


@router.get("/api/export/dolibarr/products")
def export_dolibarr_products(user: dict = READ):
    return dolibarr.products_csv(db)


@router.get("/api/export/dolibarr/orders")
def export_dolibarr_orders(user: dict = READ):
    return dolibarr.orders_csv(db)


@router.get("/api/export/dolibarr/meals")
def export_dolibarr_meals(user: dict = READ):
    return dolibarr.meals_csv(db)
