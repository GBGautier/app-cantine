"""Assistant IA : réglages (clé API gratuite), chat intégré et serveur MCP (jetons d'accès)."""

import secrets
import time
from collections import defaultdict, deque
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from cgrs import db
from cgrs.assistant import chat, llm, mcp
from cgrs.assistant.llm import PROVIDERS, ErreurModele
from cgrs.security import ADMIN, READ, check_rate, register_fail, sha
from cgrs.utils import log_action, now_iso


router = APIRouter()
TOKEN_PREFIX = "cgrs_"
RECENT: dict = defaultdict(deque)  # horodatages des messages du chat par utilisateur
MAX_PAR_MINUTE = 20  # protège le quota gratuit du fournisseur


def _save(cle, valeur):
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (cle, valeur),
    )


# ---------- réglages (administrateur) ----------
class Config(BaseModel):
    fournisseur: str
    modele: Optional[str] = None
    cle: Optional[str] = None  # vide : on garde la clé enregistrée


@router.get("/api/assistant/config")
def get_config(user: dict = ADMIN):
    c = llm.lire_config()
    return {
        "fournisseurs": {k: {"nom": v["nom"], "modele": v["modele"], "cle": v["cle"]} for k, v in PROVIDERS.items()},
        "fournisseur": c["fournisseur"],
        "modele": c["modele"],
        "cle_definie": bool(c["cle"]),
        "cle_fin": ("…" + c["cle"][-4:]) if len(c["cle"]) >= 8 else "",
    }


@router.put("/api/assistant/config")
def put_config(c: Config, user: dict = ADMIN):
    if c.fournisseur not in PROVIDERS:
        raise HTTPException(400, "Fournisseur inconnu")
    modele = (c.modele or "").strip()
    if len(modele) > 80 or any(ch.isspace() for ch in modele):
        raise HTTPException(400, "Nom de modèle invalide")
    _save("assistant_provider", c.fournisseur)
    _save("assistant_model", modele)
    if c.cle and c.cle.strip():
        cle = c.cle.strip()
        if len(cle) < 8 or any(ch.isspace() for ch in cle):
            raise HTTPException(400, "Clé API invalide")
        _save("assistant_key", cle)
    log_action(
        user, "update", "settings", None, f"Assistant IA : {PROVIDERS[c.fournisseur]['nom']} (clé non journalisée)"
    )
    return {"ok": True}


@router.delete("/api/assistant/config/cle")
def delete_cle(user: dict = ADMIN):
    _save("assistant_key", "")
    log_action(user, "update", "settings", None, "Assistant IA : clé API supprimée")
    return {"ok": True}


@router.post("/api/assistant/test")
def test_connexion(user: dict = ADMIN):
    try:
        r = llm.appeler([{"role": "user", "content": "Réponds uniquement : OK"}])
    except ErreurModele as e:
        raise HTTPException(502, str(e)) from e
    return {"ok": True, "reponse": (r.get("content") or "")[:100]}


# ---------- chat intégré ----------
@router.get("/api/assistant/etat")
def etat(user: dict = READ):
    c = llm.lire_config()
    return {
        "configure": llm.est_configure(),
        "fournisseur": PROVIDERS.get(c["fournisseur"], {}).get("nom", ""),
        "peut_ecrire": user["role"] in ("admin", "editor"),
    }


class Conversation(BaseModel):
    messages: list = []
    decisions: dict[str, bool] = {}


@router.post("/api/assistant/chat")
def converser(c: Conversation, user: dict = READ):
    if not llm.est_configure():
        raise HTTPException(
            409, "L'assistant n'est pas configuré : un administrateur doit saisir une clé API (Paramètres)."
        )
    f = RECENT[user["username"]]
    now = time.time()
    while f and f[0] < now - 60:
        f.popleft()
    if len(f) >= MAX_PAR_MINUTE:
        raise HTTPException(429, "Trop de messages à la suite : patientez une minute.")
    f.append(now)
    try:
        return chat.converser(user, c.messages, c.decisions)
    except ErreurModele as e:
        raise HTTPException(502, str(e)) from e


# ---------- jetons du serveur MCP (administrateur) ----------
class Jeton(BaseModel):
    nom: str
    droits: str = "reader"  # reader | editor


@router.get("/api/assistant/jetons")
def liste_jetons(user: dict = ADMIN):
    return db.rows("SELECT id, name, role, created, last_used FROM assistant_tokens ORDER BY id DESC")


@router.post("/api/assistant/jetons")
def creer_jeton(j: Jeton, user: dict = ADMIN):
    nom = j.nom.strip()
    if not nom or len(nom) > 60:
        raise HTTPException(400, "Nom du jeton : 1 à 60 caractères")
    if j.droits not in ("reader", "editor"):
        raise HTTPException(400, "Droits : reader (lecture) ou editor (lecture et écriture)")
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    jid = db.execute(
        "INSERT INTO assistant_tokens (name, token_hash, role, created) VALUES (?,?,?,?)",
        (nom, sha(token), j.droits, now_iso()),
    )
    log_action(user, "create", "settings", jid, f"Jeton MCP créé : {nom!r} ({j.droits})")
    return {"id": jid, "jeton": token}  # affiché une seule fois : seule l'empreinte est conservée


@router.delete("/api/assistant/jetons/{id}")
def supprimer_jeton(id: int, user: dict = ADMIN):
    db.execute("DELETE FROM assistant_tokens WHERE id=?", (id,))
    log_action(user, "delete", "settings", id, "Jeton MCP supprimé")
    return {"ok": True}


# ---------- serveur MCP ----------
def _non_autorise():
    return JSONResponse(
        {"error": "Jeton d'accès manquant ou invalide"},
        status_code=401,
        headers={"WWW-Authenticate": 'Bearer realm="cantine"'},
    )


@router.post("/mcp")
async def mcp_endpoint(request: Request):
    """Point d'entrée MCP (Streamable HTTP). Authentification par jeton « Authorization: Bearer … » (pas de cookie)."""
    origin = request.headers.get("origin")
    if origin and urlparse(origin).netloc != request.headers.get("host"):
        raise HTTPException(403, "Origine refusée")  # un site web tiers ne doit pas pouvoir appeler ce point d'entrée
    ip = request.client.host if request.client else "?"
    check_rate(("mcp", ip))
    auth = request.headers.get("authorization", "")
    tok = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    row = db.one("SELECT id, name, role FROM assistant_tokens WHERE token_hash=?", (sha(tok),)) if tok else None
    if not row:
        register_fail(("mcp", ip))
        return _non_autorise()
    db.execute("UPDATE assistant_tokens SET last_used=? WHERE id=?", (now_iso(), row["id"]))
    user = {
        "id": None,
        "username": "assistant:" + row["name"],
        "role": "editor" if row["role"] == "editor" else "reader",
    }
    try:
        corps = await request.json()
    except ValueError:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON invalide"}}, status_code=400
        )
    if isinstance(corps, list):
        reponses = [r for r in (mcp.traiter(m, user) for m in corps) if r is not None]
        return JSONResponse(reponses) if reponses else Response(status_code=202)
    rep = mcp.traiter(corps, user)
    return JSONResponse(rep) if rep is not None else Response(status_code=202)


@router.get("/mcp")
def mcp_get():
    return Response(status_code=405, headers={"Allow": "POST"})  # pas de flux serveur → client (SSE) : POST uniquement
