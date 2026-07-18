"""Claude Code hook handler. Called as: python emit_event.py <event_name>
with the hook's JSON payload on stdin. Appends one JSON line to the shared
events log and, on prompt_start, launches the game (detached) if it isn't
already running.

Must be FAST and must NEVER block or fail loudly — Claude is waiting on us.
Deliberately import-free of the game package; paths mirror game/paths.py."""
import ctypes
import json
import os
import subprocess
import sys
import time

APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                       "GraveWait")
EVENTS_FILE = os.path.join(APP_DIR, "events.jsonl")
LOCK_FILE = os.path.join(APP_DIR, "game.lock")
GAME_MAIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "main.py")
MAX_LOG_BYTES = 1_000_000


def _pid_alive(pid):
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)    # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259    # STILL_ACTIVE


def game_running():
    try:
        with open(LOCK_FILE) as f:
            return _pid_alive(int(f.read().strip()))
    except (OSError, ValueError):
        return False


def launch_game():
    if getattr(sys, "frozen", False):
        # installed build: GraveWait.exe sits next to this hook exe
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        args = [os.path.join(exe_dir, "GraveWait.exe")]
        cwd = exe_dir
    else:
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pyw):
            pyw = sys.executable
        args = [pyw, GAME_MAIN]
        cwd = os.path.dirname(GAME_MAIN)
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(args, cwd=cwd,
                     creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True)


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    line = {"event": event, "ts": time.time(),
            "session_id": data.get("session_id", "")}
    if event == "prompt_start":
        line["prompt"] = (data.get("prompt") or "")[:200]
    elif event == "tool_done":
        line["tool"] = data.get("tool_name", "")
    elif event == "notification":
        line["message"] = (data.get("message") or "")[:1200]

    os.makedirs(APP_DIR, exist_ok=True)
    launch = event == "prompt_start" and not game_running()
    if launch:
        try:                                  # no game watching: safe to rotate
            if (os.path.exists(EVENTS_FILE) and
                    os.path.getsize(EVENTS_FILE) > MAX_LOG_BYTES):
                os.remove(EVENTS_FILE)
        except OSError:
            pass
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    if launch:
        launch_game()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass                                  # never bother Claude with our problems
    sys.exit(0)
