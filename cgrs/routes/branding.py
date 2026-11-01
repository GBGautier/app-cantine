"""Personnalisation de l'application : nom, sous-titre et logo de la cantine.

La lecture est publique (l'écran de connexion et l'icône de l'onglet en ont besoin avant toute connexion) ;
la modification est réservée à l'administrateur. Le logo est stocké dans la base : il suit les sauvegardes.
"""

import base64
import hashlib

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from cgrs import db
from cgrs.security import ADMIN
from cgrs.services.branding import LOGO_MAX_BYTES, clean_name, clean_subtitle, image_type
from cgrs.utils import log_action


router = APIRouter()


class Branding(BaseModel):
    name: str = ""
    subtitle: str = ""


def _get(key):
    r = db.one("SELECT value FROM settings WHERE key=?", (key,))
    return r["value"] if r else None


def _set(key, value):
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_branding():
    logo = _get("org_logo")
    return {
        "name": clean_name(_get("org_name")),
        "subtitle": clean_subtitle(_get("org_subtitle")),
        "logo": f"/api/branding/logo?v={hashlib.sha1(logo.encode()).hexdigest()[:10]}" if logo else None,
    }


@router.get("/api/branding")
def branding():
    return get_branding()


@router.get("/api/branding/logo")
def branding_logo():
    logo, kind = _get("org_logo"), _get("org_logo_type")
    if not logo or not kind:
        raise HTTPException(404, "Aucun logo")
    return Response(
        base64.b64decode(logo),
        media_type=kind,
        headers={"Cache-Control": "no-cache", "Content-Security-Policy": "default-src 'none'"},
    )


@router.put("/api/branding")
@db.atomic
def put_branding(b: Branding, user: dict = ADMIN):
    name = clean_name(b.name)
    _set("org_name", name)
    _set("org_subtitle", clean_subtitle(b.subtitle))
    log_action(user, "update", "settings", None, f"Personnalisation : nom {name!r}")
    return get_branding()


@db.atomic
def _store_logo(data, kind, user):
    _set("org_logo", base64.b64encode(data).decode())
    _set("org_logo_type", kind)
    log_action(user, "update", "settings", None, "Logo remplacé")


@router.post("/api/branding/logo")
async def put_logo(file: UploadFile = File(...), user: dict = ADMIN):
    data = await file.read(LOGO_MAX_BYTES + 1)
    if len(data) > LOGO_MAX_BYTES:
        raise HTTPException(413, "Logo trop volumineux (512 Ko maximum)")
    kind = image_type(data)
    if not kind:
        raise HTTPException(400, "Image PNG, JPEG ou WebP attendue")
    _store_logo(data, kind, user)
    return get_branding()


@router.delete("/api/branding/logo")
@db.atomic
def delete_logo(user: dict = ADMIN):
    db.execute("DELETE FROM settings WHERE key IN ('org_logo', 'org_logo_type')")
    log_action(user, "delete", "settings", None, "Logo retiré")
    return get_branding()
