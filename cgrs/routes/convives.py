"""Effectifs par défaut des repas."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cgrs import db
from cgrs.security import ADMIN, ANY
from cgrs.utils import log_action


router = APIRouter()


# ---------- convives par défaut (repas, recettes, grammages) ----------
class ConvivesDefaults(BaseModel):
    mat: int = 140  # maternelles
    elem: int = 240  # élémentaires
    adu: int = 5  # adultes


@router.get("/api/convives-defaults")
def get_convives_defaults(user: dict = ANY):
    import json

    r = db.one("SELECT value FROM settings WHERE key='convives_defaults'")
    if r and r["value"]:
        try:
            d = json.loads(r["value"])
            return {"mat": int(d.get("mat", 140)), "elem": int(d.get("elem", 240)), "adu": int(d.get("adu", 5))}
        except Exception:
            pass
    return {"mat": 140, "elem": 240, "adu": 5}


@router.put("/api/convives-defaults")
def put_convives_defaults(c: ConvivesDefaults, user: dict = ADMIN):
    import json

    if min(c.mat, c.elem, c.adu) < 0:
        raise HTTPException(400, "Les effectifs ne peuvent pas être négatifs")
    value = json.dumps({"mat": c.mat, "elem": c.elem, "adu": c.adu})
    db.execute(
        "INSERT INTO settings (key, value) VALUES ('convives_defaults', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (value,),
    )
    log_action(user, "update", "settings", None, f"Convives par défaut : {value}")
    return {"ok": True}
