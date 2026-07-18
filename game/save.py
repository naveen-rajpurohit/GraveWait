import json
import os

from . import paths


class Save:
    def __init__(self):
        self.high_score = 0
        self.wins = 0
        self.total_kills = 0
        self.mode = "easy"
        self._load()

    def _load(self):
        try:
            with open(paths.SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.high_score = int(data.get("high_score", 0))
            self.wins = int(data.get("wins", 0))
            self.total_kills = int(data.get("total_kills", 0))
            if data.get("mode") in ("easy", "hard"):
                self.mode = data["mode"]
        except (OSError, ValueError):
            pass

    def write(self):
        paths.ensure_dirs()
        tmp = paths.SAVE_FILE + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"high_score": self.high_score, "wins": self.wins,
                           "total_kills": self.total_kills,
                           "mode": self.mode}, f)
            os.replace(tmp, paths.SAVE_FILE)
        except OSError:
            pass

    def bank_score(self, score):
        """Fold a finished/abandoned run's score into the records.
        (total_kills is incremented per kill by the game, not here.)"""
        if score > self.high_score:
            self.high_score = score
        self.write()
