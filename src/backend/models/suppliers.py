"""Modèles pour les fournisseurs."""

from typing import Optional

from pydantic import BaseModel, Field


class SupplierBase(BaseModel):
    """Base pour les modèles fournisseur."""

    name: str = Field(..., description="Nom du fournisseur")
    contact: Optional[str] = Field(default=None, description="Contact principal")
    email: Optional[str] = Field(default=None, description="Email")
    phone: Optional[str] = Field(default=None, description="Téléphone")
    address: Optional[str] = Field(default=None, description="Adresse")
    siret: Optional[str] = Field(default=None, description="SIRET")
    delivery_days: Optional[str] = Field(default=None, description="Jours de livraison (JSON)")
    franco: Optional[float] = Field(default=None, description="Montant minimum pour livraison gratuite")
    order_method: Optional[str] = Field(default=None, description="Méthode de commande")
    order_url: Optional[str] = Field(default=None, description="URL de commande")
    categories: Optional[str] = Field(default=None, description="Catégories de produits (JSON)")
    local_default: Optional[str] = Field(default=None, description="Provenance par défaut")
    direct_producteur: bool = Field(default=False, description="Fournisseur producteur direct")
    parser_regex: Optional[str] = Field(default=None, description="Regex pour parser les PDF")
    keywords: Optional[str] = Field(default=None, description="Mots-clés pour la reconnaissance")
    notes: Optional[str] = Field(default=None, description="Notes")


class SupplierCreate(SupplierBase):
    """Création d'un nouveau fournisseur."""

    pass


class SupplierEdit(BaseModel):
    """Édition d'un fournisseur."""

    name: Optional[str] = Field(default=None, description="Nom du fournisseur")
    contact: Optional[str] = Field(default=None, description="Contact principal")
    email: Optional[str] = Field(default=None, description="Email")
    phone: Optional[str] = Field(default=None, description="Téléphone")
    address: Optional[str] = Field(default=None, description="Adresse")
    siret: Optional[str] = Field(default=None, description="SIRET")
    delivery_days: Optional[str] = Field(default=None, description="Jours de livraison (JSON)")
    franco: Optional[float] = Field(default=None, description="Montant minimum pour livraison gratuite")
    order_method: Optional[str] = Field(default=None, description="Méthode de commande")
    order_url: Optional[str] = Field(default=None, description="URL de commande")
    categories: Optional[str] = Field(default=None, description="Catégories de produits (JSON)")
    local_default: Optional[str] = Field(default=None, description="Provenance par défaut")
    direct_producteur: Optional[bool] = Field(default=None, description="Fournisseur producteur direct")
    parser_regex: Optional[str] = Field(default=None, description="Regex pour parser les PDF")
    keywords: Optional[str] = Field(default=None, description="Mots-clés pour la reconnaissance")
    notes: Optional[str] = Field(default=None, description="Notes")


class SupplierOut(SupplierBase):
    """Fournisseur en sortie."""

    id: int = Field(..., description="ID du fournisseur")

    class Config:
        from_attributes = True


class Supplier(SupplierOut):
    """Fournisseur complet (pour compatibilité)."""

    pass
