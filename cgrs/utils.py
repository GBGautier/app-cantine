"""Outils communs : horodatage, journal d'actions, unités, lecture/écriture SQL générique."""

import json
from datetime import datetime, timezone

from pydantic import BaseModel

from cgrs import db


def now_iso():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def log_action(user: dict, action: str, entity: str, entity_id, description: str = None):
    """Enregistre une action dans le journal (action_log)."""
    try:
        db.execute(
            "INSERT INTO action_log (ts, username, action, entity, entity_id, description) VALUES (?,?,?,?,?,?)",
            (now_iso(), user["username"], action, entity, entity_id, description))
    except Exception:
        pass  # le journal ne doit jamais bloquer une opération


UNITS = {
    "kg": ("mass", 1), "g": ("mass", 0.001),
    "l": ("vol", 1), "litre": ("vol", 1), "litres": ("vol", 1), "ml": ("vol", 0.001), "cl": ("vol", 0.01), "dl": ("vol", 0.1),
    "unité": ("count", 1), "unités": ("count", 1), "pièce": ("count", 1), "pièces": ("count", 1), "u": ("count", 1), "pc": ("count", 1),
    "colis": ("colis", 1), "botte": ("botte", 1), "barquette": ("barquette", 1), "bidon": ("bidon", 1), "boite": ("boite", 1),
}


def unit_info(u):
    u = (u or "").strip().lower()
    if not u:
        return None
    return UNITS.get(u) or ("x:" + u, 1)


def convert(qty, from_u, to_u):
    """Convertit une quantité d'une unité à l'autre ; None si incompatibles. Unité inconnue = même unité."""
    if qty is None:
        return None
    a, b = unit_info(from_u), unit_info(to_u)
    if a is None or b is None:
        return qty
    if a[0] != b[0]:
        return None
    return qty * a[1] / b[1]


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
