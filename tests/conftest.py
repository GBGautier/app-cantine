"""Fixtures communes : bases de données temporaires, jamais la vraie base de l'application."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # racine du projet : db, paths, cgrs…


@pytest.fixture()
def database(tmp_path, monkeypatch):
    """Base SQLite vide et initialisée, dans un dossier temporaire."""
    from cgrs import db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init()
    return db


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    """Client HTTP de l'application complète, sur une base temporaire, connecté en administrateur."""
    from cgrs import db

    db.DB_PATH = tmp_path_factory.mktemp("data") / "api.db"  # avant l'import de l'application, qui initialise la base
    from fastapi.testclient import TestClient

    from cgrs.application import app

    c = TestClient(app, headers={"X-Requested-With": "cgrs"})
    r = c.post("/api/auth/setup", json={"username": "admin", "password": "Motdepasse1"})
    assert r.status_code == 200, r.text
    return c
