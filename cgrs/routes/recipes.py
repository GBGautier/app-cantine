"""Recettes."""

from datetime import date as date_cls
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import db
from cgrs.pricing import load_history, price_at
from cgrs.security import READ, WRITE
from cgrs.utils import log_action, now_iso


router = APIRouter()


class RecipeItem(BaseModel):
    product_id: Optional[int] = None
    label: Optional[str] = None
    qty_maternelle: Optional[float] = None
    qty_elementaire: Optional[float] = None
    qty_adulte: Optional[float] = None
    qty_servi: Optional[float] = None
    qty_commander: Optional[float] = None
    unit: Optional[str] = None
    principal: bool = False
    intitule_gemrcn: Optional[str] = None


class Recipe(BaseModel):
    name: str
    categorie: Optional[str] = None   # entree | plat | accompagnement | laitage | dessert
    description: Optional[str] = None
    nb_maternelles: int = 0
    nb_elementaires: int = 0
    nb_adultes: int = 0
    items: list[RecipeItem] = []


def recipe_out(r, with_items=False):
    r = dict(r)
    if with_items:
        items = db.rows(
            "SELECT ri.*, p.name AS product_name, p.unit AS product_unit, p.unit_price "
            "FROM recipe_items ri LEFT JOIN products p ON p.id=ri.product_id "
            "WHERE ri.recipe_id=? ORDER BY ri.id", (r["id"],))
        r["items"] = [dict(i) for i in items]
    return r


def recipe_cost(recipe_id, nb_mat, nb_elem, nb_adu, meal_date=None):
    """Estime le coût d'une recette selon les effectifs donnés."""
    items = db.rows(
        "SELECT ri.*, p.unit AS product_unit, p.unit_price FROM recipe_items ri "
        "LEFT JOIN products p ON p.id=ri.product_id WHERE ri.recipe_id=?", (recipe_id,))
    if not items:
        return None
    hist = load_history()
    total = 0.0
    unpriced = 0
    for it in items:
        if not it["product_id"]:
            continue
        price = price_at(hist, it["product_id"], meal_date or date_cls.today().isoformat(), it["unit_price"])
        if price is None:
            unpriced += 1
            continue
        qty = (
            (it["qty_maternelle"] or 0) * nb_mat / 1000 +
            (it["qty_elementaire"] or 0) * nb_elem / 1000 +
            (it["qty_adulte"] or 0) * nb_adu / 1000
        )   # grammages en g → kg pour un prix en €/kg
        total += qty * price
    return {"cost": round(total, 2), "unpriced": unpriced}


@router.get("/api/recipes")
def list_recipes(user: dict = READ):
    rows = db.rows("SELECT * FROM recipes ORDER BY name")
    return [recipe_out(r) for r in rows]


@router.get("/api/recipes/{id}")
def get_recipe(id: int, user: dict = READ):
    r = db.one("SELECT * FROM recipes WHERE id=?", (id,))
    if not r:
        raise HTTPException(404)
    out = recipe_out(r, with_items=True)
    # dates où cette recette a été servie (repas liés, toutes catégories confondues)
    out["served"] = db.rows(
        "SELECT date, statut, guests, plat, entree FROM meals "
        "WHERE recipe_entree=? OR recipe_plat=? OR recipe_accompagnement=? OR recipe_laitage=? OR recipe_dessert=? "
        "ORDER BY date DESC, id DESC", (id, id, id, id, id))
    return out


def save_recipe_items(recipe_id, items: list[RecipeItem]):
    db.execute("DELETE FROM recipe_items WHERE recipe_id=?", (recipe_id,))
    for it in items:
        db.execute(
            "INSERT INTO recipe_items (recipe_id, product_id, label, qty_maternelle, qty_elementaire, qty_adulte, "
            "qty_servi, qty_commander, unit, principal, intitule_gemrcn) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (recipe_id, it.product_id, it.label, it.qty_maternelle, it.qty_elementaire, it.qty_adulte,
             it.qty_servi, it.qty_commander, it.unit, 1 if it.principal else 0, it.intitule_gemrcn))


@router.post("/api/recipes")
@db.atomic
def create_recipe(r: Recipe, user: dict = WRITE):
    rid = db.execute(
        "INSERT INTO recipes (name, categorie, description, nb_maternelles, nb_elementaires, nb_adultes, created) "
        "VALUES (?,?,?,?,?,?,?)",
        (r.name, r.categorie, r.description, r.nb_maternelles, r.nb_elementaires, r.nb_adultes, now_iso()))
    save_recipe_items(rid, r.items)
    log_action(user, "create", "recipe", rid, f"Recette créée : {r.name!r}")
    return {"id": rid}


@router.put("/api/recipes/{id}")
@db.atomic
def edit_recipe(id: int, r: Recipe, user: dict = WRITE):
    if not db.one("SELECT 1 AS x FROM recipes WHERE id=?", (id,)):
        raise HTTPException(404)
    db.execute(
        "UPDATE recipes SET name=?, categorie=?, description=?, nb_maternelles=?, nb_elementaires=?, nb_adultes=? "
        "WHERE id=?",
        (r.name, r.categorie, r.description, r.nb_maternelles, r.nb_elementaires, r.nb_adultes, id))
    save_recipe_items(id, r.items)
    log_action(user, "update", "recipe", id, f"Recette modifiée : {r.name!r}")
    return {"ok": True}


@router.delete("/api/recipes/{id}")
def delete_recipe(id: int, user: dict = WRITE):
    r = db.one("SELECT name FROM recipes WHERE id=?", (id,))
    if not r:
        raise HTTPException(404)
    db.execute("DELETE FROM recipes WHERE id=?", (id,))
    log_action(user, "delete", "recipe", id, f"Recette supprimée : {r['name']!r}")
    return {"ok": True}


@router.get("/api/recipes/{id}/cost")
def recipe_cost_estimate(id: int, nb_maternelles: int = 0, nb_elementaires: int = 0,
                         nb_adultes: int = 0, meal_date: Optional[str] = None, user: dict = READ):
    if not db.one("SELECT 1 AS x FROM recipes WHERE id=?", (id,)):
        raise HTTPException(404)
    return recipe_cost(id, nb_maternelles, nb_elementaires, nb_adultes, meal_date) or {"cost": 0, "unpriced": 0}
