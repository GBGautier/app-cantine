"""Point d'entrée de l'app de bureau Windows (pywebview).

Lance le serveur FastAPI (uvicorn) dans un thread, puis ouvre une fenêtre
de bureau pointant dessus. L'import de webview est différé dans main()
pour que ce même dossier reste déployable sur un serveur sans pywebview
(uvicorn app:app).
"""
import socket
import threading
import time

import uvicorn

from src.backend.app import app

server = None  # référence globale pour l'arrêt propre


def find_free_port() -> int:
    """Port libre pour éviter les conflits entre instances."""
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

    # FastAPI dans un thread daemon (tué avec le process principal)
    threading.Thread(target=run_server, args=(port,), daemon=True).start()

    # attendre que le serveur soit prêt (évite la fenêtre blanche)
    while not (server and server.started):
        time.sleep(0.05)

    import webview  # import différé : évite d'exiger pywebview sur un serveur

    webview.create_window(
        "CGRS – réceptions & stocks",
        f"http://127.0.0.1:{port}",
        width=1200,
        height=800,
        min_size=(800, 600),
    )
    webview.start(gui="edgechromium")  # force WebView2 sur Windows

    # arrêt propre à la fermeture de la fenêtre
    if server:
        server.should_exit = True


if __name__ == "__main__":
    main()
