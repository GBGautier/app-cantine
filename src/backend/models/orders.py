"""Modèles pour les commandes et réceptions."""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderKind(str, Enum):
    """Type de document."""

    LIVRAISON = "livraison"
    FACTURE = "facture"


class OrderLineBase(BaseModel):
    """Base pour les lignes de commande."""

    product_id: Optional[int] = Field(default=None, description="ID du produit")
    ref: Optional[str] = Field(default=None, description="Référence")
    label: Optional[str] = Field(default=None, description="Libellé")
    qty: Optional[float] = Field(default=None, description="Quantité")
    unit: Optional[str] = Field(default=None, description="Unité")
    unit_price: Optional[float] = Field(default=None, description="Prix unitaire")
    total_ht: Optional[float] = Field(default=None, description="Total HT")


class OrderLine(OrderLineBase):
    """Ligne de commande."""

    id: int = Field(..., description="ID de la ligne")
    order_id: int = Field(..., description="ID de la commande")
    product_name: Optional[str] = Field(default=None, description="Nom du produit")

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    """Base pour les modèles commande."""

    supplier_id: Optional[int] = Field(default=None, description="ID du fournisseur")
    ref: Optional[str] = Field(default=None, description="Référence")
    kind: OrderKind = Field(default=OrderKind.LIVRAISON, description="Type de document")
    date: Optional[str] = Field(default=None, description="Date (AAAA-MM-JJ)")
    delivery_date: Optional[str] = Field(default=None, description="Date de livraison")
    total_ht: Optional[float] = Field(default=None, description="Total HT")
    source_file: Optional[str] = Field(default=None, description="Fichier source")
    notes: Optional[str] = Field(default=None, description="Notes")


class OrderCreate(OrderBase):
    """Création d'une nouvelle commande."""

    lines: list[OrderLineBase] = Field(default_factory=list, description="Lignes de commande")


class OrderEdit(BaseModel):
    """Édition d'une commande."""

    supplier_id: Optional[int] = Field(default=None, description="ID du fournisseur")
    ref: Optional[str] = Field(default=None, description="Référence")
    kind: Optional[OrderKind] = Field(default=None, description="Type de document")
    date: Optional[str] = Field(default=None, description="Date (AAAA-MM-JJ)")
    delivery_date: Optional[str] = Field(default=None, description="Date de livraison")
    total_ht: Optional[float] = Field(default=None, description="Total HT")
    source_file: Optional[str] = Field(default=None, description="Fichier source")
    notes: Optional[str] = Field(default=None, description="Notes")
    lines: Optional[list[OrderLineBase]] = Field(default=None, description="Lignes de commande")


class OrderOut(OrderBase):
    """Commande en sortie."""

    id: int = Field(..., description="ID de la commande")
    supplier_name: Optional[str] = Field(default=None, description="Nom du fournisseur")
    lines: list[OrderLine] = Field(default_factory=list, description="Lignes de commande")

    class Config:
        from_attributes = True


class Order(OrderOut):
    """Commande complète (pour compatibilité)."""

    pass
