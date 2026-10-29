"""Modèles pour les stocks."""

from typing import Optional

from pydantic import BaseModel, Field


class StockAdjustmentBase(BaseModel):
    """Base pour les ajustements de stock."""

    product_id: int = Field(..., description="ID du produit")
    date: str = Field(..., description="Date (AAAA-MM-JJ)")
    qty: float = Field(..., description="Quantité (positive ou négative)")
    unit: Optional[str] = Field(default=None, description="Unité")
    reason: Optional[str] = Field(default=None, description="Raison")
    username: Optional[str] = Field(default=None, description="Utilisateur")


class StockAdjustmentCreate(StockAdjustmentBase):
    """Création d'un nouvel ajustement de stock."""

    pass


class StockAdjustmentEdit(BaseModel):
    """Édition d'un ajustement de stock."""

    date: Optional[str] = Field(default=None, description="Date (AAAA-MM-JJ)")
    qty: Optional[float] = Field(default=None, description="Quantité")
    unit: Optional[str] = Field(default=None, description="Unité")
    reason: Optional[str] = Field(default=None, description="Raison")


class StockAdjustmentOut(StockAdjustmentBase):
    """Ajustement de stock en sortie."""

    id: int = Field(..., description="ID de l'ajustement")
    product_name: Optional[str] = Field(default=None, description="Nom du produit")

    class Config:
        from_attributes = True


class StockAdjustment(StockAdjustmentOut):
    """Ajustement de stock complet (pour compatibilité)."""

    pass


class StockOut(BaseModel):
    """Stock d'un produit."""

    product_id: int = Field(..., description="ID du produit")
    ref: Optional[str] = Field(default=None, description="Référence")
    name: str = Field(..., description="Nom du produit")
    category: Optional[str] = Field(default=None, description="Catégorie")
    unit: str = Field(..., description="Unité")
    stock: float = Field(..., description="Stock actuel")
    value: Optional[float] = Field(default=None, description="Valeur du stock")

    class Config:
        from_attributes = True
