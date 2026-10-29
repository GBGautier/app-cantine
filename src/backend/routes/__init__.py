"""Routes de l'application CGRS.

Ce module contient toutes les routes API de l'application,
organisées par domaine fonctionnel.
"""

from .auth import router as auth_router
from .backup import router as backup_router
from .commitments import router as commitments_router
from .export import router as export_router
from .files import router as files_router
from .grammages import router as grammages_router
from .meals import router as meals_router
from .orders import router as orders_router
from .products import router as products_router
from .recipes import router as recipes_router
from .settings import router as settings_router
from .stocks import router as stocks_router
from .suppliers import router as suppliers_router
from .users import router as users_router

__all__ = [
    "auth_router",
    "backup_router",
    "commitments_router",
    "export_router",
    "files_router",
    "grammages_router",
    "meals_router",
    "orders_router",
    "products_router",
    "recipes_router",
    "settings_router",
    "stocks_router",
    "suppliers_router",
    "users_router",
]
