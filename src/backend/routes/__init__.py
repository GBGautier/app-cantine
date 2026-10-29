"""Routes de l'application CGRS.

Ce module contient toutes les routes API de l'application,
organisées par domaine fonctionnel.
"""

from .action_log import router as action_log_router
from .auth import router as auth_router
from .backup import router as backup_router
from .commitments import router as commitments_router
from .convives_defaults import router as convives_defaults_router
from .export import router as export_router
from .files import router as files_router
from .grammages import router as grammages_router
from .grammages_rows import router as grammages_rows_router
from .meals import router as meals_router
from .meta import router as meta_router
from .orders import router as orders_router
from .products import router as products_router
from .recipes import router as recipes_router
from .settings import router as settings_router
from .stock import router as stock_router
from .stocks import router as stocks_router
from .suppliers import router as suppliers_router
from .users import router as users_router
from .stats import router as stats_router

__all__ = [
    "action_log_router",
    "auth_router",
    "backup_router",
    "commitments_router",
    "convives_defaults_router",
    "export_router",
    "files_router",
    "grammages_router",
    "grammages_rows_router",
    "meals_router",
    "meta_router",
    "orders_router",
    "products_router",
    "recipes_router",
    "settings_router",
    "stock_router",
    "stocks_router",
    "suppliers_router",
    "users_router",
    "stats_router",
]
