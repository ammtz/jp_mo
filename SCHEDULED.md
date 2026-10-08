# Scheduled jobs (runner-agnostic)

## Morning edition: daily, 7:00 AM ET
Any scheduler works: cron/systemd on a box, GitHub Actions, or an agent harness's scheduler. Cost-saving shape:

1. **Script (no model):** fetch candidates from the feeds in `context/sources.md`, normalize, dedupe.
2. **Model (judgment only):** ask the filter question from `context/filter_rules.md` per candidate. Use Jev (`typesafe-ai/jev`) via Vercel AI Gateway `POST /v1/evaluate` (see `SPEC.md`). Fallback: any gateway chat model with the same question and a `{"p": 0-1}` output.
3. **Script:** keep P(a) >= 0.75, count, sort per `context/sort_rules.md`, take top 4-5.
4. **Script/model:** render `edition_YYYY-MM-DD.md` with the footer (scanned / passed / level / feeds failed), apply `skills/calibrate_filter.md`, update the level.
5. Deliver the file (email, push notification, or drop in a synced folder).

If the job is run by an agent instead of a script, use this prompt (self-contained):

> Build today's jp_mo morning newspaper. Clone https://github.com/ammtz/jp_mo main. Read AGENTS.md and VISION.md, then follow skills/edition_build.md and skills/calibrate_filter.md exactly. Output one file edition_YYYY-MM-DD.md with the top 4-5 items and the footer. Do not push or modify the repo. Do not include the owner's name anywhere.

Notes:
- A run with no reachable feeds produces a short "no edition" note, not an empty paper.
- Calibration level and log must persist somewhere writable (`state/`, gitignored; see `SPEC.md`).

## Weekly check + calibration loop, Mondays
> Review the last 7 footers. Report average `passed`, level changes, any feed that failed more than twice, and one proposed change to the question or sources. Max 5 bullets. If at least 20 new grades have come in since the last round, run the calibration loop in `skills/calibrate_filter.md`; otherwise say "calibration: waiting for grades (n/20)".
