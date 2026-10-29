"""Routes pour la gestion des sauvegardes."""

import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from src.backend.utils import ADMIN, log_action
from src.backend.config import get_database_path, get_backups_dir, get_uploads_dir

router = APIRouter(prefix="/api/backup", tags=["Sauvegardes"])


@router.post("/create")
async def create_backup(user: dict = Depends(ADMIN)):
    """Crée une sauvegarde de la base de données et des fichiers."""
    db_path = get_database_path()
    uploads_dir = get_uploads_dir()
    backups_dir = get_backups_dir()
    
    if not db_path.exists():
        raise HTTPException(400, "Base de données introuvable")
    
    # Créer un nom de fichier unique
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"cgrs_backup_{timestamp}.zip"
    backup_path = backups_dir / backup_name
    
    # Créer l'archive
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Ajouter la base de données
        zipf.write(db_path, arcname="cantine.db")
        
        # Ajouter les fichiers uploadés
        if uploads_dir.exists():
            for file in uploads_dir.iterdir():
                if file.is_file():
                    zipf.write(file, arcname=f"uploads/{file.name}")
    
    log_action(user, "create", "backup", 0, f"Sauvegarde créée : {backup_name}")
    return {"ok": True, "filename": backup_name}


@router.get("/download/{filename}")
async def download_backup(filename: str, user: dict = Depends(ADMIN)):
    """Télécharge une sauvegarde."""
    backups_dir = get_backups_dir()
    backup_path = backups_dir / filename
    
    if not backup_path.exists():
        raise HTTPException(404, "Sauvegarde introuvable")
    
    return FileResponse(
        backup_path,
        filename=filename,
        content_disposition_type="attachment"
    )


@router.get("/list")
async def list_backups(user: dict = Depends(ADMIN)):
    """Liste toutes les sauvegardes."""
    backups_dir = get_backups_dir()
    backups = []
    
    if backups_dir.exists():
        for file in sorted(backups_dir.iterdir(), reverse=True):
            if file.is_file() and file.suffix == ".zip":
                backups.append({
                    "filename": file.name,
                    "size": file.stat().st_size,
                    "created": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
    
    return backups


@router.delete("/{filename}")
async def delete_backup(filename: str, user: dict = Depends(ADMIN)):
    """Supprime une sauvegarde."""
    backups_dir = get_backups_dir()
    backup_path = backups_dir / filename
    
    if not backup_path.exists():
        raise HTTPException(404, "Sauvegarde introuvable")
    
    backup_path.unlink()
    log_action(user, "delete", "backup", 0, f"Sauvegarde supprimée : {filename}")
    return {"ok": True}
