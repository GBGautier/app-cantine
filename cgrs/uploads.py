"""Enregistrement des fichiers envoyés (PDF des réceptions, fiches techniques)."""

import re
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile

from cgrs.config import UPLOADS


ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx", ".odt", ".ods", ".txt"}
MAX_UPLOAD = 25 * 1024 * 1024


async def save_upload(file: UploadFile, prefix="", allowed=ALLOWED_EXT) -> str:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Type de fichier non accepté ({ext or 'sans extension'})")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(file.filename).stem)[:80] + ext
    name = f"{prefix}{secrets.token_hex(6)}_{safe}"
    dest = UPLOADS / name
    size = 0
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "Fichier trop volumineux (25 Mo maximum)")
            f.write(chunk)
    return name
