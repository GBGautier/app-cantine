"""Tarif de vente d'un repas (utilisé par le bilan mensuel de l'assistant)."""

from .conftest import aller


def test_tarif_repas_dans_les_parametres(admin, api):
    page = admin
    aller(page, "Paramètres")
    champ = page.locator("input[type=number][step='0.01']").first
    champ.fill("2.5")
    champ.locator("xpath=following-sibling::button").click()
    page.wait_for_timeout(300)
    assert api.get("/api/settings")["tarif_repas"] == 2.5
