"""Shared filesystem locations. hooks/emit_event.py duplicates these on purpose
so the hook stays import-free and fast — keep the two in sync."""
import os
import sys

APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "GraveWait")
EVENTS_FILE = os.path.join(APP_DIR, "events.jsonl")
SAVE_FILE = os.path.join(APP_DIR, "save.json")
LOCK_FILE = os.path.join(APP_DIR, "game.lock")


def ensure_dirs():
    os.makedirs(APP_DIR, exist_ok=True)


def resource_dir():
    """Root for bundled read-only data (assets/...): the PyInstaller unpack
    dir when frozen, the repo root when running from source."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
