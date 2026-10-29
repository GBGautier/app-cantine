"""Routes pour la gestion des utilisateurs."""

from fastapi import APIRouter, Depends, HTTPException

from src.backend.models.auth import UserCreate, UserEdit, UserOut
from src.backend.utils import (
    ADMIN,
    admin_count,
    check_password_rule,
    clean_username,
    hash_password,
    log_action,
    now_iso,
)
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/users", tags=["Utilisateurs"])


@router.get("/", response_model=list[UserOut])
async def list_users(user: dict = Depends(ADMIN)):
    """Liste tous les utilisateurs."""
    return rows("SELECT id, username, role, created FROM users ORDER BY username")


@router.post("/", response_model=dict)
async def create_user(user_data: UserCreate, current_user: dict = Depends(ADMIN)):
    """Crée un nouvel utilisateur."""
    if user_data.role not in ["admin", "editor", "reader", "stats"]:
        raise HTTPException(400, "Profil inconnu")
    username = clean_username(user_data.username)
    check_password_rule(user_data.password)
    if one("SELECT 1 AS x FROM users WHERE username=?", (username,)):
        raise HTTPException(400, "Cet identifiant existe déjà")
    uid = execute(
        "INSERT INTO users (username, password_hash, role, created) VALUES (?,?,?,?)",
        (username, hash_password(user_data.password), user_data.role, now_iso())
    )
    log_action(
        current_user,
        "create",
        "user",
        uid,
        f"Création utilisateur {username!r} ({user_data.role})"
    )
    return {"id": uid}


@router.put("/{id}", response_model=dict)
async def edit_user(
    id: int,
    user_data: UserEdit,
    current_user: dict = Depends(ADMIN)
):
    """Modifie un utilisateur."""
    target = one("SELECT * FROM users WHERE id=?", (id,))
    if not target:
        raise HTTPException(404)
    changes = []
    if user_data.role is not None:
        if user_data.role not in ["admin", "editor", "reader", "stats"]:
            raise HTTPException(400, "Profil inconnu")
        if target["role"] == "admin" and user_data.role != "admin" and admin_count() <= 1:
            raise HTTPException(400, "Il doit rester au moins un administrateur")
        execute("UPDATE users SET role=? WHERE id=?", (user_data.role, id))
        changes.append(f"profil → {user_data.role}")
    if user_data.password:
        check_password_rule(user_data.password)
        execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(user_data.password), id))
        changes.append("mot de passe modifié")
    if user_data.role is not None or user_data.password:
        execute("DELETE FROM sessions WHERE user_id=?", (id,))
    if changes:
        log_action(
            current_user,
            "update",
            "user",
            id,
            f"Modification utilisateur {target['username']!r} : {', '.join(changes)}"
        )
    return {"ok": True}


@router.delete("/{id}", response_model=dict)
async def delete_user(id: int, current_user: dict = Depends(ADMIN)):
    """Supprime un utilisateur."""
    target = one("SELECT * FROM users WHERE id=?", (id,))
    if not target:
        raise HTTPException(404)
    if id == current_user["id"]:
        raise HTTPException(400, "Vous ne pouvez pas supprimer votre propre compte")
    if target["role"] == "admin" and admin_count() <= 1:
        raise HTTPException(400, "Il doit rester au moins un administrateur")
    log_action(
        current_user,
        "delete",
        "user",
        id,
        f"Suppression utilisateur {target['username']!r}"
    )
    execute("DELETE FROM users WHERE id=?", (id,))
    return {"ok": True}
