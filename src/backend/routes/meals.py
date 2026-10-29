"""Routes pour la gestion des repas."""

import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from src.backend.models.meals import MealCreate, MealEdit, MealOut, ShoppingListItem
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
from src.backend.services.menu_parser import parse_menu_pdf
from src.backend.config import get_uploads_dir

router = APIRouter(prefix="/api/meals", tags=["Repas"])


def meals_metrics(date_from=None, date_to=None, product_id=None):
    """Calcule les métriques pour les repas."""
    where, args = ["1=1"], []
    if date_from:
        where.append("m.date >= ?")
        args.append(date_from)
    if date_to:
        where.append("m.date <= ?")
        args.append(date_to)
    if product_id:
        where.append("m.id IN (SELECT meal_id FROM meal_items WHERE product_id=?)")
        args.append(product_id)
    w = " AND ".join(where)
    meals = rows(f"SELECT m.* FROM meals m WHERE {w} ORDER BY m.date DESC, m.id DESC", args)
    items = rows(
        "SELECT i.meal_id, i.product_id, i.qty, i.unit, i.prix_reel, m.date AS mdate, p.unit AS punit, p.unit_price, "
        "p.label_egalim, p.provenance FROM meal_items i JOIN meals m ON m.id=i.meal_id "
        f"JOIN products p ON p.id=i.product_id WHERE {w}", args)
    hist = load_history()
    acc = {m["id"]: {"cost": 0.0, "bio": 0.0, "local": 0.0, "n": 0, "unpriced": 0} for m in meals}
    for it in items:
        a = acc[it["meal_id"]]
        a["n"] += 1
        if it["prix_reel"] is not None:
            price = it["prix_reel"]
        else:
            price = price_at(hist, it["product_id"], it["mdate"], it["unit_price"])
        qty = convert(it["qty"], it["unit"] or it["punit"], it["punit"] or it["unit"])
        if price is None or qty is None:
            a["unpriced"] += 1
            continue
        c = qty * price
        a["cost"] += c
        if it["label_egalim"] == "bio":
            a["bio"] += c
        if it["provenance"] in ["cc_nozay", "loire_atlantique", "pays_loire"]:
            a["local"] += c
    out = []
    for m in meals:
        a = acc[m["id"]]
        cost = round(a["cost"], 2)
        out.append({
            "id": m["id"], "date": m["date"], "nb_maternelles": m["nb_maternelles"] or 0,
            "nb_elementaires": m["nb_elementaires"] or 0, "nb_adultes": m["nb_adultes"] or 0,
            "guests": m["guests"], "notes": m["notes"],
            "entree": m["entree"], "plat": m["plat"], "accompagnement": m["accompagnement"],
            "laitage": m["laitage"], "dessert": m["dessert"],
            "commentaire_post": m["commentaire_post"], "statut": m["statut"] or "prevu",
            "modif_prevu": bool(m["modif_prevu"]),
            "nb_items": a["n"], "unpriced": a["unpriced"],
            "cost": cost,
            "per_guest": round(cost / m["guests"], 2) if cost and m["guests"] else None,
            "pct_bio": round(100 * a["bio"] / a["cost"], 1) if a["cost"] else None,
            "pct_local": round(100 * a["local"] / a["cost"], 1) if a["cost"] else None,
        })
    return out


@router.get("/", response_model=list[MealOut])
async def list_meals(
    date_from: str | None = None,
    date_to: str | None = None,
    product_id: int | None = None,
    user: dict = Depends(READ)
):
    """Liste tous les repas avec filtres."""
    return meals_metrics(date_from=date_from, date_to=date_to, product_id=product_id)


@router.get("/shopping-list")
async def get_shopping_list(
    date_from: str,
    date_to: str,
    user: dict = Depends(READ)
):
    """Génère une liste de courses pour une période."""
    rows_ = rows(
        "SELECT i.product_id, i.qty, i.unit, p.name, p.category, p.unit AS punit "
        "FROM meal_items i JOIN meals m ON m.id=i.meal_id JOIN products p ON p.id=i.product_id "
        "WHERE m.date >= ? AND m.date <= ?",
        (date_from, date_to)
    )
    acc = {}
    for r in rows_:
        pu = r["punit"] or r["unit"] or "kg"
        q = convert(r["qty"], r["unit"] or pu, pu)
        u = pu
        if q is None:
            q, u = r["qty"], r["unit"] or pu
        a = acc.setdefault((r["product_id"], u), {
            "product_id": r["product_id"],
            "label": r["name"],
            "category": r["category"] or "Autre",
            "unit": u,
            "qty": 0.0
        })
        a["qty"] += q
    
    from src.backend.utils import CATEGORIES
    out = sorted(
        acc.values(),
        key=lambda a: (
            CATEGORIES.index(a["category"]) if a["category"] in CATEGORIES else len(CATEGORIES),
            a["category"].lower(),
            a["label"].lower()
        )
    )
    for a in out:
        a["qty"] = round(a["qty"], 3)
    return out


@router.get("/{id}", response_model=MealOut)
async def get_meal(id: int, user: dict = Depends(READ)):
    """Récupère un repas par son ID."""
    m = one("SELECT * FROM meals WHERE id=?", (id,))
    if not m:
        raise HTTPException(404)
    m["items"] = rows(
        "SELECT i.*, p.name AS product_name, p.unit_price AS unit_price FROM meal_items i "
        "JOIN products p ON p.id=i.product_id WHERE i.meal_id=? ORDER BY i.id",
        (id,)
    )
    try:
        m["estimation"] = json.loads(m["estimation"]) if m.get("estimation") else []
    except (ValueError, TypeError):
        m["estimation"] = []
    return m


def save_meal(mid, m):
    """Sauvegarde un repas."""
    guests = m.nb_maternelles + m.nb_elementaires + m.nb_adultes
    execute(
        "UPDATE meals SET date=?, nb_maternelles=?, nb_elementaires=?, nb_adultes=?, guests=?, notes=?, "
        "entree=?, plat=?, accompagnement=?, laitage=?, dessert=?, commentaire_post=?, modif_prevu=?, statut=?, "
        "recipe_entree=?, recipe_plat=?, recipe_accompagnement=?, recipe_laitage=?, recipe_dessert=?, estimation=? WHERE id=?",
        (
            m.date,
            m.nb_maternelles,
            m.nb_elementaires,
            m.nb_adultes,
            guests,
            m.notes,
            m.entree,
            m.plat,
            m.accompagnement,
            m.laitage,
            m.dessert,
            m.commentaire_post,
            int(m.modif_prevu),
            m.statut,
            m.recipe_entree,
            m.recipe_plat,
            m.recipe_accompagnement,
            m.recipe_laitage,
            m.recipe_dessert,
            json.dumps(m.estimation, ensure_ascii=False) if m.estimation else None,
            mid
        )
    )
    execute("DELETE FROM meal_items WHERE meal_id=?", (mid,))
    for i in m.items:
        if i.qty > 0:
            execute(
                "INSERT INTO meal_items (meal_id, product_id, qty, unit, prix_reel) VALUES (?,?,?,?,?)",
                (mid, i.product_id, i.qty, i.unit, i.prix_reel)
            )


@router.post("/parse-menu-pdf")
async def parse_menu_pdf_route(
    file: UploadFile = File(...),
    user: dict = Depends(EDIT)
):
    """Parse un PDF de menu."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Fichier PDF attendu")
    
    import secrets
    from pathlib import Path
    uploads_dir = get_uploads_dir()
    name = f"{secrets.token_hex(6)}_{file.filename}"
    dest = uploads_dir / name
    
    size = 0
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 25 * 1024 * 1024:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "Fichier trop volumineux (25 Mo maximum)")
            f.write(chunk)
    
    try:
        repas = parse_menu_pdf(str(dest))
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, f"Lecture du PDF impossible : {e}")
    
    existing_dates = {r["date"] for r in rows("SELECT date FROM meals")}
    for r in repas:
        r["already_exists"] = r["date"] in existing_dates
    
    dest.unlink(missing_ok=True)
    return {"repas": repas, "source_file": name}


@router.post("/", response_model=dict)
async def create_meal(meal_data: MealCreate, user: dict = Depends(EDIT)):
    """Crée un nouveau repas."""
    mid = execute(
        "INSERT INTO meals (date, entree, plat, accompagnement, laitage, dessert, statut) VALUES (?,?,?,?,?,?,?)",
        (
            meal_data.date,
            meal_data.entree,
            meal_data.plat,
            meal_data.accompagnement,
            meal_data.laitage,
            meal_data.dessert,
            meal_data.statut or "prevu"
        )
    )
    save_meal(mid, meal_data)
    log_action(user, "create", "meal", mid, f"Création repas : {meal_data.date}")
    return {"id": mid}


@router.put("/{id}", response_model=dict)
async def edit_meal(
    id: int,
    meal_data: MealEdit,
    user: dict = Depends(EDIT)
):
    """Modifie un repas."""
    if not one("SELECT 1 AS x FROM meals WHERE id=?", (id,)):
        raise HTTPException(404)
    save_meal(id, meal_data)
    log_action(user, "update", "meal", id, f"Modification repas : {meal_data.date}")
    return {"ok": True}


@router.delete("/{id}", response_model=dict)
async def delete_meal(id: int, user: dict = Depends(EDIT)):
    """Supprime un repas."""
    meal = one("SELECT date FROM meals WHERE id=?", (id,))
    if not meal:
        raise HTTPException(404)
    log_action(user, "delete", "meal", id, f"Suppression repas : {meal['date']}")
    execute("DELETE FROM meals WHERE id=?", (id,))
    return {"ok": True}
