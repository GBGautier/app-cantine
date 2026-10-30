"""Accès aux fichiers envoyés."""

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from cgrs.config import UPLOADS
from cgrs.security import READ
from cgrs.uploads import ALLOWED_EXT


router = APIRouter()


@router.get("/api/files/{name}")
def get_file(name: str, user: dict = READ):
    p = UPLOADS / Path(name).name
    if not p.is_file() or p.suffix.lower() not in ALLOWED_EXT:
        raise HTTPException(404, "Fichier introuvable")
    pretty = re.sub(r"^(?:fiche_)?[0-9a-f]{12}_", "", p.name)
    return FileResponse(p, filename=pretty, content_disposition_type="inline")
