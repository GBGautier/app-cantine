"""Journal technique : erreurs inattendues et connexions refusées laissent une trace exploitable."""
import logging

from cgrs import journal


def test_erreur_inattendue_message_propre_et_trace_dans_le_journal(client, caplog):
    from cgrs.application import app

    @app.get("/api/_test_boum")
    def boum():
        raise ZeroDivisionError("secret technique")

    from fastapi.testclient import TestClient
    c = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR, logger="cgrs"):
        r = c.get("/api/_test_boum")
    assert r.status_code == 500
    detail = r.json()["detail"]
    assert "secret technique" not in detail and "ZeroDivisionError" not in detail   # rien de technique côté utilisateur
    ref = detail.rsplit(" ", 1)[-1]
    assert len(ref) == 8
    assert any(ref in rec.getMessage() and rec.exc_info for rec in caplog.records)   # la référence retrouve la trace
    assert r.headers["x-content-type-options"] == "nosniff"


def test_connexion_refusee_journalisee(client, caplog):
    from fastapi.testclient import TestClient

    from cgrs.application import app
    c = TestClient(app, headers={"X-Requested-With": "cgrs"})
    with caplog.at_level(logging.WARNING, logger="cgrs"):
        r = c.post("/api/auth/login", json={"username": "pirate", "password": "x"})
    assert r.status_code == 401
    assert any("Connexion refusée" in rec.getMessage() and "pirate" in rec.getMessage() for rec in caplog.records)
    assert "x'" not in "".join(rec.getMessage() for rec in caplog.records)   # le mot de passe n'est jamais journalisé


def test_setup_ecrit_dans_un_fichier_tournant_sans_doublon(tmp_path):
    journal.setup(tmp_path)
    journal.setup(tmp_path)
    log = journal.get("essai")
    log.propagate = True
    log.info("bonjour")
    for h in journal.get().handlers:
        h.flush()
    assert "bonjour" in (tmp_path / "cgrs.log").read_text(encoding="utf-8")
    assert len(journal.get().handlers) == 2          # console + fichier, pas 4
    journal.setup(None)


def test_dossier_non_inscriptible_ne_bloque_pas(tmp_path):
    fichier = tmp_path / "fichier"
    fichier.write_text("x")
    journal.setup(fichier / "logs")                  # impossible de créer un dossier sous un fichier
    assert len(journal.get().handlers) == 1
