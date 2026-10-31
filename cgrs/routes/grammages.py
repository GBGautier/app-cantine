"""Grammages (référentiel GEMRCN et valeurs de la cantine)."""

import json
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from cgrs import db
from cgrs.security import ANY, EDIT
from cgrs.utils import log_action


router = APIRouter()


# ---------- grammages CGRS (overrides) ----------
@router.get("/api/grammages")
def get_grammages(user: dict = ANY):
    r = db.one("SELECT value FROM settings WHERE key='grammages_overrides'")
    try:
        return json.loads(r["value"]) if r else {}
    except Exception:
        return {}


class GrammageOverride(BaseModel):
    overrides: dict  # {"tab__sectionIdx__rowIdx": {"cgrs": ["val","val","val"], "coeff": 1.33}}


# ---------- grammages CGRS (données complètes en base) ----------
class GrammageRow(BaseModel):
    section_key: str = ""
    section_label: str = ""
    section_title: Optional[str] = None
    label: str
    gemrcn: list[str] = []
    cgrs: list[str] = []
    coeff: float = 1
    unit: Optional[str] = None


def grammage_out(r):
    r = dict(r)
    for k in ("gemrcn", "cgrs"):
        try:
            r[k] = json.loads(r[k]) if r.get(k) else []
        except (ValueError, TypeError):
            r[k] = []
    return r


@router.get("/api/grammages-rows")
def get_grammages_rows(user: dict = ANY):
    """Grammages complets (GEMRCN + CGRS + coefficient cru/cuit). Liste vide au premier lancement :
    le navigateur enregistre alors les valeurs par défaut (voir loadGramRows côté client)."""
    return [grammage_out(r) for r in db.rows("SELECT * FROM grammages ORDER BY id")]


class GrammageRowsUpdate(BaseModel):
    rows: list[GrammageRow] = []


@router.put("/api/grammages-rows")
@db.atomic
def put_grammages_rows(g: GrammageRowsUpdate, user: dict = EDIT):
    db.execute("DELETE FROM grammages")
    for r in g.rows:
        db.execute(
            "INSERT INTO grammages (section_key, section_label, section_title, label, gemrcn, cgrs, coeff, unit) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (r.section_key, r.section_label, r.section_title, r.label,
             json.dumps(r.gemrcn, ensure_ascii=False), json.dumps(r.cgrs, ensure_ascii=False),
             r.coeff, r.unit))
    log_action(user, "update", "grammages", None, f"{len(g.rows)} lignes de grammages enregistrées")
    return {"ok": True, "rows": len(g.rows)}


@router.put("/api/grammages")
def put_grammages(g: GrammageOverride, user: dict = EDIT):
    db.execute("INSERT INTO settings (key, value) VALUES ('grammages_overrides', ?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (json.dumps(g.overrides, ensure_ascii=False),))
    log_action(user, "update", "settings", None, "Mise à jour des grammages CGRS")
    return {"ok": True}
