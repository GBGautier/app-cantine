"""L'exécutable Windows n'a pas de console : sys.stdout et sys.stderr y valent None.

Le serveur du mode bureau (main.py) doit démarrer quand même, et refuser proprement quand il ne peut pas démarrer.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

DEMARRAGE = textwrap.dedent("""
    import sys, tempfile, pathlib, threading, urllib.request
    sys.stdout = None
    sys.stderr = None  # comme un programme Windows « sans console »
    from cgrs import db
    db.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "t.db"
    import main
    port = main.find_free_port()
    t = threading.Thread(target=main.run_server, args=(port,), daemon=True)
    t.start()
    main.wait_for_server(t, timeout=20)
    statut = urllib.request.urlopen(f"http://127.0.0.1:{port}/").status
    main.server.should_exit = True
    t.join(10)
    open(sys.argv[1], "w").write(f"ok {statut}")
""")

PORT_OCCUPE = textwrap.dedent("""
    import sys, socket, tempfile, pathlib, threading
    sys.stdout = None
    sys.stderr = None
    from cgrs import db
    db.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "t.db"
    import main
    occupe = socket.socket()
    occupe.bind(("127.0.0.1", 0))
    occupe.listen()
    t = threading.Thread(target=main.run_server, args=(occupe.getsockname()[1],), daemon=True)
    t.start()
    try:
        main.wait_for_server(t, timeout=20)
        resultat = "demarre"
    except RuntimeError as e:
        resultat = "refuse " + str(e)[:40]
    open(sys.argv[1], "w").write(resultat)
""")


def lancer(script, tmp_path):
    sortie = tmp_path / "sortie.txt"
    env = {**os.environ, "CGRS_BACKUP_INTERVAL_HOURS": "0"}  # ne rien écrire dans le dossier du projet
    r = subprocess.run(
        [sys.executable, "-c", script, str(sortie)], cwd=RACINE, env=env, capture_output=True, text=True, timeout=60
    )
    return sortie.read_text() if sortie.exists() else f"PAS DE SORTIE rc={r.returncode} {r.stderr[-800:]}"


def test_le_serveur_demarre_sans_console(tmp_path):
    assert lancer(DEMARRAGE, tmp_path) == "ok 200"


def test_un_demarrage_impossible_est_signale_au_lieu_d_attendre_sans_fin(tmp_path):
    assert lancer(PORT_OCCUPE, tmp_path).startswith("refuse")
