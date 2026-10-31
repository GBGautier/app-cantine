"""Point d'entree de l'app de bureau Windows (pywebview).

Lance le serveur FastAPI (uvicorn) dans un thread, puis ouvre une fenetre
de bureau pointant dessus. L'import de webview est differe dans main()
pour que ce meme dossier reste deployable sur un serveur sans pywebview
(uvicorn app:app).

L'executable est construit sans console : sys.stdout et sys.stderr y valent None. uvicorn ne doit donc pas configurer
sa journalisation vers la console (log_config=None) ; ses messages vont dans logs/cgrs.log, comme ceux de l'application.
"""

import socket
import sys
import threading
import time

import uvicorn

from app import app
from cgrs import journal

log = journal.get("bureau")

server = None  # reference globale pour l'arret propre
startup_error = None  # erreur qui a arrete le serveur avant son demarrage


def find_free_port() -> int:
    """Port libre pour eviter les conflits entre instances."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_server(port: int):
    global server, startup_error
    try:
        journal.attach("uvicorn")
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, log_level="warning")
        server = uvicorn.Server(config)
        server.run()
    except BaseException as e:  # y compris SystemExit (port impossible a ouvrir) : sinon main() attendrait sans fin
        startup_error = e
        log.exception("Le serveur s'est arrete sur une erreur")


def wait_for_server(thread: threading.Thread, timeout: float = 60.0):
    """Attend que le serveur soit pret (evite la fenetre blanche) ; leve une erreur s'il ne demarre pas."""
    deadline = time.monotonic() + timeout
    while not (server and server.started):
        if startup_error is not None or not thread.is_alive():
            raise RuntimeError(f"Le serveur n'a pas demarre : {startup_error!r}")
        if time.monotonic() > deadline:
            raise RuntimeError("Le serveur n'a pas demarre dans le delai prevu")
        time.sleep(0.05)


def fatal(message: str):
    """Signale une erreur fatale : journal, et boite de dialogue sous Windows (il n'y a pas de console)."""
    log.error(message)
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, "CGRS", 0x10)
        except Exception:  # la boite de dialogue est un confort : le journal reste la reference
            pass


def main():
    try:
        port = find_free_port()

        # FastAPI dans un thread daemon (tue avec le process principal)
        thread = threading.Thread(target=run_server, args=(port,), daemon=True)
        thread.start()
        wait_for_server(thread)

        import webview  # import differe : evite d'exiger pywebview sur un serveur

        webview.create_window(
            "CGRS – réceptions & stocks",
            f"http://127.0.0.1:{port}",
            width=1200,
            height=800,
            min_size=(800, 600),
        )
        webview.start(gui="edgechromium")  # force WebView2 sur Windows
    except Exception as e:
        log.exception("Echec du demarrage de l'application")
        fatal(f"CGRS n'a pas pu demarrer : {e}\n\nDetails dans le dossier logs, fichier cgrs.log.")
        return

    # arret propre a la fermeture de la fenetre
    if server:
        server.should_exit = True


if __name__ == "__main__":
    main()
