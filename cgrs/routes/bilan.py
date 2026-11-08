"""Bilan mensuel des approvisionnements (un mois comparé au cumul depuis septembre)."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from cgrs.security import ANY
from cgrs.services import bilan as svc
from cgrs.services.bilan_periode import bilan_periode


router = APIRouter()


@router.get("/api/bilan")
def bilan(mois: Optional[str] = None, user: dict = ANY):
    """Bilan du mois « AAAA-MM » (par défaut : le dernier mois avec des achats ou des repas) et du cumul depuis septembre.

    Pour le profil « stats », les montants et les prix sont retirés côté serveur.
    """
    try:
        return svc.bilan(mois or svc.mois_par_defaut(), masquer_prix=user["role"] == "stats")
    except svc.MoisInvalide as e:
        raise HTTPException(422, str(e)) from None


@router.get("/api/bilan/periode")
def bilan_de_la_periode(date_from: Optional[str] = None, date_to: Optional[str] = None, user: dict = ANY):
    """Indicateurs du CRT sur la période choisie dans la page Statistiques, comparés aux engagements du marché."""
    return bilan_periode(date_from or None, date_to or None, masquer_prix=user["role"] == "stats")
