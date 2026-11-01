"""Paramètres de l'application (noms de la cantine)."""

from fastapi import APIRouter
from pydantic import BaseModel

from cgrs import db
from cgrs.security import ADMIN
from cgrs.utils import log_action


router = APIRouter()


class Settings(BaseModel):
    client_names: str = ""  # noms de la cantine, séparés par « ; » (jamais pris pour un fournisseur)


def get_client_names():
    """Noms de la cantine sur les documents : ceux de la liste, plus le nom de la personnalisation s'il est défini."""
    r = db.one("SELECT value FROM settings WHERE key='client_names'")
    names = [x.strip() for x in (r["value"] if r else "").split(";") if x.strip()]
    org = db.one("SELECT value FROM settings WHERE key='org_name'")
    if org and org["value"].strip() and org["value"].strip() not in names:
        names.append(org["value"].strip())
    return names


@router.get("/api/settings")
def get_settings(user: dict = ADMIN):
    r = db.one("SELECT value FROM settings WHERE key='client_names'")
    return {"client_names": "; ".join(x.strip() for x in (r["value"] if r else "").split(";") if x.strip())}


@router.put("/api/settings")
def put_settings(s: Settings, user: dict = ADMIN):
    db.execute(
        "INSERT INTO settings (key, value) VALUES ('client_names', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (s.client_names,),
    )
    log_action(user, "update", "settings", None, f"Nom de la cantine : {s.client_names!r}")
    return {"ok": True}
