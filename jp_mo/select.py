"""Threshold, score, diversity. See context/sort_rules.md."""
from .velocity import parse_ts

THRESHOLD = 0.75               # hard rule 4: never configurable
W_P, W_MOMENTUM = 0.75, 0.25
TOP = 5
MAX_PER_SOURCE = 2


def score(c, j) -> float:
    return W_P * j.p + W_MOMENTUM * c.momentum_pct


def passed(candidates, judgements) -> list:
    return [c for c in candidates
            if judgements.get(c.id) and judgements[c.id].p is not None and judgements[c.id].p >= THRESHOLD]


def pick(candidates, judgements) -> list:
    """Top 5 by score (ties: newer first), at most 2 per source unless nothing else is left."""
    ranked = sorted(candidates, key=lambda c: (-score(c, judgements[c.id]), -parse_ts(c.published_at).timestamp()))
    chosen, overflow, per_source = [], [], {}
    for c in ranked:
        if len(chosen) == TOP:
            break
        if per_source.get(c.source, 0) < MAX_PER_SOURCE:
            chosen.append(c)
            per_source[c.source] = per_source.get(c.source, 0) + 1
        else:
            overflow.append(c)
    chosen += overflow[:TOP - len(chosen)]
    return sorted(chosen, key=ranked.index)
