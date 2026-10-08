# Skill: calibrate the filter

Goal: about 10 items pass per run (band 8-12). The knob is the question `level` in `context/filter_rules.md`. **The 0.75 threshold never changes.**

Deterministic rule, run after each edition:

1. Append today's `passed` count to the log.
2. If the last **2** runs both had `passed > 12`, raise the level by 1 (stricter).
3. If the last **2** runs both had `passed < 8`, lower the level by 1 (looser).
4. Clamp the level to [-2, +2]. Change it by at most one step per run. Reset the 2-run streak after any change.
5. Skip calibration on runs where any feed failed or "no edition" was produced (those counts aren't representative).
6. If the level sits at a bound and the count is still outside the band for 5 runs, the ladder itself needs new wording. Flag it in the footer as `recalibrate: question` and raise it in the Monday check. Don't touch the threshold.

Log line (`state/log.jsonl`): `{"date", "scanned", "passed", "level_before", "level_after", "feeds_failed", "judge_model", "cost_usd"}`.

## Calibration loop (with the owner)
The automatic rule above only moves between existing wordings. The wordings themselves improve through this loop.

**Cadence: weekly at most.** Run it on Mondays, alongside the weekly check, and only when at least **20 new grades** have come in since the last round (about a week of editions). Otherwise skip it and say so in one line. Never run it more often, even if a footer flags `recalibrate: question`: the flag waits for Monday. The owner can always ask for a round explicitly.

1. **Pool:** fetch today's candidates without judging or writing state.
2. **Grades in:** run `python -m jp_mo grades` and start from the owner's grades on the past week's notes (`state/grades.json`). Those are the main answer key.
3. **Interview:** at most 4 short questions, only where `context/calibration_log.md` doesn't already answer them.
4. **Label (only if the grades are too few or too one-sided):** show about 10-15 items (no scores, to avoid bias), spread across high, middle and low P under the current question and across feeds. The owner grades each GREAT / GOOD / BAD in one line.
5. **Test:** write 2-4 variants (state and/or ladder text), score the full pool with Jev, and compare: pair ordering against the grades, BAD items passing, average P per grade, and how many pass (target 8-12).
6. **Check against reality:** show the best variant's top 10 and have the owner grade those too. That's the real test.
7. **Adopt:** put the winning text in `context/filter_rules.md` and `jp_mo/judge.py` (a test keeps them identical), and append the round, metrics and grades to `context/calibration_log.md`. One PR per round.

The threshold stays 0.75 throughout. If every good variant passes too few or too many items, change the ladder steps, not the threshold.
