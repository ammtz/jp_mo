"""Dedupe/merge and per-source momentum percentiles."""
from .models import SOURCES

PREFERENCE = {s: i for i, s in enumerate(SOURCES)}


def dedupe(candidates) -> list:
    """Same URL -> one. Same repo across feeds -> merge, keeping the preferred feed's item."""
    ordered = sorted(candidates, key=lambda c: PREFERENCE[c.source])
    by_url, by_repo, out = {}, {}, []
    for c in ordered:
        keeper = by_url.get(c.url) or (by_repo.get(c.repo) if c.repo else None)
        if keeper:
            for s in c.sources:
                if s not in keeper.sources:
                    keeper.sources.append(s)
            continue
        by_url[c.url] = c
        if c.repo:
            by_repo[c.repo] = c
        out.append(c)
    return out


def momentum_pct(candidates) -> None:
    """Percentile of momentum within each source (0-1), so feeds are comparable."""
    groups = {}
    for c in candidates:
        groups.setdefault(c.source, []).append(c)
    for group in groups.values():
        n = len(group)
        values = sorted(c.momentum for c in group)
        for c in group:
            below = sum(1 for v in values if v < c.momentum)
            c.momentum_pct = below / (n - 1) if n > 1 else 1.0
