"""Routes pour la gestion du journal d'actions.

Ce module fournit les endpoints pour consulter le journal des actions.
"""

from fastapi import APIRouter, Depends

from src.backend.utils import READ
from src.backend.db import rows

router = APIRouter(prefix="/api/action-log", tags=["Journal"])


@router.get("/")
async def get_action_log(user: dict = Depends(READ)):
    """Retourne le journal des actions."""
    return rows(
        "SELECT a.id, a.ts, a.username, a.action, a.entity, a.entity_id, a.description "
        "FROM action_log a ORDER BY a.ts DESC LIMIT 100"
    )
