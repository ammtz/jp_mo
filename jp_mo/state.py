"""Persistent machine state: core level, run log, seen items, velocity snapshots, grades.

Two stores with the same interface: FileStore (STATE_DIR, local runs) and RedisStore (Upstash
REST, unattended runs on GitHub Actions). Pick with UPSTASH_REDIS_REST_URL/TOKEN.
"""
import json
from datetime import date, timedelta
from pathlib import Path

SEEN_DAYS = {"gh_popular": 30}
SEEN_DEFAULT_DAYS = 7
REPO_FEEDS = ("gh_stars", "gh_popular")   # items that *are* a repo (a package is not its repo)
LOG_RECENT = 60


def window(source: str) -> int:
    return SEEN_DAYS.get(source, SEEN_DEFAULT_DAYS)


class FileStore:
    def __init__(self, state_dir: Path):
        self.dir = Path(state_dir)

    def read(self, name):
        p = self.dir / f"{name}.json"
        return json.loads(p.read_text()) if p.exists() else None

    def write(self, name, data):
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.dir / f"{name}.json.tmp"
        tmp.write_text(json.dumps(data, indent=1, sort_keys=True))
        tmp.replace(self.dir / f"{name}.json")

    def append_log(self, entry: dict):
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "log.jsonl", "a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    def recent_log(self) -> list:
        p = self.dir / "log.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()[-LOG_RECENT:]] if p.exists() else []


class RedisStore:
    """Upstash Redis over its REST API: POST [command, args...] with a bearer token."""
    PREFIX = "jp_mo:"

    def __init__(self, http, url: str, token: str):
        self.http, self.url, self.token = http, url.rstrip("/"), token

    def cmd(self, *args):
        return self.http.post_json(self.url, list(args), {"Authorization": "Bearer " + self.token}).get("result")

    def read(self, name):
        raw = self.cmd("GET", self.PREFIX + name)
        return json.loads(raw) if raw else None

    def write(self, name, data):
        self.cmd("SET", self.PREFIX + name, json.dumps(data, sort_keys=True))

    def append_log(self, entry: dict):
        self.cmd("RPUSH", self.PREFIX + "log", json.dumps(entry, sort_keys=True))

    def recent_log(self) -> list:
        return [json.loads(x) for x in self.cmd("LRANGE", self.PREFIX + "log", -LOG_RECENT, -1) or []]


class State:
    def __init__(self, state_dir: Path | None = None, persist: bool = True, store=None):
        self.store = store or FileStore(state_dir)
        self.persist = persist
        self.core = self.store.read("state") or {"level": 0, "streak_dir": None, "streak": 0, "bound_runs": 0}
        self.seen = self.store.read("seen") or {}
        self.snapshots = self.store.read("snapshots") or {}

    def save(self):
        if not self.persist:
            return
        self.store.write("state", self.core)
        self.store.write("seen", self.seen)
        self.store.write("snapshots", self.snapshots)

    def save_grades(self, grades: dict):
        if self.persist:
            self.store.write("grades", grades)

    def append_log(self, entry: dict):
        if self.persist:
            self.store.append_log(entry)

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
        return any(e.get("date") == day.isoformat() and e.get("status") == "ok" for e in self.store.recent_log())

    def mark_seen(self, items, today: date):
        for c in items:
            longest = max(c.sources, key=window)    # merged items keep the longest window
            for k in self.mark_keys(c):
                self.seen[k] = {"date": today.isoformat(), "source": longest}
        cutoff = today - timedelta(days=max(SEEN_DAYS.values()))
        self.seen = {k: v for k, v in self.seen.items() if date.fromisoformat(v["date"]) >= cutoff}
