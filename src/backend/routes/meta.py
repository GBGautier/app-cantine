"""Route pour les métadonnées de l'application.

Cette route fournit les métadonnées nécessaires au frontend :
- Provenances
- Gammes
- Catégories
- Méthodes de commande
- Rôles
- Jours
- etc.
"""

from fastapi import APIRouter, Depends

from src.backend.utils import READ, PROVENANCES, GAMMES, CATEGORIES, DAYS, ORDER_METHODS, ROLES

router = APIRouter(prefix="/meta", tags=["Métadonnées"])


@router.get("/")
async def get_meta(user: dict = Depends(READ)):
    """Retourne les métadonnées de l'application."""
    return {
        "provenances": PROVENANCES,
        "gammes": GAMMES,
        "categories": CATEGORIES,
        "days": DAYS,
        "order_methods": ORDER_METHODS,
        "roles": ROLES,
        "metrics": [
            ("bio", "% bio"),
            ("egalim", "% EGalim"),
            ("local", "% local (CC Nozay, 44, Pays de la Loire)"),
            ("direct", "% direct producteur"),
            ("price_per_meal", "Prix / repas HT (€) — coût matières ÷ convives"),
        ] + [(f"label:{k}", f"% label : {v}") for k, v in (("bio", "bio"), ("autre", "autre label"), ("sans", "sans label"))]
        + [(f"provenance:{k}", f"% provenance : {v}") for k, v in PROVENANCES.items()]
        + [(f"gamme:{k}", f"% gamme : {v}") for k, v in GAMMES.items()],
    }
