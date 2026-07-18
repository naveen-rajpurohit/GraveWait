"""Installs (or removes) the GraveWait hooks in the *global* Claude Code
settings so the game launches for prompts in every project.

    python install_hooks.py            # install / refresh
    python install_hooks.py --uninstall

The original settings.json is backed up once to settings.json.gravewait.bak.
Our entries are identified by 'emit_event.py' in the command, so install is
idempotent and uninstall removes exactly ours."""
import json
import os
import shutil
import sys

SETTINGS = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
BACKUP = SETTINGS + ".gravewait.bak"
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "hooks", "emit_event.py")
OUR_MARKERS = ("emit_event.py", "gravewait-hook")   # how we recognize our entries

HOOK_EVENTS = {
    "UserPromptSubmit": "prompt_start",
    "PostToolUse": "tool_done",
    "Notification": "notification",
    "Stop": "stop",
}


def _command_prefix():
    """Dev installs call the hook script with Python; the packaged build ships
    a standalone gravewait-hook.exe so end users don't need Python at all."""
    if getattr(sys, "frozen", False):
        exe = os.path.join(os.path.dirname(os.path.abspath(sys.executable)),
                           "gravewait-hook.exe")
        return f'"{exe}"'
    return f'"{sys.executable}" "{SCRIPT}"'


def _load():
    try:
        with open(SETTINGS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _write(settings):
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


def _strip_ours(hooks):
    for event in list(hooks.keys()):
        kept = []
        for matcher_group in hooks[event]:
            inner = [h for h in matcher_group.get("hooks", [])
                     if not any(m in h.get("command", "") for m in OUR_MARKERS)]
            if inner:
                matcher_group["hooks"] = inner
                kept.append(matcher_group)
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]


def install():
    settings = _load()
    if os.path.exists(SETTINGS) and not os.path.exists(BACKUP):
        shutil.copy2(SETTINGS, BACKUP)
        print(f"backed up settings -> {BACKUP}")
    hooks = settings.setdefault("hooks", {})
    _strip_ours(hooks)
    prefix = _command_prefix()
    for event, name in HOOK_EVENTS.items():
        entry = {"hooks": [{"type": "command",
                            "command": f"{prefix} {name}",
                            "timeout": 10}]}
        if event == "PostToolUse":
            entry["matcher"] = "*"
        hooks.setdefault(event, []).append(entry)
    _write(settings)
    print(f"installed GraveWait hooks into {SETTINGS}")
    print("events: " + ", ".join(f"{k} -> {v}" for k, v in HOOK_EVENTS.items()))
    print("note: running Claude Code sessions pick hooks up on restart")


def uninstall():
    settings = _load()
    hooks = settings.get("hooks")
    if hooks:
        _strip_ours(hooks)
        if not hooks:
            settings.pop("hooks", None)
    _write(settings)
    print(f"removed GraveWait hooks from {SETTINGS}")


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
