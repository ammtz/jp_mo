# Sort rules

Input: candidates with P(a) ≥ 0.75. Output: the top 5 (print 4 if there are only 4).

1. **Score** = `0.75 * P(a) + 0.25 * momentum_pct`. `momentum_pct` is the candidate's percentile of momentum within its own source for today's run (0-1), so sources stay comparable.
2. Sort by score, descending. Ties go to the newer `published_at`.
3. **Diversity:** at most 2 items per source in the printed set. If a third would make it in, skip it and take the next item from another source. If no other source has items left, allow it.
4. If fewer than 4 pass, print what passed. The footer explains why.
