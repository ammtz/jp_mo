# Skill: build an edition

Runs daily at 7:00 AM ET. In code this is `python -m jp_mo build`; an agent follows the same steps by hand. See `SPEC.md` for the modules.

One edition per day: if the day already has a successful edition, `build` exits without changes. `--force` rebuilds it (re-opening that day's printed items, without counting it toward calibration again). A day that only got a "no edition" note can be retried freely.

1. **Load:** read `.env`, `state/state.json` (create with `level: 0` if missing), and `context/*.md`. Harvest the owner's grades (edition files, then Notion) into `state/grades.json`.
2. **Fetch** (script): every feed in `context/sources.md`, with a 20 s timeout per request and 1 retry. Record failed feeds.
3. **Normalize + dedupe** (script): as described in `sources.md`.
4. **No candidates?** Write a "no edition" note (date, failed feeds) and stop. Don't calibrate.
5. **Judge** (model): build the state and per-candidate questions from `context/filter_rules.md` at the current level. Call the judge (Jev by default), pass 1 for everything, then pass 2 for the "close" GitHub-backed items (see the two-pass rules in `filter_rules.md`). Record the final P(a) per candidate, which pass decided it, the model, and the total cost.
6. **Select** (script): keep P(a) ≥ 0.75, then apply `context/sort_rules.md`.
6b. **Curate** (model): the curator writes one news note per printed item: what it is, and the concrete way to apply it to this system (see `SPEC.md`). If it fails, fall back to the plain blurb.
7. **Render** (script): write `{EDITION_DIR}/edition_YYYY-MM-DD.md` (format below). `--dry-run` writes `dryrun_YYYY-MM-DD.md` and never touches `state/`.
8. **Calibrate** (script): apply `skills/calibrate_filter.md`, then save state and append to `state/log.jsonl` (including each printed item's P and a 10-bin histogram of all final P values).
9. **Deliver:** the file in `EDITION_DIR` always exists. If Notion is configured, the notes are also added to the "jp_mo notes" database, where the owner reads and grades them (see `SPEC.md`).

## Edition format
```markdown
# jp_mo · Wed 2026-10-07

## 1. {title}
{source label} · {momentum label} · P {0.00}
{url}

**What:** {one sentence}
**For jp_mo:** {the concrete change to this system}
**Effort:** {S|M|L} · **Effect:** {sellable|efficient|simpler}

Grade: [ ] great [ ] good [ ] bad
<!-- id: {item id} -->

## 2. ...

---
scanned {n} · 2nd-pass {n} · passed {n} · level {L} · feeds failed: {ids or none} · judge {model} · curator {model|off|failed} · cost ${0.0000}
```
Never include the owner's name.
