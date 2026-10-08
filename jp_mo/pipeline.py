"""One edition, end to end (skills/edition_build.md)."""
import sys
import time
from datetime import date, datetime

from . import calibrate, grades, judge as judging, normalize, readme, render, select, velocity
from .sources import FEEDS
from .state import State


_T0 = [time.monotonic()]


def log(msg: str):
    print(f"[{time.monotonic() - _T0[0]:6.1f}s] {msg}", file=sys.stderr)


def build(cfg, http, judge, now: datetime, day: date, dry_run: bool = False, force: bool = False,
          curator=None, readme_http=None) -> dict:
    """Returns the run summary (also the log line). Writes the edition or a no-edition note."""
    _T0[0] = time.monotonic()
    state = State(cfg.state_dir, persist=not dry_run)
    level = state.core.get("level", 0)

    # A day gets one edition. Rebuilding needs --force: it re-opens that day's printed items and
    # doesn't count toward calibration again.
    rebuild = not dry_run and state.logged_ok(day)
    if rebuild and not force:
        log(f"edition for {day} already built; use --force to rebuild it")
        return {"date": day.isoformat(), "status": "skipped: already built"}
    if rebuild:
        state.unmark_day(day)

    # 0. harvest the owner's grades from past editions (files are the source of truth)
    if not dry_run:
        harvested = grades.harvest(cfg.edition_dir)
        grades.save(cfg.state_dir, harvested)
        log(f"grades: {len(harvested)} on file")

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
               "judge_model": judge.meta.model or judge.name, "cost_usd": 0.0, "errors": 0,
               "rebuild": rebuild}

    def no_edition(reason):
        write(cfg, day, render.no_edition(day, reason, failed), dry_run)
        summary["status"] = "no edition: " + reason
        summary["seconds"] = round(time.monotonic() - _T0[0], 1)
        state.append_log(summary)
        state.save()
        return summary

    if not candidates:
        return no_edition("no candidates (all feeds failed or everything was already printed)")

    # 3. README excerpts (script)
    with_readme = readme.attach(readme_http or http, cfg.github_token, candidates)
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

    summary["printed"] = [{"id": c.id, "p": round(judgements[c.id].p, 4), "pass": judgements[c.id].passes} for c in top]
    summary["p_hist"] = histogram(j.p for j in judgements.values() if j.p is not None)

    # 5b. curator (model): one news note per printed item; never blocks the edition
    notes = {}
    if curator is not None and top:
        try:
            notes = curator.write(top, cfg.goal, cfg.root)
            summary["curator_model"] = curator.meta.model
            summary["cost_usd"] = round(summary["cost_usd"] + curator.meta.cost_usd, 6)
        except Exception as e:
            log(f"curator: FAILED ({e})")
            summary["curator_model"] = "failed"
        log(f"curator: {len(notes)} of {len(top)} notes")
    summary["notes"] = len(notes)

    # 6. calibrate (script): skip when a feed failed or the day was already counted
    core = calibrate.step(state.core, len(passed), eligible=not failed and not rebuild)
    summary["level_after"] = core["level"]
    stats = {**summary, "level": level, "recalibrate": core.get("recalibrate")}
    path = write(cfg, day, render.edition(day, top, judgements, stats, notes), dry_run)
    log(f"edition: {path} ({len(top)} items, {len(passed)} passed of {scanned})")

    state.core = core
    state.mark_seen(top, day)
    summary["status"] = "ok"
    summary["seconds"] = round(time.monotonic() - _T0[0], 1)
    state.append_log(summary)
    state.save()
    return summary


def histogram(ps) -> list:
    """Final P counts in 10 bins: [0-0.1), ..., [0.9-1.0]."""
    bins = [0] * 10
    for p in ps:
        bins[min(int(p * 10), 9)] += 1
    return bins


def write(cfg, day: date, text: str, dry_run: bool):
    cfg.edition_dir.mkdir(parents=True, exist_ok=True)
    prefix = "dryrun" if dry_run else "edition"
    path = cfg.edition_dir / f"{prefix}_{day.isoformat()}.md"
    path.write_text(text)
    return path
