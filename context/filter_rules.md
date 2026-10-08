# Filter rules

One binary question per candidate. **a** = true = pass. Jev returns P(a). Pass if **P(a) ≥ 0.75** (fixed; AGENTS.md hard rule 4).

## State (shared by every question in a request)
```
Reader: a solo engineer building one system: {USER_GOAL}. It fetches what's rising on GitHub, npm/PyPI and YouTube; a decision model filters candidates; an agent curator writes each news note; the reader grades every note GREAT, GOOD or BAD; and the system improves itself from those grades. Stack: small Python scripts, markdown, AI agents; could become a sellable product. They want "diamonds in the rough": items that could hugely improve this system by making it more sellable, more efficient, or simpler. Removing complexity counts as much as adding features. Not news or entertainment for its own sake.
```
`{USER_GOAL}` is inserted with its first letter lowercased and its final period dropped.

## Question ladder (the calibration knob)
`level` picks the wording. 0 is the default. Higher is stricter. Only `skills/calibrate_filter.md` changes the level. Calibrated with the owner on 2026-10-07 (round 1, see `context/calibration_log.md`). Levels +1/+2 are sent as the level-0 text plus "Also required for a:" and their conditions.

| level | instructions (a = true, b = false) |
|---|---|
| -2 | Could this item be useful in any way for the reader's newsletter system? a: yes. b: no, it's entertainment or news. |
| -1 | Is there a concrete way to apply this item to the reader's self-improving newsletter system (fetching, filtering, agent curation, writing notes, grading and learning, publishing to readers, running it cheaply, or selling it) that would make the system noticeably more sellable, more efficient, or simpler? a: yes. b: no, it's entertainment, news, too heavy for one person to adopt, or unrelated to the system. |
| **0** | Is there a concrete way to apply this item to the reader's self-improving newsletter system (fetching, filtering, agent curation, writing notes, grading and learning, publishing to readers, running it cheaply, or selling it) that would make the system noticeably more sellable, more efficient, or simpler? a: yes. b: no, it's entertainment, news, a well-known general-purpose tool they likely already use, too heavy for one person to adopt, or unrelated to the system. |
| +1 | Same as level 0, plus: the item is new or little-known to the reader, and specific rather than broad. |
| +2 | Same as level +1, plus: the improvement would be large, not incremental. |

## Per-candidate question text
```
{ladder[level]}

Item ({source}): {title}
{url}
{summary}
Signals: {momentum label and value}
README (first {n} chars): {readme[:n]}      ← line omitted when readme is empty
```

## Two passes (GitHub-backed items only)
1. **Pass 1:** every candidate, with `n = 500`.
2. **Pass 2:** only candidates whose cleaned README is longer than 500 chars (otherwise there's nothing new to show) and where pass 1 gave **0.50 ≤ P < 0.75** ("close"). Ask the same question again with `n = 1000`. **Pass 2's P replaces pass 1's**, so it can go up or down.
3. P < 0.50 on pass 1 is a big NO: no second pass. P ≥ 0.75 already passes: no second pass.
4. The 0.75 threshold is the same in both passes. The "close" band (0.50) is a cost knob, not a calibration knob.
