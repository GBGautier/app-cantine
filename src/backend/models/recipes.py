"""Modèles pour les recettes."""

from typing import Optional

from pydantic import BaseModel, Field


class RecipeItemBase(BaseModel):
    """Base pour les éléments de recette."""

    product_id: Optional[int] = Field(default=None, description="ID du produit")
    label: Optional[str] = Field(default=None, description="Libellé")
    qty_maternelle: Optional[float] = Field(default=None, description="Quantité pour maternelle (g)")
    qty_elementaire: Optional[float] = Field(
        default=None, description="Quantité pour élémentaire (g)"
    )
    qty_adulte: Optional[float] = Field(default=None, description="Quantité pour adulte (g)")
    qty_servi: Optional[float] = Field(default=None, description="Quantité servie")
    qty_commander: Optional[float] = Field(default=None, description="Quantité à commander")
    unit: Optional[str] = Field(default=None, description="Unité")
    principal: bool = Field(default=False, description="Ingrédient principal")
    intitule_gemrcn: Optional[str] = Field(default=None, description="Intitulé GEMRCN")


class RecipeItem(RecipeItemBase):
    """Élément de recette."""

    id: int = Field(..., description="ID de l'élément")
    recipe_id: int = Field(..., description="ID de la recette")
    product_name: Optional[str] = Field(default=None, description="Nom du produit")
    product_unit: Optional[str] = Field(default=None, description="Unité du produit")
    unit_price: Optional[float] = Field(default=None, description="Prix unitaire")

    class Config:
        from_attributes = True


class RecipeBase(BaseModel):
    """Base pour les modèles recette."""

    name: str = Field(..., description="Nom de la recette")
    categorie: Optional[str] = Field(default=None, description="Catégorie")
    description: Optional[str] = Field(default=None, description="Description")
    nb_maternelles: int = Field(default=0, description="Nombre de maternelles")
    nb_elementaires: int = Field(default=0, description="Nombre d'élémentaires")
    nb_adultes: int = Field(default=0, description="Nombre d'adultes")
    items: list[RecipeItemBase] = Field(default_factory=list, description="Éléments de la recette")


class RecipeCreate(RecipeBase):
    """Création d'une nouvelle recette."""

    pass


class RecipeEdit(BaseModel):
    """Édition d'une recette."""

    name: Optional[str] = Field(default=None, description="Nom de la recette")
    categorie: Optional[str] = Field(default=None, description="Catégorie")
    description: Optional[str] = Field(default=None, description="Description")
    nb_maternelles: Optional[int] = Field(default=None, description="Nombre de maternelles")
    nb_elementaires: Optional[int] = Field(default=None, description="Nombre d'élémentaires")
    nb_adultes: Optional[int] = Field(default=None, description="Nombre d'adultes")
    items: Optional[list[RecipeItemBase]] = Field(default=None, description="Éléments de la recette")


class RecipeOut(RecipeBase):
    """Recette en sortie."""

    id: int = Field(..., description="ID de la recette")
    created: str = Field(..., description="Date de création")

    class Config:
        from_attributes = True


class Recipe(RecipeOut):
    """Recette complète (pour compatibilité)."""

    pass
