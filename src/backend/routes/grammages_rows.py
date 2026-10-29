"""Routes pour la gestion des lignes de grammages.

Ce module fournit les endpoints pour gérer les lignes de grammages GEMRCN/CGRS.
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from src.backend.utils import READ, EDIT, log_action
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/grammages-rows", tags=["Grammages"])


@router.get("/")
@router.get("")
async def get_grammages_rows(user: dict = Depends(READ)):
    """Retourne toutes les lignes de grammages."""
    return rows("SELECT * FROM grammages ORDER BY section_key, label")


@router.put("/")
@router.put("")
async def update_grammages_rows(request: Request, user: dict = Depends(EDIT)):
    """Met à jour les lignes de grammages."""
    data = await request.json()
    rows_data = data.get("rows", [])
    
    # Supprimer toutes les lignes existantes
    execute("DELETE FROM grammages")
    
    # Insérer les nouvelles lignes
    for row in rows_data:
        execute(
            "INSERT INTO grammages (section_key, section_label, section_title, label, gemrcn, cgrs, coeff, unit) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                row.get("section_key"),
                row.get("section_label"),
                row.get("section_title"),
                row.get("label"),
                row.get("gemrcn"),
                row.get("cgrs"),
                row.get("coeff", 1.0),
                row.get("unit"),
            )
        )
    
    log_action(user, "update", "grammages_rows", 0, "Mise à jour des lignes de grammages")
    return {"ok": True}
