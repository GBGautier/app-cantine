"""Modèle de base pour toutes les réponses API."""

from pydantic import BaseModel


class BaseResponse(BaseModel):
    """Modèle de base pour toutes les réponses API."""

    success: bool = True
    message: str | None = None


class PaginatedResponse(BaseResponse):
    """Modèle pour les réponses paginées."""

    data: list | None = None
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


class ErrorResponse(BaseModel):
    """Modèle pour les réponses d'erreur."""

    success: bool = False
    error: str
    detail: str | None = None
    code: int | None = None
