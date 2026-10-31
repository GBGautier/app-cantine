"""Outils communs : horodatage, journal d'actions, unités, lecture/écriture SQL générique."""

import json
from datetime import datetime, timezone

from pydantic import BaseModel

from cgrs import db
from cgrs.services.units import UNITS, convert, unit_info  # noqa: F401  (réexportés : anciens imports)


def now_iso():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def log_action(user: dict, action: str, entity: str, entity_id, description: str = None):
    """Enregistre une action dans le journal (action_log)."""
    try:
        db.execute(
            "INSERT INTO action_log (ts, username, action, entity, entity_id, description) VALUES (?,?,?,?,?,?)",
            (now_iso(), user["username"], action, entity, entity_id, description),
        )
    except Exception:
        pass  # le journal ne doit jamais bloquer une opération


def fields(model: BaseModel, exclude=()):
    d = model.model_dump(exclude=set(exclude))
    vals = [json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v for v in d.values()]
    return list(d.keys()), vals


def insert(table, model, exclude=()):
    cols, vals = fields(model, exclude)
    return db.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)


def update(table, id_, model, exclude=()):
    cols, vals = fields(model, exclude)
    db.execute(f"UPDATE {table} SET {','.join(c + '=?' for c in cols)} WHERE id=?", vals + [id_])
