"""Sauvegardes automatiques de la base de données, avec rotation.

Une copie cohérente (API de sauvegarde de SQLite, sans arrêter l'application) est faite au démarrage puis
périodiquement, dans le dossier « sauvegardes-auto ». Seules les copies `auto-AAAAMMJJ-HHMMSS.db` sont supprimées
par la rotation : les copies « avant-restauration-… » faites par la restauration ne sont jamais touchées.

Les PDF et fiches techniques (uploads/) ne sont pas recopiés ici : ils ne changent jamais une fois enregistrés, et la
sauvegarde complète de l'interface (« Sauvegarder toutes les données ») les inclut.
"""

import re
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

from cgrs import journal

log = journal.get("sauvegarde")

PATTERN = re.compile(r"^auto-\d{8}-\d{6}\.db$")


def list_backups(dest: Path) -> list[Path]:
    """Sauvegardes automatiques existantes, de la plus ancienne à la plus récente."""
    if not dest.is_dir():
        return []
    return sorted(p for p in dest.iterdir() if p.is_file() and PATTERN.match(p.name))


def make_backup(db_path: Path, dest: Path, now: datetime | None = None) -> Path:
    """Copie cohérente de la base dans `dest`. Les sessions de connexion ne sont pas conservées."""
    dest.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    target = dest / f"auto-{stamp}.db"
    partial = dest / f"{target.name}.partiel"  # nom provisoire : jamais pris pour une sauvegarde valide
    src, out = sqlite3.connect(db_path), sqlite3.connect(partial)
    try:
        src.backup(out)
        try:
            out.execute("DELETE FROM sessions")
            out.commit()
        except sqlite3.OperationalError:  # base sans table sessions (ancienne version)
            pass
        if out.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise sqlite3.DatabaseError("la copie ne passe pas le contrôle d'intégrité")
    except BaseException:
        out.close()
        src.close()
        partial.unlink(missing_ok=True)
        raise
    out.close()
    src.close()
    partial.replace(target)
    return target


def prune(dest: Path, keep: int) -> list[Path]:
    """Supprime les plus anciennes sauvegardes automatiques au-delà de `keep` ; renvoie celles supprimées."""
    old = list_backups(dest)[:-keep] if keep > 0 else []
    for p in old:
        p.unlink(missing_ok=True)
    return old


def is_due(dest: Path, interval_hours: float, now: float | None = None) -> bool:
    last = list_backups(dest)
    if not last:
        return True
    return ((now or time.time()) - last[-1].stat().st_mtime) >= interval_hours * 3600


def run_if_due(db_path: Path, dest: Path, interval_hours: float, keep: int) -> Path | None:
    """Fait une sauvegarde si la dernière date de plus de `interval_hours`, puis applique la rotation.

    Ne lève jamais d'exception : une sauvegarde ratée est journalisée mais ne doit pas empêcher l'application de tourner.
    """
    try:
        if not is_due(dest, interval_hours):
            return None
        target = make_backup(db_path, dest)
        removed = prune(dest, keep)
        log.info("Sauvegarde automatique : %s (%d ancienne(s) supprimée(s))", target.name, len(removed))
        return target
    except Exception:
        log.exception("Échec de la sauvegarde automatique")
        return None


class Scheduler:
    """Vérifie régulièrement (toutes les heures) si une sauvegarde est due. Fil d'arrière-plan, arrêt propre."""

    def __init__(self, db_path: Path, dest: Path, interval_hours: float, keep: int, check_every: float = 3600):
        self.args = (db_path, dest, interval_hours, keep)
        self.check_every = check_every
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="cgrs-autobackup", daemon=True)

    def _loop(self):
        while True:
            run_if_due(*self.args)
            if self._stop.wait(self.check_every):
                return

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=10)
