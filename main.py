"""Point d'entree de l'app de bureau Windows (pywebview).

Lance le serveur FastAPI (uvicorn) dans un thread, puis ouvre une fenetre
de bureau pointant dessus. L'import de webview est differe dans main()
pour que ce meme dossier reste deployable sur un serveur sans pywebview
(uvicorn app:app).
"""
import socket
import threading
import time

import uvicorn

from app import app

server = None  # reference globale pour l'arret propre


def find_free_port() -> int:
    """Port libre pour eviter les conflits entre instances."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_server(port: int):
    global server
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def main():
    port = find_free_port()

    # FastAPI dans un thread daemon (tue avec le process principal)
    threading.Thread(target=run_server, args=(port,), daemon=True).start()

    # attendre que le serveur soit pret (evite la fenetre blanche)
    while not (server and server.started):
        time.sleep(0.05)

    import webview  # import differe : evite d'exiger pywebview sur un serveur

    webview.create_window(
        "CGRS – réceptions & stocks",
        f"http://127.0.0.1:{port}",
        width=1200,
        height=800,
        min_size=(800, 600),
    )
    webview.start(gui="edgechromium")  # force WebView2 sur Windows

    # arret propre a la fermeture de la fenetre
    if server:
        server.should_exit = True


if __name__ == "__main__":
    main()