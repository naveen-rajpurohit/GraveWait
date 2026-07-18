"""Simulates a full Claude prompt lifecycle through the REAL hook emitter, so a
whole game run can be play-tested without touching Claude Code.

    python tools\\fake_prompt.py           # ~2 minute run
    python tools\\fake_prompt.py --fast    # ~18s
    python tools\\fake_prompt.py --notify-only   # just fire a notification
"""
import json
import os
import random
import subprocess
import sys
import time

EMIT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "hooks", "emit_event.py")
SESSION = f"fake-{int(time.time())}"

TOOLS = ["Read", "Edit", "Bash", "Grep", "Glob", "Write", "WebFetch"]


def emit(event, **payload):
    payload.setdefault("session_id", SESSION)
    subprocess.run([sys.executable, EMIT, event],
                   input=json.dumps(payload), text=True, check=False)
    print(f"  -> {event} {payload.get('tool_name', payload.get('message', ''))[:60]}")


def main():
    fast = "--fast" in sys.argv
    k = 0.15 if fast else 1.0     # default run averages ~2 minutes
    if "--notify-only" in sys.argv:
        emit("notification",
             message="Claude needs your permission to use Bash: rm -rf node_modules")
        return
    print(f"simulating prompt lifecycle (session {SESSION})")
    emit("prompt_start",
         prompt="Refactor the payment service and add integration tests")
    time.sleep(4 * k)
    for i in range(22):
        emit("tool_done", tool_name=random.choice(TOOLS))
        time.sleep(random.uniform(2.5, 7.0) * k)
        if i == 6:
            emit("notification",
                 message="Claude needs your permission to use Bash: "
                         "npm install --save-dev vitest")
            time.sleep(10 * k)    # you're "reading" the permission in-game
    time.sleep(5 * k)
    emit("stop")
    print("done - the door should open shortly")


if __name__ == "__main__":
    main()
