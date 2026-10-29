"""Routes pour la gestion des fichiers."""

import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.backend.utils import READ, EDIT
from src.backend.config import get_uploads_dir

router = APIRouter(prefix="/api/files", tags=["Fichiers"])

# Extensions autorisées
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx", ".odt", ".ods", ".txt"}
MAX_UPLOAD = 25 * 1024 * 1024


@router.get("/{name}")
async def get_file(name: str, user: dict = Depends(READ)):
    """Récupère un fichier."""
    uploads_dir = get_uploads_dir()
    p = uploads_dir / Path(name).name
    if not p.is_file() or p.suffix.lower() not in ALLOWED_EXT:
        raise HTTPException(404, "Fichier introuvable")
    pretty = re.sub(r"^(?:fiche_)?[0-9a-f]{12}_", "", p.name)
    return FileResponse(p, filename=pretty, content_disposition_type="inline")
