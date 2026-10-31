"""Erreurs de la base de données traduites en réponses claires (au lieu d'une erreur 500 opaque).

Le frontend affiche le champ `detail` de la réponse : ces messages sont donc ceux que voit l'utilisateur.
"""
import sqlite3

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def integrity_response(exc: sqlite3.IntegrityError) -> tuple[int, str]:
    """(code HTTP, message) pour une contrainte d'intégrité non respectée."""
    msg = str(exc).upper()
    if "FOREIGN KEY" in msg:
        return 422, "Référence inconnue : un élément lié (fournisseur, produit, recette…) n'existe pas ou a été supprimé."
    if "UNIQUE" in msg:
        return 409, "Cet élément existe déjà."
    if "NOT NULL" in msg:
        return 422, "Une information obligatoire est manquante."
    return 409, "Opération refusée : elle violerait une règle d'intégrité des données."


def register(app: FastAPI) -> None:
    """Enregistre les gestionnaires d'erreurs de la base de données."""

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error(request: Request, exc: sqlite3.IntegrityError):
        status, detail = integrity_response(exc)
        return JSONResponse({"detail": detail}, status_code=status)

    @app.exception_handler(sqlite3.OperationalError)
    async def operational_error(request: Request, exc: sqlite3.OperationalError):
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            return JSONResponse({"detail": "La base de données est occupée : réessayez dans un instant."},
                                status_code=503, headers={"Retry-After": "2"})
        raise exc   # autre erreur technique : traitée comme une erreur interne
