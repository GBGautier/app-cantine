"""Engagements (objectifs comparés aux valeurs réelles dans les statistiques)."""

import json
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from cgrs import db
from cgrs.security import ADMIN, READ
from cgrs.utils import insert, update


router = APIRouter()


# ---------- engagements du marché / PAR ----------
class Commitment(BaseModel):
    label: str
    metrics: list[str] = []  # liste d'indicateurs (nouveau)
    metric: str = ""  # conservé pour compat. lecture (écrasé par metrics à l'enregistrement)
    categories: list[str] = []  # liste de catégories (nouveau)
    category: Optional[str] = None  # conservé pour compat. lecture
    gammes: list[str] = []  # liste de gammes filtrées (optionnel)
    target: float
    mode: str = "min"
    level: str = "marche"  # marche | par
    notes: Optional[str] = None


def commitment_out(c):
    c = dict(c)
    for k in ("metrics", "categories", "gammes"):
        try:
            c[k] = json.loads(c[k]) if c.get(k) else []
        except (ValueError, TypeError):
            c[k] = []
    if not c["metrics"] and c.get("metric"):
        c["metrics"] = [c["metric"]]
    if not c["categories"] and c.get("category"):
        c["categories"] = [c["category"]]
    return c


@router.get("/api/commitments")
def commitments(user: dict = READ):
    return [commitment_out(r) for r in db.rows("SELECT * FROM commitments ORDER BY id")]


@router.post("/api/commitments")
def create_commitment(c: Commitment, user: dict = ADMIN):
    return {"id": insert("commitments", c)}


@router.put("/api/commitments/{id}")
def edit_commitment(id: int, c: Commitment, user: dict = ADMIN):
    update("commitments", id, c)
    return {"ok": True}


@router.delete("/api/commitments/{id}")
def delete_commitment(id: int, user: dict = ADMIN):
    db.execute("DELETE FROM commitments WHERE id=?", (id,))
    return {"ok": True}


def seed_commitments():
    if not db.one("SELECT 1 AS x FROM commitments LIMIT 1"):
        db.execute("INSERT INTO commitments (label, metric, target, mode) VALUES ('Produits bio', 'bio', 85, 'min')")
        db.execute(
            "INSERT INTO commitments (label, metric, target, mode) VALUES ('Produits EGalim', 'egalim', 90, 'min')"
        )
