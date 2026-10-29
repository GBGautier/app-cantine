"""Routes pour la gestion des grammages."""

from fastapi import APIRouter, Depends, HTTPException

from src.backend.utils import ADMIN, EDIT, READ, log_action
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/grammages", tags=["Grammages"])


@router.get("/")
async def list_grammages(user: dict = Depends(READ)):
    """Liste tous les grammages."""
    return rows("SELECT * FROM grammages ORDER BY section_key, label")


@router.get("/{id}")
async def get_grammage(id: int, user: dict = Depends(READ)):
    """Récupère un grammage par son ID."""
    grammage = one("SELECT * FROM grammages WHERE id=?", (id,))
    if not grammage:
        raise HTTPException(404)
    return grammage


@router.post("/")
async def create_grammage(
    section_key: str,
    section_label: str,
    section_title: str | None = None,
    label: str = None,
    gemrcn: str | None = None,
    cgrs: str | None = None,
    coeff: float = 1.0,
    unit: str | None = None,
    user: dict = Depends(ADMIN)
):
    """Crée un nouveau grammage."""
    gid = execute(
        "INSERT INTO grammages (section_key, section_label, section_title, label, gemrcn, cgrs, coeff, unit) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (section_key, section_label, section_title, label, gemrcn, cgrs, coeff, unit)
    )
    log_action(user, "create", "grammage", gid, f"Grammage créé : {label}")
    return {"id": gid}


@router.put("/{id}")
async def edit_grammage(
    id: int,
    section_key: str | None = None,
    section_label: str | None = None,
    section_title: str | None = None,
    label: str | None = None,
    gemrcn: str | None = None,
    cgrs: str | None = None,
    coeff: float | None = None,
    unit: str | None = None,
    user: dict = Depends(ADMIN)
):
    """Modifie un grammage."""
    if not one("SELECT 1 AS x FROM grammages WHERE id=?", (id,)):
        raise HTTPException(404)
    
    fields = []
    values = []
    if section_key is not None:
        fields.append("section_key=?")
        values.append(section_key)
    if section_label is not None:
        fields.append("section_label=?")
        values.append(section_label)
    if section_title is not None:
        fields.append("section_title=?")
        values.append(section_title)
    if label is not None:
        fields.append("label=?")
        values.append(label)
    if gemrcn is not None:
        fields.append("gemrcn=?")
        values.append(gemrcn)
    if cgrs is not None:
        fields.append("cgrs=?")
        values.append(cgrs)
    if coeff is not None:
        fields.append("coeff=?")
        values.append(coeff)
    if unit is not None:
        fields.append("unit=?")
        values.append(unit)
    
    if fields:
        values.append(id)
        execute(f"UPDATE grammages SET {','.join(fields)} WHERE id=?", values)
        log_action(user, "update", "grammage", id, "Modification grammage")
    
    return {"ok": True}


@router.delete("/{id}")
async def delete_grammage(id: int, user: dict = Depends(ADMIN)):
    """Supprime un grammage."""
    grammage = one("SELECT label FROM grammages WHERE id=?", (id,))
    if not grammage:
        raise HTTPException(404)
    log_action(user, "delete", "grammage", id, f"Suppression grammage : {grammage['label']}")
    execute("DELETE FROM grammages WHERE id=?", (id,))
    return {"ok": True}
