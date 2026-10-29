"""Routes pour la gestion des recettes."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from src.backend.models.recipes import RecipeCreate, RecipeEdit, RecipeOut
from src.backend.utils import (
    EDIT,
    READ,
    log_action,
    now_iso,
    convert,
    price_at,
    load_history,
)
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/recipes", tags=["Recettes"])


def recipe_out(r, with_items=False):
    """Formate une recette pour la sortie."""
    r = dict(r)
    if with_items:
        items = rows(
            "SELECT ri.*, p.name AS product_name, p.unit AS product_unit, p.unit_price "
            "FROM recipe_items ri LEFT JOIN products p ON p.id=ri.product_id "
            "WHERE ri.recipe_id=? ORDER BY ri.id",
            (r["id"],)
        )
        r["items"] = [dict(i) for i in items]
    return r


def recipe_cost(recipe_id, nb_mat, nb_elem, nb_adu, meal_date=None):
    """Estime le coût d'une recette selon les effectifs donnés."""
    items = rows(
        "SELECT ri.*, p.unit AS product_unit, p.unit_price FROM recipe_items ri "
        "LEFT JOIN products p ON p.id=ri.product_id WHERE ri.recipe_id=?",
        (recipe_id,)
    )
    if not items:
        return None
    hist = load_history()
    total = 0.0
    unpriced = 0
    for it in items:
        if not it["product_id"]:
            continue
        price = price_at(hist, it["product_id"], meal_date or date.today().isoformat(), it["unit_price"])
        if price is None:
            unpriced += 1
            continue
        qty = (
            (it["qty_maternelle"] or 0) * nb_mat / 1000 +
            (it["qty_elementaire"] or 0) * nb_elem / 1000 +
            (it["qty_adulte"] or 0) * nb_adu / 1000
        )
        total += qty * price
    return {"cost": round(total, 2), "unpriced": unpriced}


def save_recipe_items(recipe_id, items):
    """Sauvegarde les éléments d'une recette."""
    execute("DELETE FROM recipe_items WHERE recipe_id=?", (recipe_id,))
    for it in items:
        execute(
            "INSERT INTO recipe_items (recipe_id, product_id, label, qty_maternelle, qty_elementaire, qty_adulte, "
            "qty_servi, qty_commander, unit, principal, intitule_gemrcn) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                recipe_id,
                it.product_id,
                it.label,
                it.qty_maternelle,
                it.qty_elementaire,
                it.qty_adulte,
                it.qty_servi,
                it.qty_commander,
                it.unit,
                1 if it.principal else 0,
                it.intitule_gemrcn
            )
        )


@router.get("/", response_model=list[RecipeOut])
async def list_recipes(user: dict = Depends(READ)):
    """Liste toutes les recettes."""
    rows_ = rows("SELECT * FROM recipes ORDER BY name")
    return [recipe_out(r) for r in rows_]


@router.get("/{id}", response_model=RecipeOut)
async def get_recipe(id: int, user: dict = Depends(READ)):
    """Récupère une recette par son ID."""
    r = one("SELECT * FROM recipes WHERE id=?", (id,))
    if not r:
        raise HTTPException(404)
    out = recipe_out(r, with_items=True)
    out["served"] = rows(
        "SELECT date, statut, guests, plat, entree FROM meals "
        "WHERE recipe_entree=? OR recipe_plat=? OR recipe_accompagnement=? OR recipe_laitage=? OR recipe_dessert=? "
        "ORDER BY date DESC, id DESC",
        (id, id, id, id, id)
    )
    return out


@router.post("/", response_model=dict)
async def create_recipe(recipe_data: RecipeCreate, user: dict = Depends(EDIT)):
    """Crée une nouvelle recette."""
    rid = execute(
        "INSERT INTO recipes (name, categorie, description, nb_maternelles, nb_elementaires, nb_adultes, created) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            recipe_data.name,
            recipe_data.categorie,
            recipe_data.description,
            recipe_data.nb_maternelles,
            recipe_data.nb_elementaires,
            recipe_data.nb_adultes,
            now_iso()
        )
    )
    save_recipe_items(rid, recipe_data.items)
    log_action(user, "create", "recipe", rid, f"Recette créée : {recipe_data.name!r}")
    return {"id": rid}


@router.put("/{id}", response_model=dict)
async def edit_recipe(
    id: int,
    recipe_data: RecipeEdit,
    user: dict = Depends(EDIT)
):
    """Modifie une recette."""
    if not one("SELECT 1 AS x FROM recipes WHERE id=?", (id,)):
        raise HTTPException(404)
    execute(
        "UPDATE recipes SET name=?, categorie=?, description=?, nb_maternelles=?, nb_elementaires=?, nb_adultes=? "
        "WHERE id=?",
        (
            recipe_data.name,
            recipe_data.categorie,
            recipe_data.description,
            recipe_data.nb_maternelles,
            recipe_data.nb_elementaires,
            recipe_data.nb_adultes,
            id
        )
    )
    save_recipe_items(id, recipe_data.items)
    log_action(user, "update", "recipe", id, f"Recette modifiée : {recipe_data.name!r}")
    return {"ok": True}


@router.delete("/{id}", response_model=dict)
async def delete_recipe(id: int, user: dict = Depends(EDIT)):
    """Supprime une recette."""
    r = one("SELECT name FROM recipes WHERE id=?", (id,))
    if not r:
        raise HTTPException(404)
    execute("DELETE FROM recipes WHERE id=?", (id,))
    log_action(user, "delete", "recipe", id, f"Recette supprimée : {r['name']!r}")
    return {"ok": True}


@router.get("/{id}/cost")
async def get_recipe_cost(
    id: int,
    nb_maternelles: int = 0,
    nb_elementaires: int = 0,
    nb_adultes: int = 0,
    meal_date: Optional[str] = None,
    user: dict = Depends(READ)
):
    """Estime le coût d'une recette."""
    if not one("SELECT 1 AS x FROM recipes WHERE id=?", (id,)):
        raise HTTPException(404)
    return recipe_cost(id, nb_maternelles, nb_elementaires, nb_adultes, meal_date) or {"cost": 0, "unpriced": 0}
