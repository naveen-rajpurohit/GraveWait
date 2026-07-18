"""The hybrid loading-bar brain.

Real signals (tool_done heartbeats, stop) feed a 'pending' pool; the displayed
value consumes the pool with scripted stalls and bursts so it moves like a
classic dodgy loading bar — but the stalls line up with Claude actually being
quiet, and completion is real."""
import random

from . import config


class Progress:
    def __init__(self):
        self.value = config.PROGRESS_START
        self.status = "idle"          # idle | running | finishing | done
        self.pending = 0.0
        self.run_start = 0.0
        self.finish_at = 0.0
        self._stall_until = 0.0

    def start_run(self, now):
        self.value = config.PROGRESS_START
        self.status = "running"
        self.pending = 2.0            # a little momentum right away
        self.run_start = now
        self.finish_at = 0.0
        self._stall_until = 0.0

    def on_tool(self, now):
        if self.status == "running":
            self.pending += random.uniform(1.5, 4.0)
            if random.random() < 0.5:            # activity often breaks a stall
                self._stall_until = min(self._stall_until, now + 0.3)

    def on_stop(self, now):
        if self.status in ("running", "idle"):
            self.status = "finishing"
            self.finish_at = max(now + 1.4, self.run_start + config.MIN_RUN_SECONDS)

    @property
    def done(self):
        return self.status == "done"

    def update(self, dt, now):
        if self.status == "running":
            self.pending += 0.35 * dt            # baseline creep even with no tools
            if now >= self._stall_until:
                if random.random() < dt * 0.09:  # occasionally freeze for a while
                    self._stall_until = now + random.uniform(1.5, 5.0)
                take = min(self.pending, (2.0 + self.pending * 0.9) * dt)
                self.pending -= take
                headroom = (config.PROGRESS_CAP - self.value) / (
                    config.PROGRESS_CAP - config.PROGRESS_START)
                self.value = min(config.PROGRESS_CAP,
                                 self.value + take * max(0.15, headroom))
        elif self.status == "finishing":
            remain = max(self.finish_at - now, 0.0001)
            self.value = min(100.0, self.value + (100.0 - self.value) / remain * dt)
            if self.value >= 99.95:
                self.value = 100.0
                self.status = "done"
