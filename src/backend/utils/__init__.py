"""Utilitaires de l'application CGRS.

Ce module contient des fonctions utilitaires communes utilisées dans toute l'application.
"""

import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, Request, Response

from src.backend.config import settings


def now_iso() -> str:
    """Retourne la date et l'heure actuelles au format ISO sans timezone."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def sha(s: str) -> str:
    """Calcule le hash SHA-256 d'une chaîne."""
    return hashlib.sha256(s.encode()).hexdigest()


def hash_password(pw: str) -> str:
    """Hache un mot de passe avec PBKDF2."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        pw.encode(),
        bytes.fromhex(salt),
        settings.PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${settings.PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    """Vérifie un mot de passe contre un hash stocké."""
    try:
        _, it, salt, h = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            pw.encode(),
            bytes.fromhex(salt),
            int(it)
        )
        return hmac.compare_digest(dk.hex(), h)
    except Exception:
        return False


# Hash factice pour un temps de réponse identique si l'identifiant n'existe pas
DUMMY_HASH = hash_password("dummy-password")

# Expression régulière pour la validation des noms d'utilisateur
USERNAME_RE = re.compile(r"^[a-z0-9._@-]{3,40}$")


def clean_username(u: str) -> str:
    """Nettoie et valide un nom d'utilisateur."""
    u = (u or "").strip().lower()
    if not USERNAME_RE.match(u):
        raise HTTPException(
            400,
            "Identifiant : 3 à 40 caractères (lettres, chiffres, . _ - @)"
        )
    return u


def check_password_rule(pw: str) -> None:
    """Vérifie que le mot de passe respecte les règles de sécurité."""
    if len(pw or "") < 8:
        raise HTTPException(400, "Le mot de passe doit faire au moins 8 caractères")


# Dictionnaire pour suivre les tentatives de connexion échouées
FAILS: dict[str, dict] = {}


def check_rate(key: str) -> None:
    """Vérifie si une clé a dépassé le taux de tentatives autorisées."""
    f = FAILS.get(key)
    if f and f["until"] > time.time():
        remaining = int(f["until"] - time.time()) + 1
        raise HTTPException(429, f"Trop de tentatives, réessayez dans {remaining} s")


def register_fail(key: str) -> None:
    """Enregistre une tentative de connexion échouée."""
    f = FAILS.setdefault(key, {"n": 0, "until": 0})
    f["n"] += 1
    if f["n"] >= settings.MAX_LOGIN_ATTEMPTS:
        f["until"], f["n"] = time.time() + settings.LOGIN_LOCKOUT_DURATION, 0


def start_session(request: Request, response: Response, user_id: int) -> None:
    """Démarre une nouvelle session utilisateur."""
    token = secrets.token_urlsafe(32)
    execute("DELETE FROM sessions WHERE expires <= ?", (now_iso(),))
    expires = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        + timedelta(days=settings.SESSION_EXPIRY_DAYS)
    ).isoformat(timespec="seconds")
    execute(
        "INSERT INTO sessions (token_hash, user_id, expires) VALUES (?,?,?)",
        (sha(token), user_id, expires)
    )
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        token,
        max_age=settings.SESSION_EXPIRY_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/"
    )


# Constantes pour les rôles et permissions
PROVENANCES = {
    "cc_nozay": "CC Nozay",
    "loire_atlantique": "Loire-Atlantique",
    "pays_loire": "Pays de la Loire et limitrophes",
    "france": "France",
    "ue": "Union européenne",
    "international": "International",
}
LOCAL = ("cc_nozay", "loire_atlantique", "pays_loire")
GAMMES = {
    "1": "1 - frais et brut",
    "2": "2 - conserves",
    "3": "3 - surgelés",
    "4": "4 - cru prêt à l'emploi",
    "5": "5 - cuit sous vide",
    "6": "6 - déshydratés ou lyophilisés",
}
CATEGORIES = [
    "Fruits: pommes, poires, kiwis", "Fruits: autres", "Légumes", "Viande de porc", "Viande de volaille", "Viande de boeuf",
    "Produits de la pêche", "Produits laitiers", "Ovoproduits", "Épicerie: légumineuses", "Épicerie: céréales", "Épicerie: autre", "Pain", "Autre",
]
DAYS = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
ORDER_METHODS = {"internet": "Internet", "telephone": "Téléphone", "email": "E-mail", "autre": "Autre"}
ROLES = {
    "admin": "Administrateur (tous les droits)",
    "editor": "Lecture et modification",
    "reader": "Lecture seule",
    "stats": "Statistiques uniquement",
}
KINDS = ("livraison", "facture")


# Unités de conversion
UNITS = {
    "kg": ("mass", 1), "g": ("mass", 0.001),
    "l": ("vol", 1), "litre": ("vol", 1), "litres": ("vol", 1), "ml": ("vol", 0.001), "cl": ("vol", 0.01), "dl": ("vol", 0.1),
    "unité": ("count", 1), "unités": ("count", 1), "pièce": ("count", 1), "pièces": ("count", 1), "u": ("count", 1), "pc": ("count", 1),
    "colis": ("colis", 1), "botte": ("botte", 1), "barquette": ("barquette", 1), "bidon": ("bidon", 1), "boite": ("boite", 1),
}


def unit_info(u: str | None) -> tuple[str, float] | None:
    """Retourne les informations sur une unité."""
    u = (u or "").strip().lower()
    if not u:
        return None
    return UNITS.get(u) or ("x:" + u, 1)


def convert(qty: float | None, from_u: str | None, to_u: str | None) -> float | None:
    """Convertit une quantité d'une unité à l'autre."""
    if qty is None:
        return None
    a, b = unit_info(from_u), unit_info(to_u)
    if a is None or b is None:
        return qty
    if a[0] != b[0]:
        return None
    return qty * a[1] / b[1]


# Fonctions pour la base de données (importées depuis db)
def execute(sql: str, args: tuple = ()) -> int:
    """Exécute une requête SQL et retourne l'ID de la dernière ligne insérée."""
    from src.backend.db import execute as _execute
    return _execute(sql, args)


def rows(sql: str, args: tuple = ()) -> list[dict]:
    """Exécute une requête SQL et retourne tous les résultats."""
    from src.backend.db import rows as _rows
    return _rows(sql, args)


def one(sql: str, args: tuple = ()) -> dict | None:
    """Exécute une requête SQL et retourne le premier résultat."""
    from src.backend.db import one as _one
    return _one(sql, args)


# Fonctions pour le journal d'actions
def log_action(user: dict, action: str, entity: str, entity_id: int, description: str = None) -> None:
    """Enregistre une action dans le journal (action_log)."""
    try:
        execute(
            "INSERT INTO action_log (ts, username, action, entity, entity_id, description) VALUES (?,?,?,?,?,?)",
            (now_iso(), user["username"], action, entity, entity_id, description)
        )
    except Exception:
        pass  # le journal ne doit jamais bloquer une opération


# Dépendances FastAPI pour l'authentification
def current_user(request: Request) -> dict | None:
    """Retourne l'utilisateur actuel à partir du cookie de session."""
    tok = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not tok:
        return None
    return one(
        "SELECT u.id, u.username, u.role FROM sessions s JOIN users u ON u.id=s.user_id "
        "WHERE s.token_hash=? AND s.expires > ?",
        (sha(tok), now_iso())
    )


def need(*roles: str):
    """Crée une dépendance FastAPI pour vérifier les permissions."""
    def dep(request: Request) -> dict:
        # Protection CSRF
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("x-requested-with") != "cgrs":
            raise HTTPException(403, "Requête refusée")
        u = current_user(request)
        if not u:
            raise HTTPException(401, "Connexion requise")
        if u["role"] not in roles:
            raise HTTPException(403, "Droits insuffisants")
        return u
    return dep


# Dépendances pré-définies
READ = need("admin", "editor", "reader")
EDIT = need("admin", "editor")
WRITE = EDIT
ADMIN = need("admin")
ANY = need("admin", "editor", "reader", "stats")


# Utilitaires pour les modèles
def fields(model: Any, exclude: tuple = ()) -> tuple[list, list]:
    """Extrait les champs et valeurs d'un modèle Pydantic."""
    d = model.model_dump(exclude=set(exclude))
    vals = [json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v for v in d.values()]
    return list(d.keys()), vals


def insert(table: str, model: Any, exclude: tuple = ()) -> int:
    """Insère un modèle dans une table."""
    cols, vals = fields(model, exclude)
    return execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)


def update(table: str, id_: int, model: Any, exclude: tuple = ()) -> None:
    """Met à jour un modèle dans une table."""
    cols, vals = fields(model, exclude)
    execute(f"UPDATE {table} SET {','.join(c + '=?' for c in cols)} WHERE id=?", vals + [id_])


# Métriques
def metric_options() -> list[tuple]:
    """Retourne les options de métriques disponibles."""
    opts = [
        ("bio", "% bio"),
        ("egalim", "% EGalim"),
        ("local", "% local (CC Nozay, 44, Pays de la Loire)"),
        ("direct", "% direct producteur"),
        ("price_per_meal", "Prix / repas HT (€) – coût matières ÷ convives"),
    ]
    opts += [(f"label:{k}", f"% label : {v}") for k, v in (("bio", "bio"), ("autre", "autre label"), ("sans", "sans label"))]
    opts += [(f"provenance:{k}", f"% provenance : {v}") for k, v in PROVENANCES.items()]
    opts += [(f"gamme:{k}", f"% gamme : {v}") for k, v in GAMMES.items()]
    return opts


# Constantes pour les cookies et sessions
COOKIE = "cgrs_session"

# Compteur d'administrateurs
def admin_count() -> int:
    """Retourne le nombre d'administrateurs."""
    return one("SELECT COUNT(*) AS n FROM users WHERE role='admin'")["n"]


def load_history() -> dict:
    """Charge l'historique des prix depuis la base de données."""
    rows_ = rows("SELECT product_id, date, price, unit FROM price_history ORDER BY product_id, date")
    hist = {}
    for r in rows_:
        hist.setdefault(r["product_id"], []).append(r)
    return hist


def price_at(hist: dict, product_id: int, date: str, default_price: float | None = None) -> float | None:
    """Retourne le prix d'un produit à une date donnée."""
    if product_id not in hist:
        return default_price
    prices = hist[product_id]
    # Trouver le prix le plus récent avant ou à la date donnée
    best = None
    for p in prices:
        if p["date"] <= date:
            if best is None or p["date"] > best["date"]:
                best = p
    return best["price"] if best else default_price
