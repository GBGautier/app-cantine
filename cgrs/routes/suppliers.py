"""Fournisseurs."""

import json
import re
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

import db
from cgrs.constants import DAYS
from cgrs.security import READ, WRITE
from cgrs.utils import insert, update


router = APIRouter()


class Supplier(BaseModel):
    name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    siret: Optional[str] = None
    delivery_days: list[str] = []
    franco: Optional[float] = None
    order_method: Optional[str] = None
    order_url: Optional[str] = None
    categories: list[str] = []
    local_default: Optional[str] = None
    direct_producteur: int = 0
    parser_regex: Optional[str] = None
    keywords: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("order_url")
    @classmethod
    def url_ok(cls, v):
        if v and not re.match(r"^https?://", v.strip(), re.I):
            raise ValueError("Le lien de commande doit commencer par http:// ou https://")
        return v.strip() if v else v

    @field_validator("delivery_days")
    @classmethod
    def days_ok(cls, v):
        return [d for d in v if d in DAYS]


def supplier_out(r):
    for k in ("delivery_days", "categories"):
        try:
            r[k] = json.loads(r[k]) if r.get(k) else []
        except ValueError:
            r[k] = []
    return r


@router.get("/api/suppliers")
def suppliers(user: dict = READ):
    out = [supplier_out(r) for r in db.rows(
        "SELECT s.*, (SELECT COUNT(*) FROM products p WHERE p.supplier_id=s.id) AS nb_products, "
        "(SELECT COUNT(*) FROM orders o WHERE o.supplier_id=s.id) AS nb_orders "
        "FROM suppliers s ORDER BY s.name")]
    if user["role"] != "admin":   # mots-clés de reconnaissance et regex de lecture : réservés à l'administrateur
        for r in out:
            r.pop("keywords", None)
            r.pop("parser_regex", None)
    return out


@router.post("/api/suppliers")
def create_supplier(s: Supplier, user: dict = WRITE):
    if user["role"] != "admin":
        s.keywords = s.parser_regex = None
    return {"id": insert("suppliers", s)}


@router.put("/api/suppliers/{id}")
def edit_supplier(id: int, s: Supplier, user: dict = WRITE):
    old = db.one("SELECT direct_producteur, keywords, parser_regex FROM suppliers WHERE id=?", (id,))
    if user["role"] != "admin" and old:   # ces deux champs ne sont pas modifiables hors administrateur
        s.keywords, s.parser_regex = old["keywords"], old["parser_regex"]
    update("suppliers", id, s)
    if s.direct_producteur and old and not old["direct_producteur"]:   # fournisseur désormais « direct producteur » : ses produits aussi
        db.execute("UPDATE products SET direct_producteur=1 WHERE supplier_id=?", (id,))
    return {"ok": True}


@router.delete("/api/suppliers/{id}")
def delete_supplier(id: int, user: dict = WRITE):
    db.execute("DELETE FROM suppliers WHERE id=?", (id,))
    return {"ok": True}
