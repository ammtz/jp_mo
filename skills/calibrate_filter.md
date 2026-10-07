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
