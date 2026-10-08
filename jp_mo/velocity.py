"""Momentum = velocity per day, never volume. See context/sources.md."""
from datetime import datetime, timedelta, timezone

MIN_AGE_DAYS = 1 / 24          # 1 hour
PKG_AGE_CAP_DAYS = 30          # pkg downloads are a last-month window
SNAPSHOT_MIN_H, SNAPSHOT_MAX_H = 12, 72
SNAPSHOT_KEEP = timedelta(days=30)


def parse_ts(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def average(c, now: datetime) -> float:
    age = max((now - parse_ts(c.published_at)).total_seconds() / 86400, MIN_AGE_DAYS)
    if c.source == "pkg":
        age = min(age, PKG_AGE_CAP_DAYS)
    return c.metric / age


def compute(candidates, snapshots: dict, now: datetime) -> dict:
    """Set c.momentum on every candidate; return the rewritten, pruned snapshot map.

    pkg always uses the average: its metric is a rolling last-month download count, so a
    day-over-day difference measures acceleration, not velocity.
    """
    for c in candidates:
        prev = snapshots.get(c.id)
        if prev and c.source != "pkg":
            hours = (now - parse_ts(prev["at"])).total_seconds() / 3600
            if SNAPSHOT_MIN_H <= hours <= SNAPSHOT_MAX_H:
                c.momentum = max(c.metric - prev["metric"], 0) / (hours / 24)
                continue
        c.momentum = average(c, now)

    fresh = {k: v for k, v in snapshots.items() if now - parse_ts(v["at"]) <= SNAPSHOT_KEEP}
    for c in candidates:
        fresh[c.id] = {"metric": c.metric, "at": now.isoformat()}
    return fresh
