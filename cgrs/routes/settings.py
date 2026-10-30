"""Paramètres de l'application (noms de la cantine)."""

from fastapi import APIRouter
from pydantic import BaseModel

import db
from cgrs.security import ADMIN
from cgrs.utils import log_action


router = APIRouter()


class Settings(BaseModel):
    client_names: str = ""   # noms de la cantine, séparés par « ; » (jamais pris pour un fournisseur)


def get_client_names():
    r = db.one("SELECT value FROM settings WHERE key='client_names'")
    return [x.strip() for x in (r["value"] if r else "").split(";") if x.strip()]


@router.get("/api/settings")
def get_settings(user: dict = ADMIN):
    return {"client_names": "; ".join(get_client_names())}


@router.put("/api/settings")
def put_settings(s: Settings, user: dict = ADMIN):
    db.execute("INSERT INTO settings (key, value) VALUES ('client_names', ?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (s.client_names,))
    log_action(user, "update", "settings", None, f"Nom de la cantine : {s.client_names!r}")
    return {"ok": True}
