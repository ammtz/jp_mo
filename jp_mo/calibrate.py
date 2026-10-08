"""Level rule from skills/calibrate_filter.md. The threshold is never touched."""
from .judge import LEVEL_MAX, LEVEL_MIN

BAND_LOW, BAND_HIGH = 8, 12
STREAK = 2
BOUND_RUNS_FLAG = 5


def step(core: dict, passed: int, eligible: bool) -> dict:
    """Return the new core state. Ineligible runs (failed feed, no edition) change nothing."""
    core = dict(core)
    core["recalibrate"] = core.get("bound_runs", 0) >= BOUND_RUNS_FLAG
    if not eligible:
        return core

    direction = "high" if passed > BAND_HIGH else "low" if passed < BAND_LOW else None
    if direction and direction == core.get("streak_dir"):
        core["streak"] = core.get("streak", 0) + 1
    else:
        core["streak_dir"], core["streak"] = direction, (1 if direction else 0)

    level = core.get("level", 0)
    at_bound = (direction == "high" and level >= LEVEL_MAX) or (direction == "low" and level <= LEVEL_MIN)
    core["bound_runs"] = core.get("bound_runs", 0) + 1 if at_bound else 0

    if core["streak"] >= STREAK and not at_bound:
        core["level"] = level + (1 if direction == "high" else -1)
        core["streak_dir"], core["streak"] = None, 0

    core["recalibrate"] = core["bound_runs"] >= BOUND_RUNS_FLAG
    return core
