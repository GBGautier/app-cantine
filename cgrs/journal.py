"""Journal technique de l'application (fichier tournant) : erreurs inattendues, connexions refusées, sauvegardes.

À ne pas confondre avec le « journal d'actions » de l'interface (routes/action_log.py), qui est dans la base
et décrit ce que font les utilisateurs.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

LOGGER = "cgrs"
FORMAT = "%(asctime)s %(levelname)-7s %(name)s : %(message)s"


def setup(log_dir: Path | None, level: str = "INFO") -> logging.Logger:
    """Configure le journal `cgrs` : fichier tournant (5 × 1 Mo) dans `log_dir`, et la console.

    Appel répétable sans effet de bord (pas de doublons de gestionnaires).
    """
    log = logging.getLogger(LOGGER)
    log.setLevel(level.upper())
    log.propagate = False
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    fmt = logging.Formatter(FORMAT)
    if sys.stderr is not None:  # application Windows sans console (exécutable) : pas de flux d'erreur
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        log.addHandler(console)
    if log_dir is not None:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(
                log_dir / "cgrs.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
            )
            fh.setFormatter(fmt)
            log.addHandler(fh)
        except OSError as e:  # dossier non inscriptible : on continue avec la console seule
            log.warning("Journal fichier indisponible (%s) : console seulement", e)
    return log


def get(name: str = "") -> logging.Logger:
    return logging.getLogger(f"{LOGGER}.{name}" if name else LOGGER)


def attach(name: str, level: str = "WARNING") -> None:
    """Fait écrire le journal d'une autre bibliothèque (ex. « uvicorn ») dans les mêmes destinations que `cgrs`."""
    lg = logging.getLogger(name)
    lg.handlers = list(get().handlers)
    lg.setLevel(level.upper())
    lg.propagate = False
