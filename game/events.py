"""Tails the append-only events.jsonl written by hooks/emit_event.py.

On startup we replay from the last prompt_start so the game launched *by* that
prompt_start still sees it (the hook appends the line before spawning us)."""
import json
import os

from . import paths

_TAIL_BYTES = 65536


class EventTail:
    def __init__(self):
        paths.ensure_dirs()
        self._pos = 0
        self._backlog = []
        try:
            size = os.path.getsize(paths.EVENTS_FILE)
            with open(paths.EVENTS_FILE, "rb") as f:
                f.seek(max(0, size - _TAIL_BYTES))
                lines = f.read().decode("utf-8", "replace").splitlines()
            events = []
            for ln in lines:
                try:
                    ev = json.loads(ln)
                    if isinstance(ev, dict) and "event" in ev:
                        events.append(ev)
                except ValueError:
                    continue
            start = None
            for i, ev in enumerate(events):
                if ev["event"] == "prompt_start":
                    start = i
            if start is not None:
                self._backlog = events[start:]
            self._pos = size
        except OSError:
            pass

    def poll(self):
        out, self._backlog = self._backlog, []
        try:
            size = os.path.getsize(paths.EVENTS_FILE)
        except OSError:
            return out
        if size < self._pos:          # file was truncated/rotated by the hook
            self._pos = 0
        if size > self._pos:
            try:
                with open(paths.EVENTS_FILE, "rb") as f:
                    f.seek(self._pos)
                    chunk = f.read(size - self._pos)
            except OSError:
                return out
            end = chunk.rfind(b"\n")  # only consume complete lines
            if end < 0:
                return out
            self._pos += end + 1
            for ln in chunk[:end].decode("utf-8", "replace").splitlines():
                try:
                    ev = json.loads(ln)
                    if isinstance(ev, dict) and "event" in ev:
                        out.append(ev)
                except ValueError:
                    continue
        return out
