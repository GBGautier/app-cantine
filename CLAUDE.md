# Règles du dépôt

- Toute évolution visible par l'utilisateur (page, carte de Paramètres, outil de l'assistant, comportement de
  l'import PDF, indicateur) met à jour `docs/GUIDE.md` dans le même commit : la section concernée, la ligne
  « Dernière mise à jour » et la liste « Évolutions depuis la présentation ». `tests/test_guide.py` vérifie la couverture.
- La présentation PDF `docs/guide-application.pdf` est générée, pas éditée à la main : après toute évolution visible
  (page, fenêtre, Paramètres, assistant…), adapter les diapositives de `docs/generer_guide.py` si besoin, lancer
  `python docs/generer_guide.py` (nécessite Playwright + Chromium ; l'appli est photographiée sur des données de
  démonstration) et valider le PDF et `docs/guide-application.empreinte` dans le même commit.
  `tests/test_guide.py` échoue si l'interface a changé sans régénération.
- Tests : `pytest -q` (dont `tests/ui`), `ruff check . && ruff format --check .` doivent passer avant de pousser.
- Interface et documentation en français.
