"""Routes d'authentification."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.backend.models.auth import (
    AuthStatus,
    Credentials,
    LoginResponse,
    PasswordChange,
    UserCreate,
    UserEdit,
    UserOut,
)
from src.backend.utils import (
    ADMIN,
    ANY,
    check_password_rule,
    clean_username,
    current_user,
    DUMMY_HASH,
    hash_password,
    log_action,
    now_iso,
    register_fail,
    check_rate,
    start_session,
    verify_password,
    admin_count,
)
from src.backend.db import one, execute, rows

router = APIRouter(prefix="/api/auth", tags=["Authentification"])


@router.get("/status", response_model=AuthStatus)
async def auth_status(request: Request):
    """Retourne le statut d'authentification."""
    return {
        "setup_needed": not one("SELECT 1 AS x FROM users LIMIT 1"),
        "user": current_user(request)
    }


@router.post("/setup", response_model=LoginResponse)
async def auth_setup(
    credentials: Credentials,
    request: Request,
    response: Response
):
    """Création du premier compte (administrateur).
    
    Possible uniquement tant qu'aucun utilisateur n'existe.
    """
    if request.headers.get("x-requested-with") != "cgrs":
        raise HTTPException(403, "Requête refusée")
    if one("SELECT 1 AS x FROM users LIMIT 1"):
        raise HTTPException(403, "Un compte existe déjà")
    username = clean_username(credentials.username)
    check_password_rule(credentials.password)
    uid = execute(
        "INSERT INTO users (username, password_hash, role, created) VALUES (?,?,?,?)",
        (username, hash_password(credentials.password), "admin", now_iso())
    )
    start_session(request, response, uid)
    return {"user": {"id": uid, "username": username, "role": "admin", "created": now_iso()}}


@router.post("/login", response_model=LoginResponse)
async def auth_login(
    credentials: Credentials,
    request: Request,
    response: Response
):
    """Connexion d'un utilisateur."""
    if request.headers.get("x-requested-with") != "cgrs":
        raise HTTPException(403, "Requête refusée")
    username = (credentials.username or "").strip().lower()
    key = (request.client.host if request.client else "?", username)
    check_rate(key)
    u = one("SELECT * FROM users WHERE username=?", (username,))
    ok = verify_password(credentials.password, u["password_hash"] if u else DUMMY_HASH)
    if not u or not ok:
        register_fail(key)
        raise HTTPException(401, "Identifiant ou mot de passe incorrect")
    from src.backend.utils import FAILS
    FAILS.pop(key, None)
    start_session(request, response, u["id"])
    return {"user": {"id": u["id"], "username": u["username"], "role": u["role"], "created": u["created"]}}


@router.post("/logout")
async def auth_logout(
    request: Request,
    response: Response
):
    """Déconnexion d'un utilisateur."""
    tok = request.cookies.get("cgrs_session")
    if tok:
        execute("DELETE FROM sessions WHERE token_hash=?", (sha(tok),))
    response.delete_cookie("cgrs_session", path="/")
    return {"ok": True}


@router.post("/password")
async def auth_password(
    password_change: PasswordChange,
    user: dict = Depends(ANY)
):
    """Changement de mot de passe."""
    row = one("SELECT password_hash FROM users WHERE id=?", (user["id"],))
    if not row or not verify_password(password_change.current, row["password_hash"]):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    check_password_rule(password_change.new)
    execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (hash_password(password_change.new), user["id"])
    )
    return {"ok": True}
