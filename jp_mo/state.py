"""Persistent machine state in STATE_DIR: state.json, log.jsonl, seen.json, snapshots.json."""
import json
from datetime import date, timedelta
from pathlib import Path

SEEN_DAYS = {"gh_popular": 30}
SEEN_DEFAULT_DAYS = 7
REPO_FEEDS = ("gh_stars", "gh_popular")   # items that *are* a repo (a package is not its repo)


def window(source: str) -> int:
    return SEEN_DAYS.get(source, SEEN_DEFAULT_DAYS)


class State:
    def __init__(self, state_dir: Path, persist: bool = True):
        self.dir = Path(state_dir)
        self.persist = persist
        self.core = self._read("state.json", {"level": 0, "streak_dir": None, "streak": 0, "bound_runs": 0})
        self.seen = self._read("seen.json", {})
        self.snapshots = self._read("snapshots.json", {})

    def _read(self, name, default):
        p = self.dir / name
        if p.exists():
            return json.loads(p.read_text())
        return default

    def _write(self, name, data):
        if not self.persist:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.dir / (name + ".tmp")
        tmp.write_text(json.dumps(data, indent=1, sort_keys=True))
        tmp.replace(self.dir / name)

    def save(self):
        self._write("state.json", self.core)
        self._write("seen.json", self.seen)
        self._write("snapshots.json", self.snapshots)

    def append_log(self, entry: dict):
        if not self.persist:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "log.jsonl", "a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    # --- seen items -------------------------------------------------------
    @staticmethod
    def check_keys(c) -> list:
        """A candidate is blocked by its own id, or by its repo having been printed as a repo."""
        return [c.id] + (["repo:" + c.repo] if c.repo else [])

    @staticmethod
    def mark_keys(c) -> list:
        """Printing a package must not block sibling packages from the same monorepo."""
        return [c.id] + (["repo:" + c.repo] if c.repo and any(s in REPO_FEEDS for s in c.sources) else [])

    def was_seen(self, c, today: date) -> bool:
        for k in self.check_keys(c):
            rec = self.seen.get(k)
            if rec and today - date.fromisoformat(rec["date"]) < timedelta(days=window(rec["source"])):
                return True
        return False

    def unmark_day(self, day: date):
        self.seen = {k: v for k, v in self.seen.items() if v["date"] != day.isoformat()}

    def logged_ok(self, day: date) -> bool:
        p = self.dir / "log.jsonl"
        if not p.exists():
            return False
        for line in p.read_text().splitlines():
            e = json.loads(line)
            if e.get("date") == day.isoformat() and e.get("status") == "ok":
                return True
        return False

    def mark_seen(self, items, today: date):
        for c in items:
            longest = max(c.sources, key=window)    # merged items keep the longest window
            for k in self.mark_keys(c):
                self.seen[k] = {"date": today.isoformat(), "source": longest}
        cutoff = today - timedelta(days=max(SEEN_DAYS.values()))
        self.seen = {k: v for k, v in self.seen.items() if date.fromisoformat(v["date"]) >= cutoff}
