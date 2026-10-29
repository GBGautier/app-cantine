"""Routes pour la gestion des engagements."""

from fastapi import APIRouter, Depends, HTTPException

from src.backend.models.commitments import CommitmentCreate, CommitmentEdit, CommitmentOut
from src.backend.utils import (
    ADMIN,
    READ,
    log_action,
    now_iso,
)
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/commitments", tags=["Engagements"])


@router.get("/", response_model=list[CommitmentOut])
async def list_commitments(user: dict = Depends(READ)):
    """Liste tous les engagements."""
    return rows("SELECT * FROM commitments ORDER BY label")


@router.get("/{id}", response_model=CommitmentOut)
async def get_commitment(id: int, user: dict = Depends(READ)):
    """Récupère un engagement par son ID."""
    commitment = one("SELECT * FROM commitments WHERE id=?", (id,))
    if not commitment:
        raise HTTPException(404)
    return commitment


@router.post("/", response_model=dict)
async def create_commitment(
    commitment_data: CommitmentCreate,
    user: dict = Depends(ADMIN)
):
    """Crée un nouvel engagement."""
    cid = execute(
        "INSERT INTO commitments (label, metric, metrics, category, categories, gammes, level, target, mode, notes) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            commitment_data.label,
            commitment_data.metric,
            commitment_data.metrics,
            commitment_data.category,
            commitment_data.categories,
            commitment_data.gammes,
            commitment_data.level,
            commitment_data.target,
            commitment_data.mode,
            commitment_data.notes,
        )
    )
    log_action(
        user,
        "create",
        "commitment",
        cid,
        f"Création engagement : {commitment_data.label!r}"
    )
    return {"id": cid}


@router.put("/{id}", response_model=dict)
async def edit_commitment(
    id: int,
    commitment_data: CommitmentEdit,
    user: dict = Depends(ADMIN)
):
    """Modifie un engagement."""
    if not one("SELECT 1 AS x FROM commitments WHERE id=?", (id,)):
        raise HTTPException(404)
    
    fields = []
    values = []
    if commitment_data.label is not None:
        fields.append("label=?")
        values.append(commitment_data.label)
    if commitment_data.metric is not None:
        fields.append("metric=?")
        values.append(commitment_data.metric)
    if commitment_data.metrics is not None:
        fields.append("metrics=?")
        values.append(commitment_data.metrics)
    if commitment_data.category is not None:
        fields.append("category=?")
        values.append(commitment_data.category)
    if commitment_data.categories is not None:
        fields.append("categories=?")
        values.append(commitment_data.categories)
    if commitment_data.gammes is not None:
        fields.append("gammes=?")
        values.append(commitment_data.gammes)
    if commitment_data.level is not None:
        fields.append("level=?")
        values.append(commitment_data.level)
    if commitment_data.target is not None:
        fields.append("target=?")
        values.append(commitment_data.target)
    if commitment_data.mode is not None:
        fields.append("mode=?")
        values.append(commitment_data.mode)
    if commitment_data.notes is not None:
        fields.append("notes=?")
        values.append(commitment_data.notes)
    
    if fields:
        values.append(id)
        execute(f"UPDATE commitments SET {','.join(fields)} WHERE id=?", values)
        log_action(user, "update", "commitment", id, "Modification engagement")
    
    return {"ok": True}


@router.delete("/{id}", response_model=dict)
async def delete_commitment(id: int, user: dict = Depends(ADMIN)):
    """Supprime un engagement."""
    commitment = one("SELECT label FROM commitments WHERE id=?", (id,))
    if not commitment:
        raise HTTPException(404)
    log_action(
        user,
        "delete",
        "commitment",
        id,
        f"Suppression engagement : {commitment['label']!r}"
    )
    execute("DELETE FROM commitments WHERE id=?", (id,))
    return {"ok": True}
