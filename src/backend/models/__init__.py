"""Modèles de données de l'application CGRS.

Ce module contient tous les modèles Pydantic utilisés pour la validation
des données entrantes et sortantes de l'API.
"""

from .auth import (
    Credentials,
    PasswordChange,
    UserCreate,
    UserEdit,
    UserOut,
    UserRole,
)
from .base import BaseResponse
from .commitments import CommitmentCreate, CommitmentEdit, CommitmentOut
from .meals import (
    Meal,
    MealCreate,
    MealEdit,
    MealItem,
    MealOut,
    ShoppingListItem,
)
from .orders import (
    Order,
    OrderCreate,
    OrderEdit,
    OrderKind,
    OrderLine,
    OrderOut,
)
from .products import (
    Product,
    ProductCreate,
    ProductEdit,
    ProductOut,
)
from .recipes import (
    Recipe,
    RecipeCreate,
    RecipeEdit,
    RecipeItem,
    RecipeOut,
)
from .stocks import (
    StockAdjustment,
    StockAdjustmentCreate,
    StockAdjustmentOut,
    StockOut,
)
from .suppliers import (
    Supplier,
    SupplierCreate,
    SupplierEdit,
    SupplierOut,
)

__all__ = [
    # Base
    "BaseResponse",
    # Auth
    "Credentials",
    "PasswordChange",
    "UserCreate",
    "UserEdit",
    "UserOut",
    "UserRole",
    # Suppliers
    "Supplier",
    "SupplierCreate",
    "SupplierEdit",
    "SupplierOut",
    # Products
    "Product",
    "ProductCreate",
    "ProductEdit",
    "ProductOut",
    # Orders
    "Order",
    "OrderCreate",
    "OrderEdit",
    "OrderKind",
    "OrderLine",
    "OrderOut",
    # Meals
    "Meal",
    "MealCreate",
    "MealEdit",
    "MealItem",
    "MealOut",
    "ShoppingListItem",
    # Recipes
    "Recipe",
    "RecipeCreate",
    "RecipeEdit",
    "RecipeItem",
    "RecipeOut",
    # Stocks
    "StockAdjustment",
    "StockAdjustmentCreate",
    "StockAdjustmentOut",
    "StockOut",
    # Commitments
    "CommitmentCreate",
    "CommitmentEdit",
    "CommitmentOut",
]
