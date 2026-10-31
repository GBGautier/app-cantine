"""Métadonnées pour le frontend (listes de valeurs, indicateurs)."""

from fastapi import APIRouter

from cgrs.constants import CATEGORIES, DAYS, GAMMES, LOCAL, ORDER_METHODS, PROVENANCES, ROLES
from cgrs.security import ANY


router = APIRouter()


def metric_options():
    opts = [
        ("bio", "% bio"),
        ("egalim", "% EGalim"),
        ("local", "% local (CC Nozay, 44, Pays de la Loire)"),
        ("direct", "% direct producteur"),
        ("price_per_meal", "Prix / repas HT (€) – coût matières ÷ convives"),
    ]
    opts += [
        (f"label:{k}", f"% label : {v}") for k, v in (("bio", "bio"), ("autre", "autre label"), ("sans", "sans label"))
    ]
    opts += [(f"provenance:{k}", f"% provenance : {v}") for k, v in PROVENANCES.items()]
    opts += [(f"gamme:{k}", f"% gamme : {v}") for k, v in GAMMES.items()]
    return opts


@router.get("/api/meta")
def meta(user: dict = ANY):
    return {
        "provenances": PROVENANCES,
        "gammes": GAMMES,
        "categories": CATEGORIES,
        "local": LOCAL,
        "metrics": metric_options(),
        "days": DAYS,
        "order_methods": ORDER_METHODS,
        "roles": ROLES,
    }
