"""Mots de passe, sessions, profils et contrôle des droits (dépendances FastAPI)."""

import hashlib
import hmac
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response

import db
from cgrs.utils import now_iso


COOKIE = "cgrs_session"
SESSION_DAYS = 30
PBKDF_ITERS = 240_000


def hash_password(pw: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), PBKDF_ITERS)
    return f"pbkdf2_sha256${PBKDF_ITERS}${salt}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, it, salt, h = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it))
        return hmac.compare_digest(dk.hex(), h)
    except Exception:
        return False


DUMMY_HASH = hash_password("dummy-password")  # pour un temps de réponse identique si l'identifiant n'existe pas


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def current_user(request: Request):
    tok = request.cookies.get(COOKIE)
    if not tok:
        return None
    return db.one(
        "SELECT u.id, u.username, u.role FROM sessions s JOIN users u ON u.id=s.user_id "
        "WHERE s.token_hash=? AND s.expires > ?", (sha(tok), now_iso()))


def need(*roles):
    def dep(request: Request):
        # protection CSRF : les requêtes qui modifient des données doivent porter cet en-tête personnalisé
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("x-requested-with") != "cgrs":
            raise HTTPException(403, "Requête refusée")
        u = current_user(request)
        if not u:
            raise HTTPException(401, "Connexion requise")
        if u["role"] not in roles:
            raise HTTPException(403, "Droits insuffisants")
        return u
    return Depends(dep)


READ = need("admin", "editor", "reader")   # lecture de toutes les données
EDIT = need("admin", "editor")             # saisie et modification des données
WRITE = EDIT
ADMIN = need("admin")                      # utilisateurs, paramètres, engagements, sauvegarde, mots-clés / regex des fournisseurs
ANY = need("admin", "editor", "reader", "stats")   # page statistiques (prix masqués pour « stats »)

FAILS: dict = {}


def check_rate(key):
    f = FAILS.get(key)
    if f and f["until"] > time.time():
        raise HTTPException(429, f"Trop de tentatives, réessayez dans {int(f['until'] - time.time()) + 1} s")


def register_fail(key):
    f = FAILS.setdefault(key, {"n": 0, "until": 0})
    f["n"] += 1
    if f["n"] >= 5:
        f["until"], f["n"] = time.time() + 60, 0


USERNAME_RE = re.compile(r"^[a-z0-9._@-]{3,40}$")


def clean_username(u: str) -> str:
    u = (u or "").strip().lower()
    if not USERNAME_RE.match(u):
        raise HTTPException(400, "Identifiant : 3 à 40 caractères (lettres, chiffres, . _ - @)")
    return u


def check_password_rule(pw: str):
    if len(pw or "") < 8:
        raise HTTPException(400, "Le mot de passe doit faire au moins 8 caractères")


def start_session(request: Request, response: Response, user_id: int):
    token = secrets.token_urlsafe(32)
    db.execute("DELETE FROM sessions WHERE expires <= ?", (now_iso(),))
    expires = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds")
    db.execute("INSERT INTO sessions (token_hash, user_id, expires) VALUES (?,?,?)", (sha(token), user_id, expires))
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https", path="/")
