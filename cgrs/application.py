"""Assemblage de l'application FastAPI : base de données, en-têtes de sécurité, routes, fichiers statiques."""


from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import db
from cgrs import errors
from cgrs.config import STATIC
from cgrs.routes.commitments import seed_commitments
from cgrs.routes import auth
from cgrs.routes import users
from cgrs.routes import export
from cgrs.routes import files
from cgrs.routes import meta
from cgrs.routes import settings
from cgrs.routes import convives
from cgrs.routes import grammages
from cgrs.routes import commitments
from cgrs.routes import suppliers
from cgrs.routes import products
from cgrs.routes import orders
from cgrs.routes import recipes
from cgrs.routes import meals
from cgrs.routes import stock
from cgrs.routes import stats
from cgrs.routes import backup
from cgrs.routes import action_log


db.init()
app = FastAPI(title="CGRS – réceptions & stocks")


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


errors.register(app)


# Enregistrement des routes (ordre des sections de l'ancien app.py)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(export.router)
app.include_router(files.router)
app.include_router(meta.router)
app.include_router(settings.router)
app.include_router(convives.router)
app.include_router(grammages.router)
app.include_router(commitments.router)
app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(recipes.router)
app.include_router(meals.router)
app.include_router(stock.router)
app.include_router(stats.router)
app.include_router(backup.router)
app.include_router(action_log.router)


# Amorçage des données par défaut
seed_commitments()
DEFAULT_CLIENTS = "C.G.R.S. SAFFRE; CGRS; Saffré; Restaurant scolaire; Rest scolaire; Comité de gestion"
_cn = db.one("SELECT value FROM settings WHERE key='client_names'")
if not _cn:
    db.execute("INSERT INTO settings (key, value) VALUES ('client_names', ?)", (DEFAULT_CLIENTS,))
elif _cn["value"] == "C.G.R.S. SAFFRE":   # ancienne valeur par défaut : on l'élargit aux variantes vues sur les documents
    db.execute("UPDATE settings SET value=? WHERE key='client_names'", (DEFAULT_CLIENTS,))


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
