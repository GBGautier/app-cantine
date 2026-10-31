"""Gestion des utilisateurs (administrateur)."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cgrs import db
from cgrs.constants import ROLES
from cgrs.security import ADMIN, check_password_rule, clean_username, hash_password
from cgrs.utils import log_action, now_iso


router = APIRouter()


class NewUser(BaseModel):
    username: str
    password: str
    role: str


class UserEdit(BaseModel):
    role: Optional[str] = None
    password: Optional[str] = None


def admin_count():
    return db.one("SELECT COUNT(*) AS n FROM users WHERE role='admin'")["n"]


@router.get("/api/users")
def list_users(user: dict = ADMIN):
    return db.rows("SELECT id, username, role, created FROM users ORDER BY username")


@router.post("/api/users")
@db.atomic
def create_user(u: NewUser, user: dict = ADMIN):
    if u.role not in ROLES:
        raise HTTPException(400, "Profil inconnu")
    username = clean_username(u.username)
    check_password_rule(u.password)
    if db.one("SELECT 1 AS x FROM users WHERE username=?", (username,)):
        raise HTTPException(400, "Cet identifiant existe déjà")
    uid = db.execute(
        "INSERT INTO users (username, password_hash, role, created) VALUES (?,?,?,?)",
        (username, hash_password(u.password), u.role, now_iso()),
    )
    log_action(user, "create", "user", uid, f"Création utilisateur {username!r} ({u.role})")
    return {"id": uid}


@router.put("/api/users/{id}")
@db.atomic
def edit_user(id: int, u: UserEdit, user: dict = ADMIN):
    target = db.one("SELECT * FROM users WHERE id=?", (id,))
    if not target:
        raise HTTPException(404)
    changes = []
    if u.role is not None:
        if u.role not in ROLES:
            raise HTTPException(400, "Profil inconnu")
        if target["role"] == "admin" and u.role != "admin" and admin_count() <= 1:
            raise HTTPException(400, "Il doit rester au moins un administrateur")
        db.execute("UPDATE users SET role=? WHERE id=?", (u.role, id))
        changes.append(f"profil → {u.role}")
    if u.password:
        check_password_rule(u.password)
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(u.password), id))
        changes.append("mot de passe modifié")
    if u.role is not None or u.password:
        db.execute("DELETE FROM sessions WHERE user_id=?", (id,))  # force une nouvelle connexion
    if changes:
        log_action(
            user, "update", "user", id, f"Modification utilisateur {target['username']!r} : {', '.join(changes)}"
        )
    return {"ok": True}


@router.delete("/api/users/{id}")
def delete_user(id: int, user: dict = ADMIN):
    target = db.one("SELECT * FROM users WHERE id=?", (id,))
    if not target:
        raise HTTPException(404)
    if id == user["id"]:
        raise HTTPException(400, "Vous ne pouvez pas supprimer votre propre compte")
    if target["role"] == "admin" and admin_count() <= 1:
        raise HTTPException(400, "Il doit rester au moins un administrateur")
    log_action(user, "delete", "user", id, f"Suppression utilisateur {target['username']!r}")
    db.execute("DELETE FROM users WHERE id=?", (id,))
    return {"ok": True}
