# Decisions

Format: `YYYY-MM-DD: decision. Why.`

- 2026-10-07: Repo under **FSL-1.1** (variant chosen below: MIT). Not planning to monetize, but keeps the option open.
- 2026-10-07: Owner's name stays out of all public files until explicitly approved. LICENSE copyright line stays a placeholder.
- 2026-10-07: Product is a filtered, sorted morning newspaper. Sources: YouTube popular, GitHub download trends, GitHub star trends.
- 2026-10-07: Decider is Jev at P >= 0.75 on a binary a/b usefulness question. Threshold fixed; only the question is calibrated.
- 2026-10-07: Target ~10 items pass per run (band 8-12); top 4-5 printed. Built daily at 7AM ET.
- 2026-10-07: Stack: Python backend; JS/TS, HTML, CSS frontend; mobile (Android/iOS) welcome.
- 2026-10-07: Agent-agnostic. `AGENTS.md` is canonical; `CLAUDE.md` is a pointer. Must work with Kimi, Grok, and others. Why: avoid vendor lock-in and cost.
- 2026-10-07: Deterministic steps run as plain scripts; a model is used only for the a/b judgment. Why: daily agent sessions are expensive.
- 2026-10-07: Jev is reached through Vercel AI Gateway (`typesafe-ai/jev`, `POST /v1/evaluate`, boolean questions, ≤40 per request). Chat-model fallback through the same gateway. Why: one key, swappable models.
- 2026-10-07: v1 is stdlib-only Python. Machine state goes in gitignored `state/`. Edition is a markdown file dropped in `EDITION_DIR`.
- 2026-10-07: Smoke test passed: gateway key + `/v1/evaluate` return `answers.<key>.probability`; YouTube Data API v3 key works for both chart calls. GitHub fine-grained token works (search 30/min); it expires 2026-11-06.

- 2026-10-07: GitHub-backed items are judged with the first 500 cleaned README chars. If 0.50 ≤ P < 0.75, a second pass with 1,000 chars decides. P < 0.50 gets no second pass. Why: descriptions are often empty, and the second look is spent only on near-misses.
- 2026-10-07: License is **FSL-1.1-MIT** (`LICENSE.md`; copyright line stays a placeholder). Why: owner isn't selling this system; MIT future license.
- 2026-10-07: Sort score = 0.75 × P + 0.25 × momentum percentile.
- 2026-10-07: GitHub side = popular repos (more than 5k stars), star trends (new repos), and downloads (new GitHub-linked npm/PyPI packages).
- 2026-10-07: Momentum is **velocity, not volume**, for every feed: growth per day from snapshots, falling back to total ÷ age. Pools are 3 pages wide because APIs sort by volume. Why: totals barely change; velocity surfaces new, rising items.

- 2026-10-07: Setup is agent-driven (`skills/setup.md`, triggered by a missing `.env` or "set me up"). On desktop, keys are pasted into a local file the agent opens, never into chat. In the cloud, environment variables override `.env`; pasting into chat is the fallback. Why: an end user only needs Claude Code and a clone.

- 2026-10-07: PR review = two booleans on line 1 (`skills/pr.md`): Complete (fully wired, no stubs) and Irreversible (not undoable by revert). 🟢 merge / 🟡 read / 🔴 not ready. Adapted from Matt Pocock's `pr` skill (MIT). Why: the owner reviews in one line.

## Open
- `USER_GOAL` is a draft in `AGENTS.md`.
- Filter-question ladder is DRAFT; needs an owner interview.
