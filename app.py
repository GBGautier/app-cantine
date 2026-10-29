import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import tempfile
import time
import zipfile
from datetime import date as date_cls, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from starlette.background import BackgroundTask

import db
import dolibarr
import pdf_parser
import menu_parser

db.init()
app = FastAPI(title="CGRS – réceptions & stocks")

import paths
STATIC = paths.STATIC
UPLOADS = paths.UPLOADS   # deja cree par paths.py

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


# =====================================================================================
#  Identification et droits
# =====================================================================================
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


class Credentials(BaseModel):
    username: str
    password: str


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


@app.get("/api/auth/status")
def auth_status(request: Request):
    return {"setup_needed": not db.one("SELECT 1 AS x FROM users LIMIT 1"), "user": current_user(request)}


@app.post("/api/auth/setup")
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


@app.post("/api/auth/login")
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


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    tok = request.cookies.get(COOKIE)
    if tok:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (sha(tok),))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


class PasswordChange(BaseModel):
    current: str
    new: str


@app.post("/api/auth/password")
def auth_password(p: PasswordChange, user: dict = ANY):
    row = db.one("SELECT password_hash FROM users WHERE id=?", (user["id"],))
    if not row or not verify_password(p.current, row["password_hash"]):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    check_password_rule(p.new)
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(p.new), user["id"]))
    return {"ok": True}


class NewUser(BaseModel):
    username: str
    password: str
    role: str


class UserEdit(BaseModel):
    role: Optional[str] = None
    password: Optional[str] = None


def admin_count():
    return db.one("SELECT COUNT(*) AS n FROM users WHERE role='admin'")["n"]


@app.get("/api/users")
def list_users(user: dict = ADMIN):
    return db.rows("SELECT id, username, role, created FROM users ORDER BY username")


@app.post("/api/users")
def create_user(u: NewUser, user: dict = ADMIN):
    if u.role not in ROLES:
        raise HTTPException(400, "Profil inconnu")
    username = clean_username(u.username)
    check_password_rule(u.password)
    if db.one("SELECT 1 AS x FROM users WHERE username=?", (username,)):
        raise HTTPException(400, "Cet identifiant existe déjà")
    uid = db.execute("INSERT INTO users (username, password_hash, role, created) VALUES (?,?,?,?)",
                     (username, hash_password(u.password), u.role, now_iso()))
    log_action(user, "create", "user", uid, f"Création utilisateur {username!r} ({u.role})")
    return {"id": uid}


@app.put("/api/users/{id}")
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
        db.execute("DELETE FROM sessions WHERE user_id=?", (id,))   # force une nouvelle connexion
    if changes:
        log_action(user, "update", "user", id, f"Modification utilisateur {target['username']!r} : {', '.join(changes)}")
    return {"ok": True}


@app.delete("/api/users/{id}")
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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    if request.url.path.startswith("/api/files/"):
        # PDF affichés dans l'iframe de la visionneuse (même origine) : DENY bloquerait l'affichage
        resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    else:
        resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# =====================================================================================
#  Outils : unités, JSON, enregistrement
# =====================================================================================
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


# =====================================================================================
#  Fichiers (PDF des réceptions, fiches techniques)
# =====================================================================================
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx", ".odt", ".ods", ".txt"}
MAX_UPLOAD = 25 * 1024 * 1024


async def save_upload(file: UploadFile, prefix="", allowed=ALLOWED_EXT) -> str:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Type de fichier non accepté ({ext or 'sans extension'})")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(file.filename).stem)[:80] + ext
    name = f"{prefix}{secrets.token_hex(6)}_{safe}"
    dest = UPLOADS / name
    size = 0
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "Fichier trop volumineux (25 Mo maximum)")
            f.write(chunk)
    return name


# ---------- Export Dolibarr (CSV pour l'assistant d'import) ----------
@app.get("/api/export/dolibarr/suppliers")
def export_dolibarr_suppliers(user: dict = READ):
    return dolibarr.suppliers_csv(db)


@app.get("/api/export/dolibarr/products")
def export_dolibarr_products(user: dict = READ):
    return dolibarr.products_csv(db)


@app.get("/api/export/dolibarr/orders")
def export_dolibarr_orders(user: dict = READ):
    return dolibarr.orders_csv(db)


@app.get("/api/export/dolibarr/meals")
def export_dolibarr_meals(user: dict = READ):
    return dolibarr.meals_csv(db)


@app.get("/api/files/{name}")
def get_file(name: str, user: dict = READ):
    p = UPLOADS / Path(name).name
    if not p.is_file() or p.suffix.lower() not in ALLOWED_EXT:
        raise HTTPException(404, "Fichier introuvable")
    pretty = re.sub(r"^(?:fiche_)?[0-9a-f]{12}_", "", p.name)
    return FileResponse(p, filename=pretty, content_disposition_type="inline")


# =====================================================================================
#  Paramètres, méta
# =====================================================================================
def metric_options():
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


@app.get("/api/meta")
def meta(user: dict = ANY):
    return {"provenances": PROVENANCES, "gammes": GAMMES, "categories": CATEGORIES, "local": LOCAL,
            "metrics": metric_options(), "days": DAYS, "order_methods": ORDER_METHODS, "roles": ROLES}


class Settings(BaseModel):
    client_names: str = ""   # noms de la cantine, séparés par « ; » (jamais pris pour un fournisseur)


def get_client_names():
    r = db.one("SELECT value FROM settings WHERE key='client_names'")
    return [x.strip() for x in (r["value"] if r else "").split(";") if x.strip()]


@app.get("/api/settings")
def get_settings(user: dict = ADMIN):
    return {"client_names": "; ".join(get_client_names())}


@app.put("/api/settings")
def put_settings(s: Settings, user: dict = ADMIN):
    db.execute("INSERT INTO settings (key, value) VALUES ('client_names', ?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (s.client_names,))
    log_action(user, "update", "settings", None, f"Nom de la cantine : {s.client_names!r}")
    return {"ok": True}


# ---------- convives par défaut (repas, recettes, grammages) ----------
class ConvivesDefaults(BaseModel):
    mat: int = 140    # maternelles
    elem: int = 240   # élémentaires
    adu: int = 5      # adultes


@app.get("/api/convives-defaults")
def get_convives_defaults(user: dict = ANY):
    import json
    r = db.one("SELECT value FROM settings WHERE key='convives_defaults'")
    if r and r["value"]:
        try:
            d = json.loads(r["value"])
            return {"mat": int(d.get("mat", 140)), "elem": int(d.get("elem", 240)), "adu": int(d.get("adu", 5))}
        except Exception:
            pass
    return {"mat": 140, "elem": 240, "adu": 5}


@app.put("/api/convives-defaults")
def put_convives_defaults(c: ConvivesDefaults, user: dict = ADMIN):
    import json
    if min(c.mat, c.elem, c.adu) < 0:
        raise HTTPException(400, "Les effectifs ne peuvent pas être négatifs")
    value = json.dumps({"mat": c.mat, "elem": c.elem, "adu": c.adu})
    db.execute("INSERT INTO settings (key, value) VALUES ('convives_defaults', ?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (value,))
    log_action(user, "update", "settings", None, f"Convives par défaut : {value}")
    return {"ok": True}


# ---------- grammages CGRS (overrides) ----------
@app.get("/api/grammages")
def get_grammages(user: dict = ANY):
    r = db.one("SELECT value FROM settings WHERE key='grammages_overrides'")
    try:
        return json.loads(r["value"]) if r else {}
    except Exception:
        return {}


class GrammageOverride(BaseModel):
    overrides: dict  # {"tab__sectionIdx__rowIdx": {"cgrs": ["val","val","val"], "coeff": 1.33}}


# ---------- grammages CGRS (données complètes en base) ----------
class GrammageRow(BaseModel):
    section_key: str = ""
    section_label: str = ""
    section_title: Optional[str] = None
    label: str
    gemrcn: list[str] = []
    cgrs: list[str] = []
    coeff: float = 1
    unit: Optional[str] = None


def grammage_out(r):
    r = dict(r)
    for k in ("gemrcn", "cgrs"):
        try:
            r[k] = json.loads(r[k]) if r.get(k) else []
        except (ValueError, TypeError):
            r[k] = []
    return r


@app.get("/api/grammages-rows")
def get_grammages_rows(user: dict = ANY):
    """Grammages complets (GEMRCN + CGRS + coefficient cru/cuit). Liste vide au premier lancement :
    le navigateur enregistre alors les valeurs par défaut (voir loadGramRows côté client)."""
    return [grammage_out(r) for r in db.rows("SELECT * FROM grammages ORDER BY id")]


class GrammageRowsUpdate(BaseModel):
    rows: list[GrammageRow] = []


@app.put("/api/grammages-rows")
def put_grammages_rows(g: GrammageRowsUpdate, user: dict = EDIT):
    db.execute("DELETE FROM grammages")
    for r in g.rows:
        db.execute(
            "INSERT INTO grammages (section_key, section_label, section_title, label, gemrcn, cgrs, coeff, unit) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (r.section_key, r.section_label, r.section_title, r.label,
             json.dumps(r.gemrcn, ensure_ascii=False), json.dumps(r.cgrs, ensure_ascii=False),
             r.coeff, r.unit))
    log_action(user, "update", "grammages", None, f"{len(g.rows)} lignes de grammages enregistrées")
    return {"ok": True, "rows": len(g.rows)}


@app.put("/api/grammages")
def put_grammages(g: GrammageOverride, user: dict = EDIT):
    db.execute("INSERT INTO settings (key, value) VALUES ('grammages_overrides', ?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (json.dumps(g.overrides, ensure_ascii=False),))
    log_action(user, "update", "settings", None, "Mise à jour des grammages CGRS")
    return {"ok": True}


# ---------- engagements du marché / PAR ----------
class Commitment(BaseModel):
    label: str
    metrics: list[str] = []         # liste d'indicateurs (nouveau)
    metric: str = ""                # conservé pour compat. lecture (écrasé par metrics à l'enregistrement)
    categories: list[str] = []      # liste de catégories (nouveau)
    category: Optional[str] = None  # conservé pour compat. lecture
    gammes: list[str] = []          # liste de gammes filtrées (optionnel)
    target: float
    mode: str = "min"
    level: str = "marche"           # marche | par
    notes: Optional[str] = None


def commitment_out(c):
    c = dict(c)
    for k in ("metrics", "categories", "gammes"):
        try:
            c[k] = json.loads(c[k]) if c.get(k) else []
        except (ValueError, TypeError):
            c[k] = []
    if not c["metrics"] and c.get("metric"):
        c["metrics"] = [c["metric"]]
    if not c["categories"] and c.get("category"):
        c["categories"] = [c["category"]]
    return c


@app.get("/api/commitments")
def commitments(user: dict = READ):
    return [commitment_out(r) for r in db.rows("SELECT * FROM commitments ORDER BY id")]


@app.post("/api/commitments")
def create_commitment(c: Commitment, user: dict = ADMIN):
    return {"id": insert("commitments", c)}


@app.put("/api/commitments/{id}")
def edit_commitment(id: int, c: Commitment, user: dict = ADMIN):
    update("commitments", id, c)
    return {"ok": True}


@app.delete("/api/commitments/{id}")
def delete_commitment(id: int, user: dict = ADMIN):
    db.execute("DELETE FROM commitments WHERE id=?", (id,))
    return {"ok": True}


def seed_commitments():
    if not db.one("SELECT 1 AS x FROM commitments LIMIT 1"):
        db.execute("INSERT INTO commitments (label, metric, target, mode) VALUES ('Produits bio', 'bio', 85, 'min')")
        db.execute("INSERT INTO commitments (label, metric, target, mode) VALUES ('Produits EGalim', 'egalim', 90, 'min')")


# =====================================================================================
#  Fournisseurs
# =====================================================================================
class Supplier(BaseModel):
    name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    siret: Optional[str] = None
    delivery_days: list[str] = []
    franco: Optional[float] = None
    order_method: Optional[str] = None
    order_url: Optional[str] = None
    categories: list[str] = []
    local_default: Optional[str] = None
    direct_producteur: int = 0
    parser_regex: Optional[str] = None
    keywords: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("order_url")
    @classmethod
    def url_ok(cls, v):
        if v and not re.match(r"^https?://", v.strip(), re.I):
            raise ValueError("Le lien de commande doit commencer par http:// ou https://")
        return v.strip() if v else v

    @field_validator("delivery_days")
    @classmethod
    def days_ok(cls, v):
        return [d for d in v if d in DAYS]


def supplier_out(r):
    for k in ("delivery_days", "categories"):
        try:
            r[k] = json.loads(r[k]) if r.get(k) else []
        except ValueError:
            r[k] = []
    return r


@app.get("/api/suppliers")
def suppliers(user: dict = READ):
    out = [supplier_out(r) for r in db.rows(
        "SELECT s.*, (SELECT COUNT(*) FROM products p WHERE p.supplier_id=s.id) AS nb_products, "
        "(SELECT COUNT(*) FROM orders o WHERE o.supplier_id=s.id) AS nb_orders "
        "FROM suppliers s ORDER BY s.name")]
    if user["role"] != "admin":   # mots-clés de reconnaissance et regex de lecture : réservés à l'administrateur
        for r in out:
            r.pop("keywords", None)
            r.pop("parser_regex", None)
    return out


@app.post("/api/suppliers")
def create_supplier(s: Supplier, user: dict = WRITE):
    if user["role"] != "admin":
        s.keywords = s.parser_regex = None
    return {"id": insert("suppliers", s)}


@app.put("/api/suppliers/{id}")
def edit_supplier(id: int, s: Supplier, user: dict = WRITE):
    old = db.one("SELECT direct_producteur, keywords, parser_regex FROM suppliers WHERE id=?", (id,))
    if user["role"] != "admin" and old:   # ces deux champs ne sont pas modifiables hors administrateur
        s.keywords, s.parser_regex = old["keywords"], old["parser_regex"]
    update("suppliers", id, s)
    if s.direct_producteur and old and not old["direct_producteur"]:   # fournisseur désormais « direct producteur » : ses produits aussi
        db.execute("UPDATE products SET direct_producteur=1 WHERE supplier_id=?", (id,))
    return {"ok": True}


@app.delete("/api/suppliers/{id}")
def delete_supplier(id: int, user: dict = WRITE):
    db.execute("DELETE FROM suppliers WHERE id=?", (id,))
    return {"ok": True}


# =====================================================================================
#  Produits, fiches techniques, historique des prix
# =====================================================================================
class Product(BaseModel):
    ref: Optional[str] = None
    name: str
    supplier_id: Optional[int] = None
    category: Optional[str] = None
    gamme: Optional[str] = None
    label_egalim: str = "bio"
    label_detail: Optional[str] = None
    provenance: Optional[str] = None
    direct_producteur: int = 0
    avoid: int = 0            # « à éviter » : produit signalé (affiché en orange dans la liste)
    favorite: int = 0         # produit favori (étoile)
    unit: Optional[str] = "kg"
    unit_price: Optional[float] = None
    notes: Optional[str] = None


def add_history(product_id, day, price, unit, order_id, source):
    db.execute("INSERT INTO price_history (product_id, date, price, unit, order_id, source) VALUES (?,?,?,?,?,?)",
               (product_id, day, price, unit, order_id, source))


def refresh_product_price(product_id):
    """Le prix courant d'un produit = dernier prix de son historique."""
    last = db.one("SELECT price FROM price_history WHERE product_id=? ORDER BY date DESC, id DESC LIMIT 1", (product_id,))
    if last:
        db.execute("UPDATE products SET unit_price=? WHERE id=?", (last["price"], product_id))


@app.get("/api/products")
def products(user: dict = READ):
    return db.rows(
        "SELECT p.*, s.name AS supplier_name FROM products p "
        "LEFT JOIN suppliers s ON s.id=p.supplier_id ORDER BY p.name")


def fill_unpriced_lines(product_id):
    """Un prix saisi sur la fiche produit complète les lignes de réception restées sans prix (bon de livraison importé
    sans prix). Les lignes déjà chiffrées ne bougent pas : un changement de prix ne réécrit jamais les anciennes factures."""
    p = db.one("SELECT unit, unit_price FROM products WHERE id=?", (product_id,))
    if not p or not p["unit_price"]:
        return
    touched = set()
    for l in db.rows("SELECT id, order_id, qty, unit FROM order_lines WHERE product_id=? AND (unit_price IS NULL OR unit_price=0) "
                     "AND (total_ht IS NULL OR total_ht=0) AND qty > 0", (product_id,)):
        q = convert(l["qty"], l["unit"] or p["unit"], p["unit"] or l["unit"])
        if q is None:
            continue
        price_line = round(p["unit_price"] * q / l["qty"], 4)
        db.execute("UPDATE order_lines SET unit_price=?, total_ht=? WHERE id=?", (price_line, round(q * p["unit_price"], 2), l["id"]))
        touched.add(l["order_id"])
    for oid in touched:   # total de la réception : recalculé seulement s'il était vide ou égal à la somme des lignes
        o = db.one("SELECT total_ht FROM orders WHERE id=?", (oid,))
        s_all = db.one("SELECT COALESCE(SUM(total_ht),0) AS s FROM order_lines WHERE order_id=?", (oid,))["s"]
        if not o["total_ht"]:
            db.execute("UPDATE orders SET total_ht=? WHERE id=?", (round(s_all, 2), oid))


@app.post("/api/products")
def create_product(p: Product, user: dict = WRITE):
    pid = insert("products", p)
    if p.unit_price is not None:
        add_history(pid, date_cls.today().isoformat(), p.unit_price, p.unit, None, "manuel")
        fill_unpriced_lines(pid)
    return {"id": pid}


@app.put("/api/products/{id}")
def edit_product(id: int, p: Product, user: dict = WRITE):
    old = db.one("SELECT unit_price FROM products WHERE id=?", (id,))
    if not old:
        raise HTTPException(404)
    update("products", id, p)
    if p.unit_price is not None and (old["unit_price"] is None or abs(old["unit_price"] - p.unit_price) > 1e-9):
        add_history(id, date_cls.today().isoformat(), p.unit_price, p.unit, None, "manuel")
    fill_unpriced_lines(id)
    return {"ok": True}


@app.delete("/api/products/{id}")
def delete_product(id: int, user: dict = WRITE):
    db.execute("DELETE FROM products WHERE id=?", (id,))
    return {"ok": True}


@app.post("/api/products/{id}/favorite")
def toggle_favorite(id: int, user: dict = WRITE):
    """Bascule l'étoile « favori » d'un produit, sans passer par la fiche complète."""
    p = db.one("SELECT id FROM products WHERE id=?", (id,))
    if not p:
        raise HTTPException(404)
    db.execute("UPDATE products SET favorite = 1 - COALESCE(favorite, 0) WHERE id=?", (id,))
    return {"favorite": db.one("SELECT favorite FROM products WHERE id=?", (id,))["favorite"]}


@app.get("/api/products/{id}/prices")
def product_prices(id: int, user: dict = READ):
    return db.rows(
        "SELECT h.id, h.date, h.price, h.unit, h.source, o.ref AS order_ref, o.kind AS order_kind "
        "FROM price_history h LEFT JOIN orders o ON o.id=h.order_id WHERE h.product_id=? "
        "ORDER BY h.date DESC, h.id DESC", (id,))


@app.get("/api/products/prices-at")
def prices_at_date(date: str, user: dict = READ):
    """Prix de tous les produits à une date donnée (dernier relevé ≤ date)."""
    hist = load_history()
    prods = db.rows("SELECT id, unit_price FROM products")
    return {str(p["id"]): price_at(hist, p["id"], date, p["unit_price"]) for p in prods}


@app.post("/api/products/{id}/datasheet")
async def upload_datasheet(id: int, file: UploadFile = File(...), user: dict = WRITE):
    if not db.one("SELECT 1 AS x FROM products WHERE id=?", (id,)):
        raise HTTPException(404)
    name = await save_upload(file, prefix="fiche_")
    db.execute("UPDATE products SET datasheet=? WHERE id=?", (name, id))
    return {"datasheet": name}


@app.post("/api/orders/{id}/upload-pdf")
async def upload_order_pdf(id: int, file: UploadFile = File(...), user: dict = WRITE):
    """Attache un PDF (BL ou facture) à une réception existante."""
    if not db.one("SELECT 1 AS x FROM orders WHERE id=?", (id,)):
        raise HTTPException(404)
    name = await save_upload(file, allowed={".pdf"})
    # Suppression de l'ancien fichier s'il existait
    old = db.one("SELECT source_file FROM orders WHERE id=?", (id,))
    if old and old["source_file"]:
        (UPLOADS / Path(old["source_file"]).name).unlink(missing_ok=True)
    db.execute("UPDATE orders SET source_file=? WHERE id=?", (name, id))
    return {"source_file": name}


@app.delete("/api/orders/{id}/upload-pdf")
def delete_order_pdf(id: int, user: dict = WRITE):
    """Supprime le PDF attaché à une réception."""
    r = db.one("SELECT source_file FROM orders WHERE id=?", (id,))
    if not r:
        raise HTTPException(404)
    if r["source_file"]:
        (UPLOADS / Path(r["source_file"]).name).unlink(missing_ok=True)
    db.execute("UPDATE orders SET source_file=NULL WHERE id=?", (id,))
    return {"ok": True}


@app.delete("/api/products/{id}/datasheet")
def delete_datasheet(id: int, user: dict = WRITE):
    r = db.one("SELECT datasheet FROM products WHERE id=?", (id,))
    if r and r["datasheet"]:
        (UPLOADS / Path(r["datasheet"]).name).unlink(missing_ok=True)
    db.execute("UPDATE products SET datasheet=NULL WHERE id=?", (id,))
    return {"ok": True}


# =====================================================================================
#  Réceptions : bons de livraison (provisoires) et factures (définitives)
# =====================================================================================
class Line(BaseModel):
    create_product: bool = False   # créer le produit à partir du libellé s'il n'existe pas
    product_id: Optional[int] = None
    ref: Optional[str] = None
    label: Optional[str] = None
    qty: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total_ht: Optional[float] = None


class Order(BaseModel):
    supplier_id: Optional[int] = None
    ref: Optional[str] = None
    kind: str = "livraison"
    date: Optional[str] = None
    total_ht: Optional[float] = None
    source_file: Optional[str] = None
    notes: Optional[str] = None
    new_supplier_name: Optional[str] = None   # créer le fournisseur s'il n'existe pas
    new_supplier_direct: bool = False         # … et le marquer « direct producteur » (ses produits le seront aussi)
    replaces: list[int] = []                  # bons de livraison remplacés par cette facture
    lines: list[Line] = []


def ref_key(s):
    k = re.sub(r"[^A-Z0-9]", "", (s or "").upper())
    return re.sub(r"^(?:BL|BC|FAC|FA|FC)", "", k)


@app.get("/api/orders")
def orders(user: dict = READ):
    return db.rows(
        "SELECT o.*, s.name AS supplier_name, "
        "(SELECT COUNT(*) FROM order_lines l WHERE l.order_id=o.id) AS nb_lines "
        "FROM orders o LEFT JOIN suppliers s ON s.id=o.supplier_id ORDER BY o.date DESC, o.id DESC")


@app.get("/api/orders/{id}")
def get_order(id: int, user: dict = READ):
    o = db.one("SELECT * FROM orders WHERE id=?", (id,))
    if not o:
        raise HTTPException(404)
    o["lines"] = db.rows(
        "SELECT l.*, p.name AS product_name FROM order_lines l "
        "LEFT JOIN products p ON p.id=l.product_id WHERE l.order_id=? ORDER BY l.id", (id,))
    return o


def save_lines(order_id, lines):
    for l in lines:
        total = l.total_ht
        if total is None and l.qty is not None and l.unit_price is not None:
            total = round(l.qty * l.unit_price, 2)
        db.execute(
            "INSERT INTO order_lines (order_id, product_id, ref, label, qty, unit, unit_price, total_ht) VALUES (?,?,?,?,?,?,?,?)",
            (order_id, l.product_id, l.ref, l.label, l.qty, l.unit, l.unit_price, total))


def order_total(o: Order):
    if o.total_ht is not None:
        return o.total_ht
    return round(sum((l.total_ht if l.total_ht is not None else (l.qty or 0) * (l.unit_price or 0)) for l in o.lines), 2)


def resolve_creations(o: Order):
    """Crée (ou retrouve) le fournisseur et les produits demandés ; rattache les lignes par référence connue."""
    created = {"supplier": None, "products": []}
    if o.supplier_id is None and (o.new_supplier_name or "").strip():
        name = o.new_supplier_name.strip()
        found = db.one("SELECT id FROM suppliers WHERE LOWER(name)=LOWER(?)", (name,))
        if found:
            o.supplier_id = found["id"]
        else:
            o.supplier_id = db.execute("INSERT INTO suppliers (name, direct_producteur) VALUES (?,?)", (name, 1 if o.new_supplier_direct else 0))
            created["supplier"] = name
    sup = db.one("SELECT * FROM suppliers WHERE id=?", (o.supplier_id,)) if o.supplier_id else None
    for l in o.lines:
        if l.product_id is not None:
            continue
        if l.ref:   # référence déjà connue : on rattache au produit existant
            q = "SELECT id FROM products WHERE LOWER(ref)=LOWER(?)" + (" AND supplier_id=?" if o.supplier_id else "")
            found = db.one(q, (l.ref, o.supplier_id) if o.supplier_id else (l.ref,))
            if found:
                l.product_id = found["id"]
                continue
        if not l.create_product:
            continue
        name = (l.label or "").strip()
        if not name:
            continue
        found = db.one("SELECT id FROM products WHERE LOWER(name)=LOWER(?) AND COALESCE(supplier_id,0)=COALESCE(?,0)",
                       (name, o.supplier_id))
        if found:
            l.product_id = found["id"]
            continue
        l.product_id = db.execute(
            "INSERT INTO products (ref, name, supplier_id, label_egalim, provenance, direct_producteur, unit) VALUES (?,?,?,?,?,?,?)",
            (l.ref, name, o.supplier_id, "bio", sup["local_default"] if sup else None,
             sup["direct_producteur"] if sup else 0, l.unit or "kg"))
        created["products"].append(name)
    return created


def update_prices(order_id, o: Order, day=None):
    """Met à jour le prix des produits quand il change et alimente l'historique ; apprend les références.

    `day` : date des relevés. Une facture qui remplace des bons de livraison garde la date de livraison
    (c'est à partir de ce jour-là que le prix s'applique, pas à partir de la date de la facture).
    """
    changes = []
    day = day or o.date or date_cls.today().isoformat()
    for l in o.lines:
        if l.product_id is None:
            continue
        p = db.one("SELECT * FROM products WHERE id=?", (l.product_id,))
        if not p:
            continue
        if l.ref and not (p["ref"] or "").strip():
            db.execute("UPDATE products SET ref=? WHERE id=?", (l.ref, p["id"]))
        if l.unit_price is None:
            continue
        # le prix n'est comparé que si les unités sont compatibles (€/kg avec €/kg, pas avec €/pièce)
        if l.unit and p["unit"] and convert(1, l.unit, p["unit"]) is None:
            continue
        price = l.unit_price
        if l.unit and p["unit"]:
            factor = convert(1, l.unit, p["unit"])   # prix par unité de la ligne -> prix par unité du produit
            if factor:
                price = round(price / factor, 4)
        last = db.one("SELECT price, date FROM price_history WHERE product_id=? ORDER BY date DESC, id DESC LIMIT 1", (p["id"],))
        if last is None or abs(last["price"] - price) > 1e-9:
            add_history(p["id"], day, price, p["unit"], order_id, "reception")
            if last is None or (last["date"] or "") <= day:
                if p["unit_price"] is None or abs(p["unit_price"] - price) > 1e-9:
                    changes.append({"name": p["name"], "old": p["unit_price"], "new": price, "unit": p["unit"]})
                db.execute("UPDATE products SET unit_price=? WHERE id=?", (price, p["id"]))
    return changes


def remove_order(order_id):
    pids = [r["product_id"] for r in db.rows("SELECT DISTINCT product_id FROM price_history WHERE order_id=?", (order_id,))]
    db.execute("DELETE FROM orders WHERE id=?", (order_id,))
    for pid in pids:
        refresh_product_price(pid)


def price_day(order_id, o: Order, rdates):
    """Date des relevés de prix : une facture qui remplace des bons de livraison garde leur date de livraison."""
    cur = db.one("SELECT delivery_date FROM orders WHERE id=?", (order_id,))
    dd = [d for d in [cur and cur["delivery_date"], *(rdates or [])] if d] if o.kind == "facture" else []
    day = min(dd) if dd else None
    db.execute("UPDATE orders SET delivery_date=? WHERE id=?", (day, order_id))
    return day


def delete_replaced(ids, new_id, supplier_id):
    """Supprime les bons de livraison remplacés par la facture ; renvoie leur description."""
    done, dates = [], []
    for rid in ids:
        r = db.one("SELECT * FROM orders WHERE id=?", (rid,))
        if not r or r["kind"] != "livraison" or rid == new_id:
            continue
        if supplier_id and r["supplier_id"] and r["supplier_id"] != supplier_id:
            continue
        done.append(f"{r['ref'] or 'BL'} du {r['date'] or '?'}")
        if r["date"]:
            dates.append(r["date"])
        remove_order(rid)
    return done, dates


def normalize_order(o: Order):
    o.kind = "facture" if o.kind == "facture" else "livraison"
    if o.kind != "facture":
        o.replaces = []


def find_duplicate(ref, kind, supplier_id=None, exclude_id=None):
    """Réception déjà enregistrée avec la même référence (et le même type, chez le même fournisseur s'il est connu)."""
    key = pdf_parser.norm_ref(ref or "")
    if not key:
        return None
    for r in db.rows("SELECT o.id, o.ref, o.kind, o.date, o.supplier_id, s.name AS supplier_name FROM orders o "
                     "LEFT JOIN suppliers s ON s.id=o.supplier_id WHERE o.ref IS NOT NULL AND o.ref != ''"):
        if (r["id"] != exclude_id and pdf_parser.norm_ref(r["ref"]) == key and r["kind"] == kind
                and (not supplier_id or r["supplier_id"] in (supplier_id, None))):
            return r
    return None


@app.post("/api/orders")
def create_order(o: Order, user: dict = WRITE):
    normalize_order(o)
    dup = find_duplicate(o.ref, o.kind, o.supplier_id)
    if dup:
        raise HTTPException(409, f"{'La facture' if dup['kind'] == 'facture' else 'Le bon de livraison'} {dup['ref']} est déjà enregistré"
                                 f"{' (' + dup['supplier_name'] + ')' if dup['supplier_name'] else ''} : import refusé.")
    created = resolve_creations(o)
    o.total_ht = order_total(o)
    oid = insert("orders", o, exclude=("lines", "new_supplier_name", "new_supplier_direct", "replaces"))
    save_lines(oid, o.lines)
    replaced, rdates = delete_replaced(o.replaces, oid, o.supplier_id)   # d'abord : l'historique de prix des bons remplacés disparaît avec eux
    price_updates = update_prices(oid, o, price_day(oid, o, rdates))
    if replaced:
        note = "Remplace : " + " ; ".join(replaced)
        db.execute("UPDATE orders SET notes=? WHERE id=?", ((o.notes + "\n" if o.notes else "") + note, oid))
    return {"id": oid, "created": created, "price_updates": price_updates, "replaced": replaced}


@app.put("/api/orders/{id}")
def edit_order(id: int, o: Order, user: dict = WRITE):
    if not db.one("SELECT 1 AS x FROM orders WHERE id=?", (id,)):
        raise HTTPException(404)
    normalize_order(o)
    dup = find_duplicate(o.ref, o.kind, o.supplier_id, exclude_id=id)
    if dup:
        raise HTTPException(409, f"Un autre enregistrement porte déjà la référence {dup['ref']} : modification refusée.")
    created = resolve_creations(o)
    o.total_ht = order_total(o)
    old_pids = [r["product_id"] for r in db.rows("SELECT DISTINCT product_id FROM price_history WHERE order_id=?", (id,))]
    db.execute("DELETE FROM price_history WHERE order_id=?", (id,))
    update("orders", id, o, exclude=("lines", "new_supplier_name", "new_supplier_direct", "replaces"))
    db.execute("DELETE FROM order_lines WHERE order_id=?", (id,))
    save_lines(id, o.lines)
    replaced, rdates = delete_replaced(o.replaces, id, o.supplier_id)
    price_updates = update_prices(id, o, price_day(id, o, rdates))
    for pid in old_pids:
        refresh_product_price(pid)
    if replaced:
        note = "Remplace : " + " ; ".join(replaced)
        db.execute("UPDATE orders SET notes=? WHERE id=?", ((o.notes + "\n" if o.notes else "") + note, id))
    return {"ok": True, "created": created, "price_updates": price_updates, "replaced": replaced}


@app.delete("/api/orders/{id}")
def delete_order(id: int, user: dict = WRITE):
    remove_order(id)
    return {"ok": True}


class CandidateQuery(BaseModel):
    supplier_id: Optional[int] = None
    kind: str = "facture"
    total_ht: Optional[float] = None
    refs: list[str] = []
    exclude_id: Optional[int] = None


@app.post("/api/orders/candidates")
def replacement_candidates(q: CandidateQuery, user: dict = WRITE):
    """Bons de livraison du fournisseur qu'une facture peut remplacer (cités sur la facture ou de même montant)."""
    if q.kind != "facture" or not q.supplier_id:
        return []
    cands = db.rows(
        "SELECT id, ref, date, total_ht FROM orders WHERE supplier_id=? AND kind='livraison' AND id != ? "
        "ORDER BY date DESC, id DESC LIMIT 60", (q.supplier_id, q.exclude_id or -1))
    keys = {ref_key(r) for r in q.refs if ref_key(r)}
    for c in cands:
        reasons = []
        if ref_key(c["ref"]) and ref_key(c["ref"]) in keys:
            reasons.append("cité sur la facture")
        if q.total_ht is not None and c["total_ht"] is not None and abs(c["total_ht"] - q.total_ht) < 0.01:
            reasons.append("même montant")
        c["match"] = bool(reasons)
        c["reason"] = ", ".join(reasons)
    cands.sort(key=lambda c: not c["match"])
    return cands[:25]


@app.post("/api/orders/parse-pdf")
async def parse_pdf(file: UploadFile = File(...), user: dict = WRITE):
    """Lit un PDF et renvoie une prévisualisation (rien n'est enregistré, le fichier est conservé)."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Fichier PDF attendu")
    name = await save_upload(file, allowed={".pdf"})
    try:
        docs = pdf_parser.parse_pdf(
            str(UPLOADS / name), db.rows("SELECT * FROM suppliers"), db.rows("SELECT * FROM products"),
            client_names=get_client_names())
    except Exception as e:  # PDF illisible
        (UPLOADS / name).unlink(missing_ok=True)
        raise HTTPException(422, f"Lecture du PDF impossible : {e}")
    for d in docs:
        d["source_file"] = name
        dup = find_duplicate(d.get("ref"), d.get("kind"), d.get("supplier_id"))
        d["duplicate"] = ({"ref": dup["ref"], "date": dup["date"], "supplier_name": dup["supplier_name"]} if dup else None)
        d.pop("text_preview", None)   # contient parfois des coordonnées bancaires : inutile côté navigateur
    if docs and all(d["duplicate"] for d in docs):
        (UPLOADS / name).unlink(missing_ok=True)   # rien de nouveau : on ne garde pas le fichier en double
    return {"documents": docs, "source_file": name, "source_label": Path(file.filename).name}


# =====================================================================================
#  Recettes
# =====================================================================================
class RecipeItem(BaseModel):
    product_id: Optional[int] = None
    label: Optional[str] = None
    qty_maternelle: Optional[float] = None
    qty_elementaire: Optional[float] = None
    qty_adulte: Optional[float] = None
    qty_servi: Optional[float] = None
    qty_commander: Optional[float] = None
    unit: Optional[str] = None
    principal: bool = False
    intitule_gemrcn: Optional[str] = None


class Recipe(BaseModel):
    name: str
    categorie: Optional[str] = None   # entree | plat | accompagnement | laitage | dessert
    description: Optional[str] = None
    nb_maternelles: int = 0
    nb_elementaires: int = 0
    nb_adultes: int = 0
    items: list[RecipeItem] = []


def recipe_out(r, with_items=False):
    r = dict(r)
    if with_items:
        items = db.rows(
            "SELECT ri.*, p.name AS product_name, p.unit AS product_unit, p.unit_price "
            "FROM recipe_items ri LEFT JOIN products p ON p.id=ri.product_id "
            "WHERE ri.recipe_id=? ORDER BY ri.id", (r["id"],))
        r["items"] = [dict(i) for i in items]
    return r


def recipe_cost(recipe_id, nb_mat, nb_elem, nb_adu, meal_date=None):
    """Estime le coût d'une recette selon les effectifs donnés."""
    items = db.rows(
        "SELECT ri.*, p.unit AS product_unit, p.unit_price FROM recipe_items ri "
        "LEFT JOIN products p ON p.id=ri.product_id WHERE ri.recipe_id=?", (recipe_id,))
    if not items:
        return None
    hist = load_history()
    total = 0.0
    unpriced = 0
    for it in items:
        if not it["product_id"]:
            continue
        price = price_at(hist, it["product_id"], meal_date or date_cls.today().isoformat(), it["unit_price"])
        if price is None:
            unpriced += 1
            continue
        qty = (
            (it["qty_maternelle"] or 0) * nb_mat / 1000 +
            (it["qty_elementaire"] or 0) * nb_elem / 1000 +
            (it["qty_adulte"] or 0) * nb_adu / 1000
        )   # grammages en g → kg pour un prix en €/kg
        total += qty * price
    return {"cost": round(total, 2), "unpriced": unpriced}


@app.get("/api/recipes")
def list_recipes(user: dict = READ):
    rows = db.rows("SELECT * FROM recipes ORDER BY name")
    return [recipe_out(r) for r in rows]


@app.get("/api/recipes/{id}")
def get_recipe(id: int, user: dict = READ):
    r = db.one("SELECT * FROM recipes WHERE id=?", (id,))
    if not r:
        raise HTTPException(404)
    out = recipe_out(r, with_items=True)
    # dates où cette recette a été servie (repas liés, toutes catégories confondues)
    out["served"] = db.rows(
        "SELECT date, statut, guests, plat, entree FROM meals "
        "WHERE recipe_entree=? OR recipe_plat=? OR recipe_accompagnement=? OR recipe_laitage=? OR recipe_dessert=? "
        "ORDER BY date DESC, id DESC", (id, id, id, id, id))
    return out


def save_recipe_items(recipe_id, items: list[RecipeItem]):
    db.execute("DELETE FROM recipe_items WHERE recipe_id=?", (recipe_id,))
    for it in items:
        db.execute(
            "INSERT INTO recipe_items (recipe_id, product_id, label, qty_maternelle, qty_elementaire, qty_adulte, "
            "qty_servi, qty_commander, unit, principal, intitule_gemrcn) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (recipe_id, it.product_id, it.label, it.qty_maternelle, it.qty_elementaire, it.qty_adulte,
             it.qty_servi, it.qty_commander, it.unit, 1 if it.principal else 0, it.intitule_gemrcn))


@app.post("/api/recipes")
def create_recipe(r: Recipe, user: dict = WRITE):
    rid = db.execute(
        "INSERT INTO recipes (name, categorie, description, nb_maternelles, nb_elementaires, nb_adultes, created) "
        "VALUES (?,?,?,?,?,?,?)",
        (r.name, r.categorie, r.description, r.nb_maternelles, r.nb_elementaires, r.nb_adultes, now_iso()))
    save_recipe_items(rid, r.items)
    log_action(user, "create", "recipe", rid, f"Recette créée : {r.name!r}")
    return {"id": rid}


@app.put("/api/recipes/{id}")
def edit_recipe(id: int, r: Recipe, user: dict = WRITE):
    if not db.one("SELECT 1 AS x FROM recipes WHERE id=?", (id,)):
        raise HTTPException(404)
    db.execute(
        "UPDATE recipes SET name=?, categorie=?, description=?, nb_maternelles=?, nb_elementaires=?, nb_adultes=? "
        "WHERE id=?",
        (r.name, r.categorie, r.description, r.nb_maternelles, r.nb_elementaires, r.nb_adultes, id))
    save_recipe_items(id, r.items)
    log_action(user, "update", "recipe", id, f"Recette modifiée : {r.name!r}")
    return {"ok": True}


@app.delete("/api/recipes/{id}")
def delete_recipe(id: int, user: dict = WRITE):
    r = db.one("SELECT name FROM recipes WHERE id=?", (id,))
    if not r:
        raise HTTPException(404)
    db.execute("DELETE FROM recipes WHERE id=?", (id,))
    log_action(user, "delete", "recipe", id, f"Recette supprimée : {r['name']!r}")
    return {"ok": True}


@app.get("/api/recipes/{id}/cost")
def recipe_cost_estimate(id: int, nb_maternelles: int = 0, nb_elementaires: int = 0,
                         nb_adultes: int = 0, meal_date: Optional[str] = None, user: dict = READ):
    if not db.one("SELECT 1 AS x FROM recipes WHERE id=?", (id,)):
        raise HTTPException(404)
    return recipe_cost(id, nb_maternelles, nb_elementaires, nb_adultes, meal_date) or {"cost": 0, "unpriced": 0}


# =====================================================================================
#  Repas, coûts matières
# =====================================================================================
class MealItem(BaseModel):
    product_id: int
    qty: float
    unit: Optional[str] = None
    prix_reel: Optional[float] = None


class Meal(BaseModel):
    date: str
    nb_maternelles: int = 0
    nb_elementaires: int = 0
    nb_adultes: int = 0
    notes: Optional[str] = None
    entree: Optional[str] = None
    plat: Optional[str] = None
    accompagnement: Optional[str] = None
    laitage: Optional[str] = None
    dessert: Optional[str] = None
    commentaire_post: Optional[str] = None
    modif_prevu: bool = False
    statut: str = "prevu"
    recipe_entree: Optional[int] = None
    recipe_plat: Optional[int] = None
    recipe_accompagnement: Optional[int] = None
    recipe_laitage: Optional[int] = None
    recipe_dessert: Optional[int] = None
    estimation: Optional[list] = None   # lignes de l'estimation des coûts : [{cat, label, product_id, qty, price, unit, manual}]
    items: list[MealItem] = []

    @field_validator("nb_maternelles", "nb_elementaires", "nb_adultes")
    @classmethod
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("Les effectifs ne peuvent pas être négatifs")
        return v


def load_history():
    h = {}
    for r in db.rows("SELECT product_id, date, price FROM price_history ORDER BY date, id"):
        h.setdefault(r["product_id"], []).append((r["date"] or "", r["price"]))
    return h


def price_at(hist, pid, day, fallback):
    """Prix d'un produit à une date (dernier relevé connu à cette date), à défaut le prix courant."""
    seq = hist.get(pid)
    if not seq:
        return fallback
    best = None
    for d, p in seq:
        if d <= (day or ""):
            best = p
        else:
            break
    return best if best is not None else seq[0][1]


def meals_metrics(date_from=None, date_to=None, product_id=None):
    where, args = ["1=1"], []
    if date_from:
        where.append("m.date >= ?"); args.append(date_from)
    if date_to:
        where.append("m.date <= ?"); args.append(date_to)
    if product_id:   # filtre : repas dont le bilan (lignes réellement sorties) contient ce produit
        where.append("m.id IN (SELECT meal_id FROM meal_items WHERE product_id=?)"); args.append(product_id)
    w = " AND ".join(where)
    meals = db.rows(f"SELECT m.* FROM meals m WHERE {w} ORDER BY m.date DESC, m.id DESC", args)
    items = db.rows(
        "SELECT i.meal_id, i.product_id, i.qty, i.unit, i.prix_reel, m.date AS mdate, p.unit AS punit, p.unit_price, "
        "p.label_egalim, p.provenance FROM meal_items i JOIN meals m ON m.id=i.meal_id "
        f"JOIN products p ON p.id=i.product_id WHERE {w}", args)
    hist = load_history()
    acc = {m["id"]: {"cost": 0.0, "bio": 0.0, "local": 0.0, "n": 0, "unpriced": 0} for m in meals}
    for it in items:
        a = acc[it["meal_id"]]
        a["n"] += 1
        # Prix réel saisi manuellement > historique calculé
        if it["prix_reel"] is not None:
            price = it["prix_reel"]
        else:
            price = price_at(hist, it["product_id"], it["mdate"], it["unit_price"])
        qty = convert(it["qty"], it["unit"] or it["punit"], it["punit"] or it["unit"])
        if price is None or qty is None:
            a["unpriced"] += 1
            continue
        c = qty * price
        a["cost"] += c
        if it["label_egalim"] == "bio":
            a["bio"] += c
        if it["provenance"] in LOCAL:
            a["local"] += c
    out = []
    for m in meals:
        a = acc[m["id"]]
        cost = round(a["cost"], 2)
        out.append({
            "id": m["id"], "date": m["date"], "nb_maternelles": m["nb_maternelles"] or 0,
            "nb_elementaires": m["nb_elementaires"] or 0, "nb_adultes": m["nb_adultes"] or 0,
            "guests": m["guests"], "notes": m["notes"],
            "entree": m["entree"], "plat": m["plat"], "accompagnement": m["accompagnement"],
            "laitage": m["laitage"], "dessert": m["dessert"],
            "commentaire_post": m["commentaire_post"], "statut": m["statut"] or "prevu",
            "modif_prevu": bool(m["modif_prevu"]),
            "nb_items": a["n"], "unpriced": a["unpriced"],
            "cost": cost,
            "per_guest": round(cost / m["guests"], 2) if cost and m["guests"] else None,
            "pct_bio": round(100 * a["bio"] / a["cost"], 1) if a["cost"] else None,
            "pct_local": round(100 * a["local"] / a["cost"], 1) if a["cost"] else None,
        })
    return out


@app.get("/api/meals")
def meals(product_id: int = None, user: dict = READ):
    return meals_metrics(product_id=product_id)


@app.get("/api/meals/shopping-list")
def shopping_list(date_from: str, date_to: str, user: dict = READ):
    """Liste de courses : quantités des produits sortis pour les repas de la période, triées par catégorie."""
    rows = db.rows(
        "SELECT i.product_id, i.qty, i.unit, p.name, p.category, p.unit AS punit "
        "FROM meal_items i JOIN meals m ON m.id=i.meal_id JOIN products p ON p.id=i.product_id "
        "WHERE m.date >= ? AND m.date <= ?", (date_from, date_to))
    acc = {}
    for r in rows:
        pu = r["punit"] or r["unit"] or "kg"
        q = convert(r["qty"], r["unit"] or pu, pu)
        u = pu
        if q is None:   # unité incompatible avec celle du produit : gardée telle quelle
            q, u = r["qty"], r["unit"] or pu
        a = acc.setdefault((r["product_id"], u), {
            "product_id": r["product_id"], "label": r["name"], "category": r["category"] or "Autre",
            "unit": u, "qty": 0.0})
        a["qty"] += q
    out = sorted(acc.values(), key=lambda a: (
        CATEGORIES.index(a["category"]) if a["category"] in CATEGORIES else len(CATEGORIES),
        a["category"].lower(), a["label"].lower()))
    for a in out:
        a["qty"] = round(a["qty"], 3)
    return out


@app.get("/api/meals/{id}")
def get_meal(id: int, user: dict = READ):
    m = db.one("SELECT * FROM meals WHERE id=?", (id,))
    if not m:
        raise HTTPException(404)
    m["items"] = db.rows(
        "SELECT i.*, p.name AS product_name, p.unit_price AS unit_price FROM meal_items i "
        "JOIN products p ON p.id=i.product_id WHERE i.meal_id=? ORDER BY i.id", (id,))
    try:
        m["estimation"] = json.loads(m["estimation"]) if m.get("estimation") else []
    except (ValueError, TypeError):
        m["estimation"] = []
    return dict(m)


def save_meal(mid, m: Meal):
    guests = m.nb_maternelles + m.nb_elementaires + m.nb_adultes
    db.execute(
        "UPDATE meals SET date=?, nb_maternelles=?, nb_elementaires=?, nb_adultes=?, guests=?, notes=?, "
        "entree=?, plat=?, accompagnement=?, laitage=?, dessert=?, commentaire_post=?, modif_prevu=?, statut=?, "
        "recipe_entree=?, recipe_plat=?, recipe_accompagnement=?, recipe_laitage=?, recipe_dessert=?, estimation=? WHERE id=?",
        (m.date, m.nb_maternelles, m.nb_elementaires, m.nb_adultes, guests, m.notes,
         m.entree, m.plat, m.accompagnement, m.laitage, m.dessert, m.commentaire_post, int(m.modif_prevu), m.statut,
         m.recipe_entree, m.recipe_plat, m.recipe_accompagnement, m.recipe_laitage, m.recipe_dessert,
         json.dumps(m.estimation, ensure_ascii=False) if m.estimation else None, mid))
    db.execute("DELETE FROM meal_items WHERE meal_id=?", (mid,))
    for i in m.items:
        if i.qty > 0:
            db.execute("INSERT INTO meal_items (meal_id, product_id, qty, unit, prix_reel) VALUES (?,?,?,?,?)",
                       (mid, i.product_id, i.qty, i.unit, i.prix_reel))


@app.post("/api/meals/parse-menu-pdf")
async def parse_menu_pdf(file: UploadFile = File(...), user: dict = WRITE):
    """Lit un PDF de menu et renvoie la liste des repas détectés (rien n'est enregistré)."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Fichier PDF attendu")
    name = await save_upload(file, allowed={".pdf"})
    path = str(UPLOADS / name)
    try:
        repas = menu_parser.parse_menu_pdf(path)
    except Exception as e:
        (UPLOADS / name).unlink(missing_ok=True)
        raise HTTPException(422, f"Lecture du PDF impossible : {e}")
    # Marquer les dates déjà enregistrées
    existing_dates = {r["date"] for r in db.rows("SELECT date FROM meals")}
    for r in repas:
        r["already_exists"] = r["date"] in existing_dates
    return {"repas": repas, "source_file": name}


@app.post("/api/meals")
def create_meal(m: Meal, user: dict = WRITE):
    mid = db.execute(
        "INSERT INTO meals (date, entree, plat, accompagnement, laitage, dessert, statut) VALUES (?,?,?,?,?,?,?)",
        (m.date, m.entree, m.plat, m.accompagnement, m.laitage, m.dessert, m.statut or "prevu"))
    save_meal(mid, m)
    return {"id": mid}


@app.put("/api/meals/{id}")
def edit_meal(id: int, m: Meal, user: dict = WRITE):
    if not db.one("SELECT 1 AS x FROM meals WHERE id=?", (id,)):
        raise HTTPException(404)
    save_meal(id, m)
    return {"ok": True}


@app.delete("/api/meals/{id}")
def delete_meal(id: int, user: dict = WRITE):
    db.execute("DELETE FROM meals WHERE id=?", (id,))
    return {"ok": True}


# =====================================================================================
#  Stocks : reçu (réceptions) - sorti (repas) + ajustements (inventaires)
# =====================================================================================
def compute_stock():
    prods = {p["id"]: p for p in db.rows(
        "SELECT p.*, s.name AS supplier_name FROM products p LEFT JOIN suppliers s ON s.id=p.supplier_id")}
    acc = {}

    def add(pid, field, qty, unit):
        p = prods.get(pid)
        if not p or qty is None:
            return
        pu = p["unit"] or "kg"
        q, u = convert(qty, unit or pu, pu), pu
        if q is None:   # unité incompatible avec celle du produit : suivie à part
            q, u = qty, unit
        r = acc.setdefault((pid, u), {"in": 0.0, "out": 0.0, "adj": 0.0})
        r[field] += q

    for l in db.rows("SELECT product_id, qty, unit FROM order_lines WHERE product_id IS NOT NULL"):
        add(l["product_id"], "in", l["qty"], l["unit"])
    for i in db.rows("SELECT product_id, qty, unit FROM meal_items"):
        add(i["product_id"], "out", i["qty"], i["unit"])
    for a in db.rows("SELECT product_id, qty, unit FROM stock_adjustments"):
        add(a["product_id"], "adj", a["qty"], a["unit"])
    rows_ = []
    for (pid, unit), r in acc.items():
        p = prods[pid]
        stock = round(r["in"] - r["out"] + r["adj"], 3)
        value = round(stock * p["unit_price"], 2) if p["unit_price"] is not None and unit == (p["unit"] or "kg") else None
        rows_.append({"product_id": pid, "ref": p["ref"], "name": p["name"], "category": p["category"],
                      "supplier_id": p["supplier_id"], "supplier_name": p["supplier_name"], "unit": unit,
                      "received": round(r["in"], 3), "used": round(r["out"], 3), "adjusted": round(r["adj"], 3),
                      "stock": stock, "value": value})
    rows_.sort(key=lambda r: (r["name"] or "").lower())
    return rows_


class StockAdjust(BaseModel):
    product_id: int
    unit: Optional[str] = None
    target_qty: float
    reason: Optional[str] = None


@app.get("/api/stock")
def stock(user: dict = READ):
    adj = db.rows(
        "SELECT a.id, a.date, a.qty, a.unit, a.reason, a.username, p.name AS product_name "
        "FROM stock_adjustments a JOIN products p ON p.id=a.product_id ORDER BY a.date DESC, a.id DESC LIMIT 50")
    return {"rows": compute_stock(), "adjustments": adj}


@app.post("/api/stock/adjust")
def stock_adjust(a: StockAdjust, user: dict = WRITE):
    """Inventaire : on saisit la quantité réellement présente, l'écart devient un ajustement."""
    p = db.one("SELECT * FROM products WHERE id=?", (a.product_id,))
    if not p:
        raise HTTPException(404)
    unit = a.unit or p["unit"] or "kg"
    current = next((r["stock"] for r in compute_stock() if r["product_id"] == a.product_id and r["unit"] == unit), 0.0)
    delta = round(a.target_qty - current, 3)
    if delta == 0:
        return {"delta": 0}
    db.execute("INSERT INTO stock_adjustments (product_id, date, qty, unit, reason, username) VALUES (?,?,?,?,?,?)",
               (a.product_id, date_cls.today().isoformat(), delta, unit, a.reason, user["username"]))
    return {"delta": delta}


@app.delete("/api/stock/adjustments/{id}")
def delete_adjustment(id: int, user: dict = WRITE):
    db.execute("DELETE FROM stock_adjustments WHERE id=?", (id,))
    return {"ok": True}


# =====================================================================================
#  Statistiques
# =====================================================================================
def breakdown(rows_, key, labels=None):
    total = sum(r["spend"] for r in rows_) or 0
    agg = {}
    for r in rows_:
        k = r[key] if r[key] not in (None, "") else "non renseigné"
        agg[k] = agg.get(k, 0) + r["spend"]
    out = []
    for k, v in sorted(agg.items(), key=lambda kv: -kv[1]):
        out.append({
            "key": k,
            "label": (labels or {}).get(k, k),
            "amount": round(v, 2),
            "pct": round(100 * v / total, 1) if total else 0,
        })
    return out


def _metric_pred(metric):
    """Retourne le prédicat correspondant à un indicateur."""
    kind, _, key = metric.partition(":")
    preds = {
        "bio": lambda r: r["label_egalim"] == "bio",
        "egalim": lambda r: r["label_egalim"] in ("bio", "autre"),
        "local": lambda r: r["provenance"] in LOCAL,
        "direct": lambda r: bool(r["direct_producteur"]),
        "label": lambda r: r["label_egalim"] == key,
        "provenance": lambda r: r["provenance"] == key,
        "gamme": lambda r: r["gamme"] == key,
    }
    return preds.get(kind)


def lines_metric(lines, metric, category=None):
    """Calcul pour un seul indicateur / une seule catégorie (compatibilité ancienne API)."""
    subset = [r for r in lines if not category or r["category"] == category]
    total = sum(r["spend"] for r in subset)
    if not total:
        return None
    pred = _metric_pred(metric)
    if not pred:
        return None
    return round(100 * sum(r["spend"] for r in subset if pred(r)) / total, 1)


def lines_metric_multi(lines, metrics, categories=None, gammes=None):
    """Calcul pour plusieurs indicateurs, catégories et/ou gammes.

    - Si plusieurs indicateurs : on vérifie qu'une ligne respecte AU MOINS UN des indicateurs (union).
    - Si des catégories sont précisées : on ne garde que les lignes de ces catégories.
    - Si des gammes sont précisées : on filtre supplémentairement sur ces gammes.
    Le résultat est le % de dépenses satisfaisant au moins un indicateur sur l'assiette filtrée.
    """
    subset = lines
    if categories:
        subset = [r for r in subset if r["category"] in categories]
    if gammes:
        subset = [r for r in subset if r["gamme"] in gammes]
    total = sum(r["spend"] for r in subset)
    if not total:
        return None
    if not metrics:
        return None
    preds = [p for p in (_metric_pred(m) for m in metrics) if p is not None]
    if not preds:
        return None
    return round(100 * sum(r["spend"] for r in subset if any(p(r) for p in preds)) / total, 1)


@app.get("/api/stats")
def stats(date_from: Optional[str] = None, date_to: Optional[str] = None, user: dict = ANY):
    """Statistiques sur la période. Le prix par repas = coûts matières des repas ÷ nombre de convives.

    Pour le profil « stats », tout ce qui révèle un prix est retiré de la réponse côté serveur.
    """
    where, args = ["1=1"], []
    if date_from:
        where.append("o.date >= ?"); args.append(date_from)
    if date_to:
        where.append("o.date <= ?"); args.append(date_to)
    w = " AND ".join(where)
    lines = db.rows(
        "SELECT l.order_id, o.total_ht AS order_total, l.qty, COALESCE(l.total_ht, l.qty*l.unit_price) AS spend, "
        "p.label_egalim, p.provenance, p.gamme, p.category, p.direct_producteur, s.name AS supplier "
        "FROM order_lines l JOIN orders o ON o.id=l.order_id "
        "LEFT JOIN products p ON p.id=l.product_id LEFT JOIN suppliers s ON s.id=o.supplier_id "
        f"WHERE {w}", args)
    # Lignes sans montant (bon de livraison sans prix) : si le total HT de la réception est connu, l'écart avec les
    # lignes chiffrées est réparti sur ces lignes (au prorata des quantités) pour que les achats soient bien comptés.
    by_order = {}
    for r in lines:
        by_order.setdefault(r["order_id"], []).append(r)
    for rs in by_order.values():
        open_ = [r for r in rs if not r["spend"]]
        known = sum(r["spend"] or 0 for r in rs)
        rest = (rs[0]["order_total"] or 0) - known
        if open_ and rest > 0.005:
            weights = [r["qty"] or 0 for r in open_]
            tw = sum(weights)
            for r, wgt in zip(open_, weights):
                r["spend"] = rest * (wgt / tw if tw else 1 / len(open_))
    for r in lines:
        r["spend"] = r["spend"] or 0
    total = round(sum(r["spend"] for r in lines), 2)

    def pct(pred):
        return round(100 * sum(r["spend"] for r in lines if pred(r)) / total, 1) if total else 0

    mm = meals_metrics(date_from, date_to)
    priced = [m for m in mm if m["cost"] > 0 and m["guests"] > 0]
    cost_total = round(sum(m["cost"] for m in priced), 2)
    guests_priced = sum(m["guests"] for m in priced)
    price_per_meal = round(cost_total / guests_priced, 2) if guests_priced else None
    daily = sorted(({"date": m["date"], "guests": m["guests"], "cost": m["cost"], "per_guest": m["per_guest"],
                     "pct_bio": m["pct_bio"], "pct_local": m["pct_local"]} for m in mm),
                   key=lambda d: d["date"])

    labels = dict(metric_options())
    engagements = []
    for c in [commitment_out(r) for r in db.rows("SELECT * FROM commitments ORDER BY id")]:
        metrics = c["metrics"]
        categories = c["categories"] or None
        gammes = c["gammes"] or None
        if "price_per_meal" in metrics:
            actual = price_per_meal
        else:
            actual = lines_metric_multi(lines, metrics, categories, gammes)
        if actual is None:
            status = "nodata"
        elif c["mode"] == "max":
            status = "ok" if actual <= c["target"] else "ko"
        else:
            status = "ok" if actual >= c["target"] else "ko"
        metric_label = " + ".join(labels.get(m, m) for m in metrics)
        engagements.append({**c, "metric_label": metric_label, "actual": actual, "status": status})

    result = {
        "commitments": engagements,
        "total_ht": total,
        "nb_lines": len(lines),
        "meals": len(mm),
        "meals_priced": len(priced),
        "guests": sum(m["guests"] for m in mm),
        "cost_total": cost_total,
        "price_per_meal": price_per_meal,
        "pct_bio": pct(lambda r: r["label_egalim"] == "bio"),
        "pct_egalim": pct(lambda r: r["label_egalim"] in ("bio", "autre")),
        "pct_local": pct(lambda r: r["provenance"] in LOCAL),
        "pct_direct": pct(lambda r: r["direct_producteur"]),
        "by_label": breakdown(lines, "label_egalim", {"bio": "Bio", "autre": "Autre label", "sans": "Sans label"}),
        "by_provenance": breakdown(lines, "provenance", PROVENANCES),
        "by_gamme": breakdown(lines, "gamme", GAMMES),
        "by_category": breakdown(lines, "category"),
        "by_supplier": breakdown(lines, "supplier"),
        "daily": daily,
        "prices_hidden": False,
    }
    if user["role"] == "stats":
        for k in ("total_ht", "cost_total", "price_per_meal", "daily", "nb_lines"):
            result.pop(k, None)
        for k in ("by_label", "by_provenance", "by_gamme", "by_category", "by_supplier"):
            for row in result[k]:
                row.pop("amount", None)
        result["commitments"] = [c for c in result["commitments"] if "price_per_meal" not in c.get("metrics", [c.get("metric", "")])]
        result["prices_hidden"] = True
    return result


# =====================================================================================
#  Sauvegarde de toutes les données
# =====================================================================================
@app.get("/api/backup")
def backup(user: dict = ADMIN):
    """Archive .zip : base de données (copie cohérente) + tous les PDF et fiches techniques."""
    fd, tmp_zip = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    fd, tmp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    src, dst = sqlite3.connect(db.DB_PATH), sqlite3.connect(tmp_db)
    try:
        src.backup(dst)
        dst.execute("DELETE FROM sessions")   # on ne sauvegarde pas les connexions en cours
        dst.commit()
    finally:
        src.close()
        dst.close()
    with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp_db, "cantine.db")
        for p in sorted(UPLOADS.rglob("*")):
            if p.is_file():
                z.write(p, f"uploads/{p.relative_to(UPLOADS).as_posix()}")
        z.writestr("LISEZ-MOI.txt", (
            f"Sauvegarde CGRS du {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            "Contenu : cantine.db (toutes les données, y compris les comptes utilisateurs et leurs mots de passe chiffrés)\n"
            "et uploads/ (PDF des réceptions, fiches techniques).\n\n"
            "Ce fichier contient des données sensibles : ne le partagez pas.\n\n"
            "Restauration : arrêter l'application, remplacer cantine.db et le dossier uploads/ du dossier de l'application\n"
            "par ceux de cette archive, puis relancer l'application.\n"))
    os.remove(tmp_db)
    return FileResponse(tmp_zip, media_type="application/zip",
                        filename=f"cgrs-sauvegarde-{date_cls.today().isoformat()}.zip",
                        background=BackgroundTask(os.remove, tmp_zip))


MAX_RESTORE = 500 * 1024 * 1024
RESTORE_TABLES = {"suppliers", "products", "orders", "order_lines", "meals", "users", "settings"}


@app.post("/api/restore")
async def restore(file: UploadFile = File(...), user: dict = ADMIN):
    """Restaure une sauvegarde (.zip produit par « Sauvegarder toutes les données »).

    La base actuelle est remplacée par celle de l'archive (une copie de sécurité de l'ancienne est conservée dans
    le dossier « sauvegardes-auto »), les PDF et fiches techniques de l'archive sont remis dans uploads/.
    """
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Fichier .zip attendu (sauvegarde de l'application)")
    fd, tmp_zip = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    tmp_dir = tempfile.mkdtemp()
    try:
        size = 0
        with open(tmp_zip, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_RESTORE:
                    raise HTTPException(413, "Archive trop volumineuse (500 Mo maximum)")
                f.write(chunk)
        try:
            z = zipfile.ZipFile(tmp_zip)
        except zipfile.BadZipFile:
            raise HTTPException(400, "Ce fichier n'est pas une archive .zip valide")
        with z:
            if "cantine.db" not in z.namelist():
                raise HTTPException(400, "Archive invalide : cantine.db est absent (ce n'est pas une sauvegarde CGRS)")
            new_db = Path(tmp_dir) / "cantine.db"
            with z.open("cantine.db") as src, open(new_db, "wb") as dst:
                dst.write(src.read())
            # contrôle de la base de l'archive avant de toucher à quoi que ce soit
            try:
                c = sqlite3.connect(new_db)
                ok = c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                admins = c.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] if "users" in tables else 0
                c.close()
            except sqlite3.DatabaseError:
                raise HTTPException(400, "La base de données de l'archive est illisible")
            if not ok or not RESTORE_TABLES <= tables:
                raise HTTPException(400, "La base de l'archive est incomplète ou abîmée : restauration annulée")
            if not admins:
                raise HTTPException(400, "La sauvegarde ne contient aucun administrateur : restauration annulée")
            # copie de sécurité de l'état actuel
            safe_dir = paths.BACKUPS
            safe_dir.mkdir(exist_ok=True)
            safe = safe_dir / f"avant-restauration-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            s_, d_ = sqlite3.connect(db.DB_PATH), sqlite3.connect(safe)
            try:
                s_.backup(d_)
            finally:
                s_.close()
                d_.close()
            # remplacement du contenu de la base en place
            s_, d_ = sqlite3.connect(new_db), sqlite3.connect(db.DB_PATH)
            try:
                s_.backup(d_)
            finally:
                s_.close()
                d_.close()
            db.init()   # ajoute les colonnes manquantes si la sauvegarde vient d'une ancienne version
            files = 0
            for name in z.namelist():
                parts = Path(name).parts
                if len(parts) == 2 and parts[0] == "uploads" and parts[1] not in ("", ".", "..") and not name.endswith("/"):
                    dest = UPLOADS / Path(parts[1]).name
                    with z.open(name) as src, open(dest, "wb") as out:
                        out.write(src.read())
                    files += 1
        return {"ok": True, "files": files, "safety_copy": safe.name}
    finally:
        os.remove(tmp_zip)
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


seed_commitments()
DEFAULT_CLIENTS = "C.G.R.S. SAFFRE; CGRS; Saffré; Restaurant scolaire; Rest scolaire; Comité de gestion"
_cn = db.one("SELECT value FROM settings WHERE key='client_names'")
if not _cn:
    db.execute("INSERT INTO settings (key, value) VALUES ('client_names', ?)", (DEFAULT_CLIENTS,))
elif _cn["value"] == "C.G.R.S. SAFFRE":   # ancienne valeur par défaut : on l'élargit aux variantes vues sur les documents
    db.execute("UPDATE settings SET value=? WHERE key='client_names'", (DEFAULT_CLIENTS,))


# =====================================================================================
#  Journal des actions
# =====================================================================================
@app.get("/api/action-log")
def get_action_log(limit: int = 200, user: dict = ADMIN):
    rows = db.rows(
        "SELECT id, ts, username, action, entity, entity_id, description "
        "FROM action_log ORDER BY ts DESC, id DESC LIMIT ?", (limit,))
    return rows


# =====================================================================================
#  Front
# =====================================================================================
@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")