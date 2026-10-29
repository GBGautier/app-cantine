"""Application FastAPI principale pour CGRS - Réceptions & stocks.

Ce module initialise l'application FastAPI et enregistre toutes les routes.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.backend.config import get_static_dir, settings
from src.backend.db import init as init_db
from src.backend.routes import (
    auth_router,
    backup_router,
    commitments_router,
    export_router,
    files_router,
    grammages_router,
    meals_router,
    orders_router,
    products_router,
    recipes_router,
    settings_router,
    stocks_router,
    suppliers_router,
    users_router,
)
from src.backend.utils import (
    COOKIE,
    current_user,
    now_iso,
    PROVENANCES,
    LOCAL,
    GAMMES,
    CATEGORIES,
    DAYS,
    ORDER_METHODS,
    ROLES,
    KINDS,
)

# Initialisation de la base de données
init_db()

# Configuration du logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestion du cycle de vie de l'application."""
    # Initialisation
    logger.info("Initialisation de l'application CGRS")
    
    # Création des répertoires nécessaires
    from src.backend.config import get_uploads_dir, get_backups_dir
    get_uploads_dir()
    get_backups_dir()
    
    yield
    
    # Nettoyage
    logger.info("Arrêt de l'application CGRS")


# Création de l'application FastAPI
app = FastAPI(
    title="CGRS – Réceptions & stocks",
    description="Application de gestion des réceptions et stocks pour les cantines scolaires",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware de sécurité
@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Ajoute les en-têtes de sécurité HTTP."""
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    if request.url.path.startswith("/api/files/"):
        resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    else:
        resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# Enregistrement des routes
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(suppliers_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(meals_router)
app.include_router(recipes_router)
app.include_router(stocks_router)
app.include_router(commitments_router)
app.include_router(settings_router)
app.include_router(grammages_router)
app.include_router(export_router)
app.include_router(backup_router)
app.include_router(files_router)


# Route pour servir le frontend
@app.get("/")
async def serve_frontend():
    """Sert le fichier index.html du frontend."""
    static_dir = get_static_dir()
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Bienvenue sur CGRS - Réceptions & stocks"}


# Montage des fichiers statiques
try:
    static_dir = get_static_dir()
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception as e:
    logger.warning(f"Impossible de monter les fichiers statiques: {e}")


# Export des variables pour compatibilité
COOKIE = "cgrs_session"
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.backend.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
