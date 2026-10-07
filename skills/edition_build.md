# Skill: build an edition

Runs daily at 7:00 AM ET. In code this is `python -m jp_mo build`; an agent follows the same steps by hand. See `SPEC.md` for the modules.

1. **Load:** read `.env`, `state/state.json` (create with `level: 0` if missing), and `context/*.md`.
2. **Fetch** (script): every feed in `context/sources.md`, with a 20 s timeout per request and 1 retry. Record failed feeds.
3. **Normalize + dedupe** (script): as described in `sources.md`.
4. **No candidates?** Write a "no edition" note (date, failed feeds) and stop. Don't calibrate.
5. **Judge** (model): build the state and per-candidate questions from `context/filter_rules.md` at the current level. Call the judge (Jev by default), pass 1 for everything, then pass 2 for the "close" GitHub-backed items (see the two-pass rules in `filter_rules.md`). Record the final P(a) per candidate, which pass decided it, the model, and the total cost.
6. **Select** (script): keep P(a) ≥ 0.75, then apply `context/sort_rules.md`.
7. **Render** (script): write `editions/edition_YYYY-MM-DD.md` (format below).
8. **Calibrate** (script): apply `skills/calibrate_filter.md`, then save state and append to `state/log.jsonl`.
9. **Deliver:** copy the file to `EDITION_DIR`. v1 does nothing else.

## Edition format
```markdown
# jp_mo · Wed 2026-10-07

## 1. {title}
{source label} · {momentum label} · P {0.00}
{url}
{summary, ≤ 2 lines}

## 2. ...

---
scanned {n} · 2nd-pass {n} · passed {n} · level {L} · feeds failed: {ids or none} · judge {model snapshot} · cost ${0.0000}
```
Never include the owner's name.
