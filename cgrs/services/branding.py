"""Personnalisation (nom, sous-titre, logo) : valeurs par défaut et validations. Sans base ni serveur."""

DEFAULT_NAME = "Cantine"
NAME_MAX = 60
SUBTITLE_MAX = 80
LOGO_MAX_BYTES = 512 * 1024


def clean_name(value):
    """Nom affiché : espaces superflus retirés, nom par défaut s'il est vide, 60 caractères au plus."""
    name = " ".join((value or "").split())
    return name[:NAME_MAX] if name else DEFAULT_NAME


def clean_subtitle(value):
    """Sous-titre affiché (facultatif) : 80 caractères au plus."""
    return " ".join((value or "").split())[:SUBTITLE_MAX]


def image_type(data: bytes):
    """Type MIME d'une image PNG, JPEG ou WebP reconnue à son contenu (jamais à son nom) ; None sinon.

    Le SVG est refusé exprès : il peut contenir des scripts.
    """
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
