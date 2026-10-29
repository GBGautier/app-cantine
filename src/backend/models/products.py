"""Modèles pour les produits."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LabelEgalim(str, Enum):
    """Labels EGalim."""

    BIO = "bio"
    AUTRE = "autre"
    SANS = "sans"


class Provenance(str, Enum):
    """Provenances."""

    CC_NOZAY = "cc_nozay"
    LOIRE_ATLANTIQUE = "loire_atlantique"
    PAYS_LOIRE = "pays_loire"
    FRANCE = "france"
    UE = "ue"
    INTERNATIONAL = "international"


class Gamme(str, Enum):
    """Gammes de produits."""

    FRAIS_BRUT = "1"
    CONSERVES = "2"
    SURGELES = "3"
    CRU_PRET_EMPLOI = "4"
    CUIT_SOUS_VIDE = "5"
    DESHYDRATES = "6"


class ProductBase(BaseModel):
    """Base pour les modèles produit."""

    ref: Optional[str] = Field(default=None, description="Référence du produit")
    name: str = Field(..., description="Nom du produit")
    supplier_id: Optional[int] = Field(default=None, description="ID du fournisseur")
    category: Optional[str] = Field(default=None, description="Catégorie")
    gamme: Optional[Gamme] = Field(default=None, description="Gamme")
    label_egalim: LabelEgalim = Field(default=LabelEgalim.BIO, description="Label EGalim")
    label_detail: Optional[str] = Field(default=None, description="Détail du label")
    provenance: Optional[Provenance] = Field(default=None, description="Provenance")
    direct_producteur: bool = Field(default=False, description="Produit du producteur direct")
    commerce_equitable: bool = Field(default=False, description="Commerce équitable")
    avoid: bool = Field(default=False, description="À éviter")
    favorite: bool = Field(default=False, description="Favori")
    unit: str = Field(default="kg", description="Unité")
    unit_price: Optional[float] = Field(default=None, description="Prix unitaire")
    datasheet: Optional[str] = Field(default=None, description="Fiche technique")
    notes: Optional[str] = Field(default=None, description="Notes")


class ProductCreate(ProductBase):
    """Création d'un nouveau produit."""

    pass


class ProductEdit(BaseModel):
    """Édition d'un produit."""

    ref: Optional[str] = Field(default=None, description="Référence du produit")
    name: Optional[str] = Field(default=None, description="Nom du produit")
    supplier_id: Optional[int] = Field(default=None, description="ID du fournisseur")
    category: Optional[str] = Field(default=None, description="Catégorie")
    gamme: Optional[Gamme] = Field(default=None, description="Gamme")
    label_egalim: Optional[LabelEgalim] = Field(default=None, description="Label EGalim")
    label_detail: Optional[str] = Field(default=None, description="Détail du label")
    provenance: Optional[Provenance] = Field(default=None, description="Provenance")
    direct_producteur: Optional[bool] = Field(default=None, description="Produit du producteur direct")
    commerce_equitable: Optional[bool] = Field(default=None, description="Commerce équitable")
    avoid: Optional[bool] = Field(default=None, description="À éviter")
    favorite: Optional[bool] = Field(default=None, description="Favori")
    unit: Optional[str] = Field(default=None, description="Unité")
    unit_price: Optional[float] = Field(default=None, description="Prix unitaire")
    datasheet: Optional[str] = Field(default=None, description="Fiche technique")
    notes: Optional[str] = Field(default=None, description="Notes")


class ProductOut(ProductBase):
    """Produit en sortie."""

    id: int = Field(..., description="ID du produit")
    supplier_name: Optional[str] = Field(default=None, description="Nom du fournisseur")

    class Config:
        from_attributes = True


class Product(ProductOut):
    """Produit complet (pour compatibilité)."""

    pass
