"""One edition, end to end (skills/edition_build.md)."""
import sys
from datetime import date, datetime

from . import calibrate, judge as judging, normalize, readme, render, select, velocity
from .sources import FEEDS
from .state import State


def log(msg: str):
    print(msg, file=sys.stderr)


def build(cfg, http, judge, now: datetime, day: date, dry_run: bool = False) -> dict:
    """Returns the run summary (also the log line). Writes the edition or a no-edition note."""
    state = State(cfg.state_dir, persist=not dry_run)
    level = state.core.get("level", 0)

    # 1. fetch (script)
    candidates, failed = [], []
    for name, fetch in FEEDS.items():
        try:
            got = fetch(cfg, http, now)
            candidates += got
            log(f"fetch {name}: {len(got)}")
        except Exception as e:
            failed.append(name)
            log(f"fetch {name}: FAILED ({e})")

    # 2. normalize, velocity, seen-filter (script)
    candidates = normalize.dedupe(candidates)
    state.snapshots = velocity.compute(candidates, state.snapshots, now)
    normalize.momentum_pct(candidates)
    candidates = [c for c in candidates if not state.was_seen(c, day)]
    scanned = len(candidates)

    summary = {"date": day.isoformat(), "scanned": scanned, "passed": 0, "second_pass": 0,
               "level_before": level, "level_after": level, "feeds_failed": failed,
               "judge_model": judge.meta.model or judge.name, "cost_usd": 0.0, "errors": 0}

    def no_edition(reason):
        write(cfg, day, render.no_edition(day, reason, failed), dry_run)
        summary["status"] = "no edition: " + reason
        state.append_log(summary)
        state.save()
        return summary

    if not candidates:
        return no_edition("no candidates (all feeds failed or everything was already printed)")

    # 3. README excerpts (script)
    with_readme = readme.attach(http, cfg.github_token, candidates)
    log(f"readme: {with_readme} of {sum(1 for c in candidates if c.repo)} repos")

    # 4. judge (model)
    try:
        judgements, second = judging.run(judge, candidates, level, cfg.goal)
    except judging.JudgeError as e:
        log(f"judge: FAILED ({e})")
        return no_edition("judge unavailable")
    summary.update(second_pass=second, judge_model=judge.meta.model or judge.name,
                   cost_usd=round(judge.meta.cost_usd, 6),
                   errors=sum(1 for c in candidates if judgements.get(c.id) is None or judgements[c.id].p is None))

    # 5. select + render (script)
    passed = select.passed(candidates, judgements)
    top = select.pick(passed, judgements)
    summary["passed"] = len(passed)

    # 6. calibrate (script): skip when a feed failed
    core = calibrate.step(state.core, len(passed), eligible=not failed)
    summary["level_after"] = core["level"]
    stats = {**summary, "level": level, "recalibrate": core.get("recalibrate")}
    path = write(cfg, day, render.edition(day, top, judgements, stats), dry_run)
    log(f"edition: {path} ({len(top)} items, {len(passed)} passed of {scanned})")

    state.core = core
    state.mark_seen(top, day)
    summary["status"] = "ok"
    state.append_log(summary)
    state.save()
    return summary


def write(cfg, day: date, text: str, dry_run: bool):
    cfg.edition_dir.mkdir(parents=True, exist_ok=True)
    prefix = "dryrun" if dry_run else "edition"
    path = cfg.edition_dir / f"{prefix}_{day.isoformat()}.md"
    path.write_text(text)
    return path
