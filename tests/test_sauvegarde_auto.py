"""Sauvegardes automatiques : copie cohérente, rotation prudente, jamais bloquante."""
import os
import sqlite3
import time
from datetime import datetime, timedelta

from cgrs import autobackup


def fake_backup(dest, name, age_hours=0):
    dest.mkdir(exist_ok=True)
    p = dest / name
    p.write_bytes(b"x")
    t = time.time() - age_hours * 3600
    os.utime(p, (t, t))
    return p


def test_copie_coherente_sans_sessions(database, tmp_path):
    database.execute("INSERT INTO suppliers (name) VALUES ('A')")
    uid = database.execute("INSERT INTO users (username, password_hash, role, created) VALUES ('u', 'h', 'admin', 'x')")
    database.execute("INSERT INTO sessions (token_hash, user_id, expires) VALUES ('t', ?, 'y')", (uid,))
    out = autobackup.make_backup(database.DB_PATH, tmp_path / "auto", datetime(2030, 1, 2, 3, 4, 5))
    assert out.name == "auto-20300102-030405.db"
    c = sqlite3.connect(out)
    assert c.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] == 1
    assert c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    c.close()
    assert [p.name for p in (tmp_path / "auto").iterdir()] == [out.name]       # pas de fichier provisoire oublié


def test_rotation_ne_touche_que_les_sauvegardes_automatiques(tmp_path):
    for i in range(1, 6):
        fake_backup(tmp_path, f"auto-2030010{i}-120000.db")
    garde = fake_backup(tmp_path, "avant-restauration-20200101-000000.db")
    autre = fake_backup(tmp_path, "notes.txt")
    supprimees = autobackup.prune(tmp_path, keep=2)
    assert [p.name for p in supprimees] == ["auto-20300101-120000.db", "auto-20300102-120000.db", "auto-20300103-120000.db"]
    assert [p.name for p in autobackup.list_backups(tmp_path)] == ["auto-20300104-120000.db", "auto-20300105-120000.db"]
    assert garde.exists() and autre.exists()


def test_pas_de_sauvegarde_si_la_derniere_est_recente(database, tmp_path):
    dest = tmp_path / "auto"
    fake_backup(dest, "auto-20300101-120000.db", age_hours=2)
    assert autobackup.run_if_due(database.DB_PATH, dest, interval_hours=24, keep=5) is None
    assert len(autobackup.list_backups(dest)) == 1


def test_sauvegarde_si_la_derniere_est_ancienne_ou_absente(database, tmp_path):
    dest = tmp_path / "auto"
    assert autobackup.run_if_due(database.DB_PATH, dest, 24, 5) is not None          # aucune sauvegarde : on en fait une
    for f in dest.iterdir():
        t = time.time() - 30 * 3600
        os.utime(f, (t, t))
    assert autobackup.run_if_due(database.DB_PATH, dest, 24, 5) is not None          # la dernière a 30 h
    assert len(autobackup.list_backups(dest)) in (1, 2)


def test_une_sauvegarde_ratee_ne_leve_pas_et_ne_laisse_rien(tmp_path):
    dest = tmp_path / "auto"
    assert autobackup.run_if_due(tmp_path / "absente" / "x.db", dest, 24, 5) is None   # base introuvable
    assert not list(dest.glob("*")) if dest.exists() else True


def test_au_demarrage_l_application_sauvegarde_puis_s_arrete_proprement(database, tmp_path):
    s = autobackup.Scheduler(database.DB_PATH, tmp_path / "auto", 24, 3, check_every=0.05)
    s.start()
    for _ in range(100):
        if autobackup.list_backups(tmp_path / "auto"):
            break
        time.sleep(0.05)
    s.stop()
    assert len(autobackup.list_backups(tmp_path / "auto")) == 1
    assert not s._thread.is_alive()
