"""Routes pour la gestion des paramètres."""

from fastapi import APIRouter, Depends, HTTPException

from src.backend.utils import ADMIN, log_action
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/settings", tags=["Paramètres"])


@router.get("/")
async def get_settings(user: dict = Depends(ADMIN)):
    """Récupère tous les paramètres."""
    return rows("SELECT * FROM settings")


@router.get("/{key}")
async def get_setting(key: str, user: dict = Depends(ADMIN)):
    """Récupère un paramètre par sa clé."""
    setting = one("SELECT * FROM settings WHERE key=?", (key,))
    if not setting:
        raise HTTPException(404)
    return setting


@router.post("/")
async def create_setting(key: str, value: str, user: dict = Depends(ADMIN)):
    """Crée un nouveau paramètre."""
    if one("SELECT 1 AS x FROM settings WHERE key=?", (key,)):
        raise HTTPException(400, "Ce paramètre existe déjà")
    execute("INSERT INTO settings (key, value) VALUES (?,?)", (key, value))
    log_action(user, "create", "setting", 0, f"Paramètre créé : {key}")
    return {"ok": True}


@router.put("/{key}")
async def edit_setting(key: str, value: str, user: dict = Depends(ADMIN)):
    """Modifie un paramètre."""
    if not one("SELECT 1 AS x FROM settings WHERE key=?", (key,)):
        raise HTTPException(404)
    execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    log_action(user, "update", "setting", 0, f"Paramètre modifié : {key}")
    return {"ok": True}


@router.delete("/{key}")
async def delete_setting(key: str, user: dict = Depends(ADMIN)):
    """Supprime un paramètre."""
    if not one("SELECT 1 AS x FROM settings WHERE key=?", (key,)):
        raise HTTPException(404)
    execute("DELETE FROM settings WHERE key=?", (key,))
    log_action(user, "delete", "setting", 0, f"Paramètre supprimé : {key}")
    return {"ok": True}
