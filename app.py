"""Point d'entrée ASGI : `uvicorn app:app` (et `from app import app` dans main.py).

L'application est assemblée dans le package cgrs/ (voir cgrs/application.py).
"""

from cgrs.application import app  # noqa: F401
