"""Repas et coûts matières."""

import json
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, field_validator

import db
import menu_parser
from cgrs.config import UPLOADS
from cgrs.constants import CATEGORIES, LOCAL
from cgrs.pricing import load_history, price_at
from cgrs.security import READ, WRITE
from cgrs.uploads import save_upload
from cgrs.utils import convert


router = APIRouter()


class MealItem(BaseModel):
    product_id: int
    qty: float
    unit: Optional[str] = None
    prix_reel: Optional[float] = None


class Meal(BaseModel):
    date: str
    nb_maternelles: int = 0
    nb_elementaires: int = 0
    nb_adultes: int = 0
    notes: Optional[str] = None
    entree: Optional[str] = None
    plat: Optional[str] = None
    accompagnement: Optional[str] = None
    laitage: Optional[str] = None
    dessert: Optional[str] = None
    commentaire_post: Optional[str] = None
    modif_prevu: bool = False
    statut: str = "prevu"
    recipe_entree: Optional[int] = None
    recipe_plat: Optional[int] = None
    recipe_accompagnement: Optional[int] = None
    recipe_laitage: Optional[int] = None
    recipe_dessert: Optional[int] = None
    estimation: Optional[list] = None   # lignes de l'estimation des coûts : [{cat, label, product_id, qty, price, unit, manual}]
    items: list[MealItem] = []

    @field_validator("nb_maternelles", "nb_elementaires", "nb_adultes")
    @classmethod
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("Les effectifs ne peuvent pas être négatifs")
        return v


def meals_metrics(date_from=None, date_to=None, product_id=None):
    where, args = ["1=1"], []
    if date_from:
        where.append("m.date >= ?"); args.append(date_from)
    if date_to:
        where.append("m.date <= ?"); args.append(date_to)
    if product_id:   # filtre : repas dont le bilan (lignes réellement sorties) contient ce produit
        where.append("m.id IN (SELECT meal_id FROM meal_items WHERE product_id=?)"); args.append(product_id)
    w = " AND ".join(where)
    meals = db.rows(f"SELECT m.* FROM meals m WHERE {w} ORDER BY m.date DESC, m.id DESC", args)
    items = db.rows(
        "SELECT i.meal_id, i.product_id, i.qty, i.unit, i.prix_reel, m.date AS mdate, p.unit AS punit, p.unit_price, "
        "p.label_egalim, p.provenance FROM meal_items i JOIN meals m ON m.id=i.meal_id "
        f"JOIN products p ON p.id=i.product_id WHERE {w}", args)
    hist = load_history()
    acc = {m["id"]: {"cost": 0.0, "bio": 0.0, "local": 0.0, "n": 0, "unpriced": 0} for m in meals}
    for it in items:
        a = acc[it["meal_id"]]
        a["n"] += 1
        # Prix réel saisi manuellement > historique calculé
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
        if it["provenance"] in LOCAL:
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


@router.get("/api/meals")
def meals(product_id: int = None, user: dict = READ):
    return meals_metrics(product_id=product_id)


@router.get("/api/meals/shopping-list")
def shopping_list(date_from: str, date_to: str, user: dict = READ):
    """Liste de courses : quantités des produits sortis pour les repas de la période, triées par catégorie."""
    rows = db.rows(
        "SELECT i.product_id, i.qty, i.unit, p.name, p.category, p.unit AS punit "
        "FROM meal_items i JOIN meals m ON m.id=i.meal_id JOIN products p ON p.id=i.product_id "
        "WHERE m.date >= ? AND m.date <= ?", (date_from, date_to))
    acc = {}
    for r in rows:
        pu = r["punit"] or r["unit"] or "kg"
        q = convert(r["qty"], r["unit"] or pu, pu)
        u = pu
        if q is None:   # unité incompatible avec celle du produit : gardée telle quelle
            q, u = r["qty"], r["unit"] or pu
        a = acc.setdefault((r["product_id"], u), {
            "product_id": r["product_id"], "label": r["name"], "category": r["category"] or "Autre",
            "unit": u, "qty": 0.0})
        a["qty"] += q
    out = sorted(acc.values(), key=lambda a: (
        CATEGORIES.index(a["category"]) if a["category"] in CATEGORIES else len(CATEGORIES),
        a["category"].lower(), a["label"].lower()))
    for a in out:
        a["qty"] = round(a["qty"], 3)
    return out


@router.get("/api/meals/{id}")
def get_meal(id: int, user: dict = READ):
    m = db.one("SELECT * FROM meals WHERE id=?", (id,))
    if not m:
        raise HTTPException(404)
    m["items"] = db.rows(
        "SELECT i.*, p.name AS product_name, p.unit_price AS unit_price FROM meal_items i "
        "JOIN products p ON p.id=i.product_id WHERE i.meal_id=? ORDER BY i.id", (id,))
    try:
        m["estimation"] = json.loads(m["estimation"]) if m.get("estimation") else []
    except (ValueError, TypeError):
        m["estimation"] = []
    return dict(m)


def save_meal(mid, m: Meal):
    guests = m.nb_maternelles + m.nb_elementaires + m.nb_adultes
    db.execute(
        "UPDATE meals SET date=?, nb_maternelles=?, nb_elementaires=?, nb_adultes=?, guests=?, notes=?, "
        "entree=?, plat=?, accompagnement=?, laitage=?, dessert=?, commentaire_post=?, modif_prevu=?, statut=?, "
        "recipe_entree=?, recipe_plat=?, recipe_accompagnement=?, recipe_laitage=?, recipe_dessert=?, estimation=? WHERE id=?",
        (m.date, m.nb_maternelles, m.nb_elementaires, m.nb_adultes, guests, m.notes,
         m.entree, m.plat, m.accompagnement, m.laitage, m.dessert, m.commentaire_post, int(m.modif_prevu), m.statut,
         m.recipe_entree, m.recipe_plat, m.recipe_accompagnement, m.recipe_laitage, m.recipe_dessert,
         json.dumps(m.estimation, ensure_ascii=False) if m.estimation else None, mid))
    db.execute("DELETE FROM meal_items WHERE meal_id=?", (mid,))
    for i in m.items:
        if i.qty > 0:
            db.execute("INSERT INTO meal_items (meal_id, product_id, qty, unit, prix_reel) VALUES (?,?,?,?,?)",
                       (mid, i.product_id, i.qty, i.unit, i.prix_reel))


@router.post("/api/meals/parse-menu-pdf")
async def parse_menu_pdf(file: UploadFile = File(...), user: dict = WRITE):
    """Lit un PDF de menu et renvoie la liste des repas détectés (rien n'est enregistré)."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Fichier PDF attendu")
    name = await save_upload(file, allowed={".pdf"})
    path = str(UPLOADS / name)
    try:
        repas = menu_parser.parse_menu_pdf(path)
    except Exception as e:
        (UPLOADS / name).unlink(missing_ok=True)
        raise HTTPException(422, f"Lecture du PDF impossible : {e}") from e
    # Marquer les dates déjà enregistrées
    existing_dates = {r["date"] for r in db.rows("SELECT date FROM meals")}
    for r in repas:
        r["already_exists"] = r["date"] in existing_dates
    return {"repas": repas, "source_file": name}


@router.post("/api/meals")
@db.atomic
def create_meal(m: Meal, user: dict = WRITE):
    mid = db.execute(
        "INSERT INTO meals (date, entree, plat, accompagnement, laitage, dessert, statut) VALUES (?,?,?,?,?,?,?)",
        (m.date, m.entree, m.plat, m.accompagnement, m.laitage, m.dessert, m.statut or "prevu"))
    save_meal(mid, m)
    return {"id": mid}


@router.put("/api/meals/{id}")
@db.atomic
def edit_meal(id: int, m: Meal, user: dict = WRITE):
    if not db.one("SELECT 1 AS x FROM meals WHERE id=?", (id,)):
        raise HTTPException(404)
    save_meal(id, m)
    return {"ok": True}


@router.delete("/api/meals/{id}")
def delete_meal(id: int, user: dict = WRITE):
    db.execute("DELETE FROM meals WHERE id=?", (id,))
    return {"ok": True}
