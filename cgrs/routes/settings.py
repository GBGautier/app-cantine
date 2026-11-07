"""Paramètres de l'application (noms de la cantine)."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cgrs import db
from cgrs.security import ADMIN
from cgrs.utils import log_action


router = APIRouter()


class Settings(BaseModel):
    client_names: str = ""  # noms de la cantine, séparés par « ; » (jamais pris pour un fournisseur)
    tarif_repas: Optional[float] = (
        None  # tarif de vente d'un repas (€) : sert au déficit du bilan mensuel ; inchangé si absent
    )


TARIF_REPAS_DEFAUT = 2.04


def get_tarif_repas():
    """Tarif de vente d'un repas (€), réglé dans les paramètres."""
    r = db.one("SELECT value FROM settings WHERE key='tarif_repas'")
    try:
        v = float(r["value"]) if r else TARIF_REPAS_DEFAUT
    except (TypeError, ValueError):
        v = TARIF_REPAS_DEFAUT
    return v if v > 0 else TARIF_REPAS_DEFAUT


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
    return {
        "client_names": "; ".join(x.strip() for x in (r["value"] if r else "").split(";") if x.strip()),
        "tarif_repas": get_tarif_repas(),
    }


@router.put("/api/settings")
def put_settings(s: Settings, user: dict = ADMIN):
    if s.tarif_repas is not None and not 0 < s.tarif_repas <= 50:
        raise HTTPException(422, "Le tarif d'un repas doit être compris entre 0 et 50 €.")
    db.execute(
        "INSERT INTO settings (key, value) VALUES ('client_names', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (s.client_names,),
    )
    if s.tarif_repas is not None:
        db.execute(
            "INSERT INTO settings (key, value) VALUES ('tarif_repas', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(round(s.tarif_repas, 2)),),
        )
    log_action(
        user, "update", "settings", None, f"Nom de la cantine : {s.client_names!r} ; tarif repas : {get_tarif_repas()}"
    )
    return {"ok": True}
