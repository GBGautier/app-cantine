"""Modèles pour les repas."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MealItemBase(BaseModel):
    """Base pour les éléments de repas."""

    product_id: int = Field(..., description="ID du produit")
    qty: float = Field(..., description="Quantité")
    unit: Optional[str] = Field(default=None, description="Unité")
    prix_reel: Optional[float] = Field(default=None, description="Prix réel")


class MealItem(MealItemBase):
    """Élément de repas."""

    id: int = Field(..., description="ID de l'élément")
    meal_id: int = Field(..., description="ID du repas")
    product_name: Optional[str] = Field(default=None, description="Nom du produit")
    unit_price: Optional[float] = Field(default=None, description="Prix unitaire du produit")

    class Config:
        from_attributes = True


class MealBase(BaseModel):
    """Base pour les modèles repas."""

    date: str = Field(..., description="Date (AAAA-MM-JJ)")
    nb_maternelles: int = Field(default=0, description="Nombre de maternelles")
    nb_elementaires: int = Field(default=0, description="Nombre d'élémentaires")
    nb_adultes: int = Field(default=0, description="Nombre d'adultes")
    notes: Optional[str] = Field(default=None, description="Notes")
    entree: Optional[str] = Field(default=None, description="Entrée")
    plat: Optional[str] = Field(default=None, description="Plat")
    accompagnement: Optional[str] = Field(default=None, description="Accompagnement")
    laitage: Optional[str] = Field(default=None, description="Laitage")
    dessert: Optional[str] = Field(default=None, description="Dessert")
    commentaire_post: Optional[str] = Field(default=None, description="Commentaire post-repas")
    modif_prevu: bool = Field(default=False, description="Modification prévue")
    statut: str = Field(default="prevu", description="Statut")
    recipe_entree: Optional[int] = Field(default=None, description="ID de la recette pour l'entrée")
    recipe_plat: Optional[int] = Field(default=None, description="ID de la recette pour le plat")
    recipe_accompagnement: Optional[int] = Field(
        default=None, description="ID de la recette pour l'accompagnement"
    )
    recipe_laitage: Optional[int] = Field(default=None, description="ID de la recette pour le laitage")
    recipe_dessert: Optional[int] = Field(default=None, description="ID de la recette pour le dessert")
    estimation: Optional[list] = Field(default=None, description="Estimation des coûts")
    items: list[MealItemBase] = Field(default_factory=list, description="Éléments du repas")

    @field_validator("nb_maternelles", "nb_elementaires", "nb_adultes")
    @classmethod
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("Les effectifs ne peuvent pas être négatifs")
        return v


class MealCreate(MealBase):
    """Création d'un nouveau repas."""

    pass


class MealEdit(BaseModel):
    """Édition d'un repas."""

    date: Optional[str] = Field(default=None, description="Date (AAAA-MM-JJ)")
    nb_maternelles: Optional[int] = Field(default=None, description="Nombre de maternelles")
    nb_elementaires: Optional[int] = Field(default=None, description="Nombre d'élémentaires")
    nb_adultes: Optional[int] = Field(default=None, description="Nombre d'adultes")
    notes: Optional[str] = Field(default=None, description="Notes")
    entree: Optional[str] = Field(default=None, description="Entrée")
    plat: Optional[str] = Field(default=None, description="Plat")
    accompagnement: Optional[str] = Field(default=None, description="Accompagnement")
    laitage: Optional[str] = Field(default=None, description="Laitage")
    dessert: Optional[str] = Field(default=None, description="Dessert")
    commentaire_post: Optional[str] = Field(default=None, description="Commentaire post-repas")
    modif_prevu: Optional[bool] = Field(default=None, description="Modification prévue")
    statut: Optional[str] = Field(default=None, description="Statut")
    recipe_entree: Optional[int] = Field(default=None, description="ID de la recette pour l'entrée")
    recipe_plat: Optional[int] = Field(default=None, description="ID de la recette pour le plat")
    recipe_accompagnement: Optional[int] = Field(
        default=None, description="ID de la recette pour l'accompagnement"
    )
    recipe_laitage: Optional[int] = Field(default=None, description="ID de la recette pour le laitage")
    recipe_dessert: Optional[int] = Field(default=None, description="ID de la recette pour le dessert")
    estimation: Optional[list] = Field(default=None, description="Estimation des coûts")
    items: Optional[list[MealItemBase]] = Field(default=None, description="Éléments du repas")


class MealOut(MealBase):
    """Repas en sortie."""

    id: int = Field(..., description="ID du repas")
    guests: int = Field(..., description="Nombre total de convives")

    class Config:
        from_attributes = True


class Meal(MealOut):
    """Repas complet (pour compatibilité)."""

    pass


class ShoppingListItem(BaseModel):
    """Élément de la liste de courses."""

    product_id: int = Field(..., description="ID du produit")
    label: str = Field(..., description="Libellé")
    category: str = Field(..., description="Catégorie")
    unit: str = Field(..., description="Unité")
    qty: float = Field(..., description="Quantité")

    class Config:
        from_attributes = True
