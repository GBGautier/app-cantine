"""Journal des actions."""

from fastapi import APIRouter

from cgrs import db
from cgrs.security import ADMIN


router = APIRouter()


@router.get("/api/action-log")
def get_action_log(limit: int = 200, user: dict = ADMIN):
    rows = db.rows(
        "SELECT id, ts, username, action, entity, entity_id, description "
        "FROM action_log ORDER BY ts DESC, id DESC LIMIT ?",
        (limit,),
    )
    return rows
