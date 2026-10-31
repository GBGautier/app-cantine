"""Identification : état, création du premier compte, connexion, déconnexion, mot de passe."""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

import db
from cgrs.security import ANY, check_password_rule, check_rate, clean_username, COOKIE, current_user, DUMMY_HASH, FAILS, hash_password, register_fail, sha, start_session, verify_password
from cgrs.utils import now_iso


router = APIRouter()


class Credentials(BaseModel):
    username: str
    password: str


@router.get("/api/auth/status")
def auth_status(request: Request):
    return {"setup_needed": not db.one("SELECT 1 AS x FROM users LIMIT 1"), "user": current_user(request)}


@router.post("/api/auth/setup")
@db.atomic
def auth_setup(c: Credentials, request: Request, response: Response):
    """Création du premier compte (administrateur) : possible uniquement tant qu'aucun utilisateur n'existe."""
    if request.headers.get("x-requested-with") != "cgrs":
        raise HTTPException(403, "Requête refusée")
    if db.one("SELECT 1 AS x FROM users LIMIT 1"):
        raise HTTPException(403, "Un compte existe déjà")
    username = clean_username(c.username)
    check_password_rule(c.password)
    uid = db.execute("INSERT INTO users (username, password_hash, role, created) VALUES (?,?,?,?)",
                     (username, hash_password(c.password), "admin", now_iso()))
    start_session(request, response, uid)
    return {"user": {"id": uid, "username": username, "role": "admin"}}


@router.post("/api/auth/login")
def auth_login(c: Credentials, request: Request, response: Response):
    if request.headers.get("x-requested-with") != "cgrs":
        raise HTTPException(403, "Requête refusée")
    username = (c.username or "").strip().lower()
    key = (request.client.host if request.client else "?", username)
    check_rate(key)
    u = db.one("SELECT * FROM users WHERE username=?", (username,))
    ok = verify_password(c.password, u["password_hash"] if u else DUMMY_HASH)
    if not u or not ok:
        register_fail(key)
        raise HTTPException(401, "Identifiant ou mot de passe incorrect")
    FAILS.pop(key, None)
    start_session(request, response, u["id"])
    return {"user": {"id": u["id"], "username": u["username"], "role": u["role"]}}


@router.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    tok = request.cookies.get(COOKIE)
    if tok:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (sha(tok),))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


class PasswordChange(BaseModel):
    current: str
    new: str


@router.post("/api/auth/password")
def auth_password(p: PasswordChange, user: dict = ANY):
    row = db.one("SELECT password_hash FROM users WHERE id=?", (user["id"],))
    if not row or not verify_password(p.current, row["password_hash"]):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    check_password_rule(p.new)
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(p.new), user["id"]))
    return {"ok": True}
