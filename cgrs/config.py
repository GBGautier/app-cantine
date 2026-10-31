"""Chemins de l'application (dossier statique et dossier des fichiers envoyés)."""

import paths


STATIC = paths.STATIC
UPLOADS = paths.UPLOADS
UPLOADS.mkdir(parents=True, exist_ok=True)   # paths.py ne crée que le dossier de données : sans ceci, le premier envoi de PDF échouait (erreur 500)
