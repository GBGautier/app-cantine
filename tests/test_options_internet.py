"""Options d'exposition sur Internet : désactivées par défaut (comportement d'origine), actives par variables d'environnement."""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

SCRIPT = textwrap.dedent("""
    import sys, tempfile, pathlib
    from cgrs import db
    db.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "t.db"
    from fastapi.testclient import TestClient
    from cgrs.application import app
    c = TestClient(app, headers={"X-Requested-With": "cgrs"})
    docs = c.get("/docs").status_code, c.get("/openapi.json").status_code
    r = c.post("/api/auth/setup", json={"username": "admin", "password": "Motdepasse1"})
    print(docs[0], docs[1], r.headers.get("strict-transport-security", "-"), "secure" in r.headers["set-cookie"].lower())
""")


def lancer(**env):
    e = {k: v for k, v in os.environ.items() if not k.startswith("CGRS_")}
    e.update(env, CGRS_BACKUP_INTERVAL_HOURS="0")
    r = subprocess.run([sys.executable, "-c", SCRIPT], cwd=RACINE, env=e, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-1500:]
    return r.stdout.split()[-4:]


def test_par_defaut_comme_l_original():
    assert lancer() == ["200", "200", "-", "False"]


def test_mode_internet():
    assert lancer(CGRS_DOCS="0", CGRS_HSTS="1", CGRS_SECURE_COOKIES="1") == ["404", "404", "max-age=31536000", "True"]
