"""Mod\u00e8les pour les fournisseurs."""

import json
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SupplierBase(BaseModel):
    """Base pour les mod\u00e8les fournisseur."""

    name: str = Field(..., description="Nom du fournisseur")
    contact: Optional[str] = Field(default=None, description="Contact principal")
    email: Optional[str] = Field(default=None, description="Email")
    phone: Optional[str] = Field(default=None, description="T\u00e9l\u00e9phone")
    address: Optional[str] = Field(default=None, description="Adresse")
    siret: Optional[str] = Field(default=None, description="SIRET")
    delivery_days: Optional[str] = Field(default=None, description="Jours de livraison (JSON)")
    franco: Optional[float] = Field(default=None, description="Montant minimum pour livraison gratuite")
    order_method: Optional[str] = Field(default=None, description="M\u00e9thode de commande")
    order_url: Optional[str] = Field(default=None, description="URL de commande")
    categories: Optional[str] = Field(default=None, description="Cat\u00e9gories de produits (JSON)")
    local_default: Optional[str] = Field(default=None, description="Provenance par d\u00e9faut")
    direct_producteur: bool = Field(default=False, description="Fournisseur producteur direct")
    parser_regex: Optional[str] = Field(default=None, description="Regex pour parser les PDF")
    keywords: Optional[str] = Field(default=None, description="Mots-cl\u00e9s pour la reconnaissance")
    notes: Optional[str] = Field(default=None, description="Notes")


class SupplierCreate(SupplierBase):
    """Cr\u00e9ation d'un nouveau fournisseur."""

    pass


class SupplierEdit(BaseModel):
    """\u00c9dition d'un fournisseur."""

    name: Optional[str] = Field(default=None, description="Nom du fournisseur")
    contact: Optional[str] = Field(default=None, description="Contact principal")
    email: Optional[str] = Field(default=None, description="Email")
    phone: Optional[str] = Field(default=None, description="T\u00e9l\u00e9phone")
    address: Optional[str] = Field(default=None, description="Adresse")
    siret: Optional[str] = Field(default=None, description="SIRET")
    delivery_days: Optional[str] = Field(default=None, description="Jours de livraison (JSON)")
    franco: Optional[float] = Field(default=None, description="Montant minimum pour livraison gratuite")
    order_method: Optional[str] = Field(default=None, description="M\u00e9thode de commande")
    order_url: Optional[str] = Field(default=None, description="URL de commande")
    categories: Optional[str] = Field(default=None, description="Cat\u00e9gories de produits (JSON)")
    local_default: Optional[str] = Field(default=None, description="Provenance par d\u00e9faut")
    direct_producteur: Optional[bool] = Field(default=None, description="Fournisseur producteur direct")
    parser_regex: Optional[str] = Field(default=None, description="Regex pour parser les PDF")
    keywords: Optional[str] = Field(default=None, description="Mots-cl\u00e9s pour la reconnaissance")
    notes: Optional[str] = Field(default=None, description="Notes")


class SupplierOut(SupplierBase):
    """Fournisseur en sortie."""

    id: int = Field(..., description="ID du fournisseur")

    @field_validator('delivery_days', 'categories', mode='before')
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


class Supplier(SupplierOut):
    """Fournisseur complet (pour compatibilit\u00e9)."""

    pass
