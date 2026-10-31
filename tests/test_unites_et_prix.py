"""Conversions d'unités et prix à une date : fonctions pures, testées sans base ni serveur."""

import pytest

from cgrs.services.prices import price_at
from cgrs.services.units import convert


@pytest.mark.parametrize(
    "qty, de, vers, attendu",
    [
        (1500, "g", "kg", 1.5),
        (2, "kg", "g", 2000),
        (250, "cl", "l", 2.5),
        (3, "pièces", "unité", 3),
        (5, "kg", "l", None),  # masse et volume : incompatibles
        (5, "kg", "colis", None),
        (5, "", "kg", 5),  # unité absente : on garde la quantité
        (5, "kg", None, 5),
        (None, "kg", "g", None),
        (2, "tonneau", "TONNEAU", 2),  # unité inconnue = même unité, sans tenir compte de la casse
        (2, "tonneau", "fût", None),
    ],
)
def test_convert(qty, de, vers, attendu):
    resultat = convert(qty, de, vers)
    if attendu is None:
        assert resultat is None
    else:
        assert resultat == pytest.approx(attendu)


HIST = {7: [("2026-01-10", 2.0), ("2026-03-01", 2.5), ("2026-06-01", 3.0)]}


@pytest.mark.parametrize(
    "jour, attendu",
    [
        ("2026-01-10", 2.0),
        ("2026-02-15", 2.0),  # dernier relevé connu à cette date
        ("2026-03-01", 2.5),
        ("2030-01-01", 3.0),
        ("2025-01-01", 2.0),  # avant le premier relevé : le premier prix connu
        (None, 2.0),
    ],
)
def test_price_at(jour, attendu):
    assert price_at(HIST, 7, jour, 99.0) == attendu


def test_price_at_sans_historique_prend_le_prix_courant():
    assert price_at(HIST, 8, "2026-01-01", 1.25) == 1.25
    assert price_at({}, 8, "2026-01-01", None) is None
