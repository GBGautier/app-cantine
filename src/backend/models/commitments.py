"""Modèles pour les engagements."""

from typing import Optional

from pydantic import BaseModel, Field


class CommitmentBase(BaseModel):
    """Base pour les modèles engagement."""

    label: str = Field(..., description="Libellé de l'engagement")
    metric: str = Field(..., description="Métrique")
    metrics: Optional[str] = Field(default=None, description="Liste des métriques (JSON)")
    category: Optional[str] = Field(default=None, description="Catégorie")
    categories: Optional[str] = Field(default=None, description="Liste des catégories (JSON)")
    gammes: Optional[str] = Field(default=None, description="Liste des gammes (JSON)")
    level: str = Field(default="marche", description="Niveau")
    target: float = Field(..., description="Cible (% ou €)")
    mode: str = Field(default="min", description="Mode (min/max)")
    notes: Optional[str] = Field(default=None, description="Notes")


class CommitmentCreate(CommitmentBase):
    """Création d'un nouvel engagement."""

    pass


class CommitmentEdit(BaseModel):
    """Édition d'un engagement."""

    label: Optional[str] = Field(default=None, description="Libellé de l'engagement")
    metric: Optional[str] = Field(default=None, description="Métrique")
    metrics: Optional[str] = Field(default=None, description="Liste des métriques (JSON)")
    category: Optional[str] = Field(default=None, description="Catégorie")
    categories: Optional[str] = Field(default=None, description="Liste des catégories (JSON)")
    gammes: Optional[str] = Field(default=None, description="Liste des gammes (JSON)")
    level: Optional[str] = Field(default=None, description="Niveau")
    target: Optional[float] = Field(default=None, description="Cible")
    mode: Optional[str] = Field(default=None, description="Mode")
    notes: Optional[str] = Field(default=None, description="Notes")


class CommitmentOut(CommitmentBase):
    """Engagement en sortie."""

    id: int = Field(..., description="ID de l'engagement")

    class Config:
        from_attributes = True
