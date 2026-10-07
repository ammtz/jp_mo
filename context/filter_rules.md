# Filter rules

One binary question per candidate. **a** = true = pass. Jev returns P(a). Pass if **P(a) ≥ 0.75** (fixed; AGENTS.md hard rule 4).

## State (shared by every question in a request)
```
Reader: an engineer who works alone. Goal: {USER_GOAL}.
They read a 4-5 item morning paper and want only items they could act on themselves.
```

## Question ladder (the calibration knob)
`level` picks the wording. 0 is the default. Higher is stricter. Only `skills/calibrate_filter.md` changes the level. All wordings are DRAFT, pending an owner interview.

| level | instructions (a = true, b = false) |
|---|---|
| -2 | Does this item point to any idea, tool, or technique the reader could personally try? a: yes. b: no. |
| -1 | Could the reader turn this item into something they build or use themselves? a: yes. b: no, it's only news, entertainment, or opinion. |
| **0** | Could the reader, working alone, turn this item into an idea or solution they can build and run themselves within about a month? a: yes, worth their morning. b: no, it's entertainment, news without an actionable angle, or it needs a team or capital. |
| +1 | Same as level 0, plus: the problem it solves is clear, and the reader could ship a first version in a weekend. |
| +2 | Same as level +1, plus: nothing well known already solves it the same way. |

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
