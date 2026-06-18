"""Desktop entry point for the packaged macOS app.

NOT used in dev — dev runs `uvicorn app.main:app` and a browser. This module
starts the same FastAPI app on a local ephemeral port and shows it in a native
pywebview window. It is the PyInstaller entry script.
"""
import socket
import threading
import time

import uvicorn

from app.main import app


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_until_up(port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main() -> None:
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    if not _wait_until_up(port):
        raise RuntimeError("Cherry.Pickle server failed to start")

    import webview  # imported lazily; only present with the `desktop` extra
    webview.create_window("Cherry.Pickle", f"http://127.0.0.1:{port}/",
                          width=1280, height=860)
    webview.start()           # blocks until the window is closed
    server.should_exit = True


if __name__ == "__main__":
    main()
