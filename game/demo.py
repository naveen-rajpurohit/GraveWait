"""Standalone mode: a self-driven 4-minute run for people who don't have
Claude Code. Presents the same poll() interface as events.EventTail, so the
Game can't tell the difference."""
import random
import time

TOOLS = ["Read", "Edit", "Bash", "Grep", "Glob", "Write", "WebSearch"]

DEMO_MESSAGE = ("When Claude Code needs a permission, this messenger delivers "
                "it and shields you while you read. Press ENTER to close "
                "this, and it will return to its portal.")


class DemoDriver:
    def __init__(self, duration=240.0):
        now = time.time()
        sid = "demo"
        self._queue = [(now, {"event": "prompt_start", "session_id": sid,
                              "prompt": "Survive the graveyard - 4 minutes"})]
        end = now + duration - 7.0     # stop early enough that the door opens
        t = now + 5.0                  # right around the 4:00 mark
        notified = False
        while t < end:
            self._queue.append((t, {"event": "tool_done", "session_id": sid,
                                    "tool": random.choice(TOOLS)}))
            t += random.uniform(5.0, 13.0)
            if not notified and t - now > duration * 0.35:
                self._queue.append((t, {"event": "notification",
                                        "session_id": sid,
                                        "message": DEMO_MESSAGE}))
                t += 12.0
                notified = True
        self._queue.append((end, {"event": "stop", "session_id": sid}))
        self._queue.sort(key=lambda e: e[0])

    def poll(self):
        now = time.time()
        out = []
        while self._queue and self._queue[0][0] <= now:
            out.append(self._queue.pop(0)[1])
        return out
