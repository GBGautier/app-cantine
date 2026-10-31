"""Sauvegarde et restauration de toutes les données."""

import os
import sqlite3
import tempfile
import zipfile
from datetime import date as date_cls, datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

import db
import paths
from cgrs.config import UPLOADS
from cgrs.security import ADMIN


router = APIRouter()


@router.get("/api/backup")
def backup(user: dict = ADMIN):
    """Archive .zip : base de données (copie cohérente) + tous les PDF et fiches techniques."""
    fd, tmp_zip = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    fd, tmp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    src, dst = sqlite3.connect(db.DB_PATH), sqlite3.connect(tmp_db)
    try:
        src.backup(dst)
        dst.execute("DELETE FROM sessions")   # on ne sauvegarde pas les connexions en cours
        dst.commit()
    finally:
        src.close()
        dst.close()
    with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp_db, "cantine.db")
        for p in sorted(UPLOADS.rglob("*")):
            if p.is_file():
                z.write(p, f"uploads/{p.relative_to(UPLOADS).as_posix()}")
        z.writestr("LISEZ-MOI.txt", (
            f"Sauvegarde CGRS du {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            "Contenu : cantine.db (toutes les données, y compris les comptes utilisateurs et leurs mots de passe chiffrés)\n"
            "et uploads/ (PDF des réceptions, fiches techniques).\n\n"
            "Ce fichier contient des données sensibles : ne le partagez pas.\n\n"
            "Restauration : arrêter l'application, remplacer cantine.db et le dossier uploads/ du dossier de l'application\n"
            "par ceux de cette archive, puis relancer l'application.\n"))
    os.remove(tmp_db)
    return FileResponse(tmp_zip, media_type="application/zip",
                        filename=f"cgrs-sauvegarde-{date_cls.today().isoformat()}.zip",
                        background=BackgroundTask(os.remove, tmp_zip))


MAX_RESTORE = 500 * 1024 * 1024
RESTORE_TABLES = {"suppliers", "products", "orders", "order_lines", "meals", "users", "settings"}


@router.post("/api/restore")
async def restore(file: UploadFile = File(...), user: dict = ADMIN):
    """Restaure une sauvegarde (.zip produit par « Sauvegarder toutes les données »).

    La base actuelle est remplacée par celle de l'archive (une copie de sécurité de l'ancienne est conservée dans
    le dossier « sauvegardes-auto »), les PDF et fiches techniques de l'archive sont remis dans uploads/.
    """
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Fichier .zip attendu (sauvegarde de l'application)")
    fd, tmp_zip = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    tmp_dir = tempfile.mkdtemp()
    try:
        size = 0
        with open(tmp_zip, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_RESTORE:
                    raise HTTPException(413, "Archive trop volumineuse (500 Mo maximum)")
                f.write(chunk)
        try:
            z = zipfile.ZipFile(tmp_zip)
        except zipfile.BadZipFile:
            raise HTTPException(400, "Ce fichier n'est pas une archive .zip valide") from None
        with z:
            if "cantine.db" not in z.namelist():
                raise HTTPException(400, "Archive invalide : cantine.db est absent (ce n'est pas une sauvegarde CGRS)")
            new_db = Path(tmp_dir) / "cantine.db"
            with z.open("cantine.db") as src, open(new_db, "wb") as dst:
                dst.write(src.read())
            # contrôle de la base de l'archive avant de toucher à quoi que ce soit
            try:
                c = sqlite3.connect(new_db)
                ok = c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                admins = c.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] if "users" in tables else 0
                c.close()
            except sqlite3.DatabaseError:
                raise HTTPException(400, "La base de données de l'archive est illisible") from None
            if not ok or not RESTORE_TABLES <= tables:
                raise HTTPException(400, "La base de l'archive est incomplète ou abîmée : restauration annulée")
            if not admins:
                raise HTTPException(400, "La sauvegarde ne contient aucun administrateur : restauration annulée")
            # copie de sécurité de l'état actuel
            safe_dir = paths.BACKUPS
            safe_dir.mkdir(exist_ok=True)
            safe = safe_dir / f"avant-restauration-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            s_, d_ = sqlite3.connect(db.DB_PATH), sqlite3.connect(safe)
            try:
                s_.backup(d_)
            finally:
                s_.close()
                d_.close()
            # remplacement du contenu de la base en place
            s_, d_ = sqlite3.connect(new_db), sqlite3.connect(db.DB_PATH)
            try:
                s_.backup(d_)
            finally:
                s_.close()
                d_.close()
            db.init()   # ajoute les colonnes manquantes si la sauvegarde vient d'une ancienne version
            files = 0
            for name in z.namelist():
                parts = Path(name).parts
                if len(parts) == 2 and parts[0] == "uploads" and parts[1] not in ("", ".", "..") and not name.endswith("/"):
                    dest = UPLOADS / Path(parts[1]).name
                    with z.open(name) as src, open(dest, "wb") as out:
                        out.write(src.read())
                    files += 1
        return {"ok": True, "files": files, "safety_copy": safe.name}
    finally:
        os.remove(tmp_zip)
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
