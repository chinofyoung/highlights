import sys
from pathlib import Path


def resource_dir() -> Path:
    """Root for bundled resources.

    When frozen by PyInstaller, files are unpacked under sys._MEIPASS.
    In dev (and tests) we use the repository root (app/'s parent).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent
