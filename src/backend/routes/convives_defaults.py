"""Routes pour la gestion des convives par défaut.

Ce module fournit les endpoints pour gérer les nombres de convives par défaut.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from src.backend.utils import READ, EDIT, log_action
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/convives-defaults", tags=["Paramètres"])


@router.get("/")
async def get_convives_defaults(user: dict = Depends(READ)):
    """Retourne les convives par défaut."""
    result = one("SELECT value FROM settings WHERE key='convives_defaults'")
    if result:
        return result["value"]
    return {}


@router.put("/")
async def update_convives_defaults(request: Request, user: dict = Depends(EDIT)):
    """Met à jour les convives par défaut."""
    data = await request.json()
    
    # Vérifier si la clé existe
    existing = one("SELECT 1 AS x FROM settings WHERE key='convives_defaults'")
    if existing:
        execute("UPDATE settings SET value=? WHERE key='convives_defaults'", (data,))
    else:
        execute("INSERT INTO settings (key, value) VALUES (?,?)", ("convives_defaults", data))
    
    log_action(user, "update", "settings", 0, "Mise à jour des convives par défaut")
    return {"ok": True}
