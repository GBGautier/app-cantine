"""Mod\u00e8les pour les engagements."""

import json
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CommitmentBase(BaseModel):
    """Base pour les mod\u00e8les engagement."""

    label: str = Field(..., description="Libell\u00e9 de l'engagement")
    metric: str = Field(..., description="M\u00e9trique")
    metrics: Optional[str] = Field(default=None, description="Liste des m\u00e9triques (JSON)")
    category: Optional[str] = Field(default=None, description="Cat\u00e9gorie")
    categories: Optional[str] = Field(default=None, description="Liste des cat\u00e9gories (JSON)")
    gammes: Optional[str] = Field(default=None, description="Liste des gammes (JSON)")
    level: str = Field(default="marche", description="Niveau")
    target: float = Field(..., description="Cible (% ou \u20ac)")
    mode: str = Field(default="min", description="Mode (min/max)")
    notes: Optional[str] = Field(default=None, description="Notes")


class CommitmentCreate(CommitmentBase):
    """Cr\u00e9ation d'un nouvel engagement."""

    pass


class CommitmentEdit(BaseModel):
    """\u00c9dition d'un engagement."""

    label: Optional[str] = Field(default=None, description="Libell\u00e9 de l'engagement")
    metric: Optional[str] = Field(default=None, description="M\u00e9trique")
    metrics: Optional[str] = Field(default=None, description="Liste des m\u00e9triques (JSON)")
    category: Optional[str] = Field(default=None, description="Cat\u00e9gorie")
    categories: Optional[str] = Field(default=None, description="Liste des cat\u00e9gories (JSON)")
    gammes: Optional[str] = Field(default=None, description="Liste des gammes (JSON)")
    level: Optional[str] = Field(default=None, description="Niveau")
    target: Optional[float] = Field(default=None, description="Cible")
    mode: Optional[str] = Field(default=None, description="Mode")
    notes: Optional[str] = Field(default=None, description="Notes")


class CommitmentOut(CommitmentBase):
    """Engagement en sortie."""

    id: int = Field(..., description="ID de l'engagement")

    @field_validator('metrics', 'categories', 'gammes', mode='before')
    @classmethod
    def parse_json_fields(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    class Config:
        from_attributes = True
