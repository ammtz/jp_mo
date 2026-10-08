# Build spec (v1)

What to build so `python -m jp_mo build` produces today's edition. Behavior lives in `context/` and `skills/`; this file covers code shape, the judge, and when it's done.

## Constraints
- Python 3.11+, **stdlib only** (`urllib`, `json`, `dataclasses`, `zoneinfo`). `pytest` for tests (dev only). No frameworks. Any added dependency must be FSL-compatible (no GPL/AGPL).
- Config comes only from env/`.env` (see `.env.example`). `.env`, `state/`, and `editions/` are gitignored.
- The model is used only in `judge.py`. Everything else is deterministic.

## Layout
```
jp_mo/
  __main__.py        CLI: build [--date] [--dry-run] [--judge jev|chat] [--force] [--no-curator] | grade | grades | check
  config.py          real env vars override .env (so cloud sessions need no file); validate required keys; never log values
  models.py          Candidate, Judgement, RunResult dataclasses
  sources/
    youtube.py       fetch() -> list[Candidate]
    github_stars.py
    github_popular.py
  velocity.py        momentum = velocity; reads/writes state/snapshots.json
    packages.py
    readme.py        fetch + clean README to <=1,000 chars
  normalize.py       dedupe/merge, seen-filter, momentum_pct
  judge.py           JevJudge, ChatJudge, StubJudge; ladder; two-pass run()
  pipeline.py        one edition end to end
  curator.py         agent curator: one chat call writes a news note per printed item
  grades.py          owner grades: tick boxes in edition files, harvested to state/grades.json
  net.py             stdlib HTTP (swappable)
  dryrun.py          FixtureHttp: serves tests/fixtures for --dry-run
  select.py          threshold 0.75 (constant, not config), sort, diversity
  render.py          edition + "no edition" markdown
  calibrate.py       level rule from skills/calibrate_filter.md
  state.py           state/state.json, state/log.jsonl, state/seen.json, state/snapshots.json
tests/               offline only; fixtures in tests/fixtures/*.json
.env.example
```
`filter_rules.md` and `sort_rules.md` are the spec. Their ladder text and weights are copied into code as constants, and a test asserts the ladder in code matches the table in `filter_rules.md` (parse the markdown table), so the two can't drift.

## Wiring check (`python -m jp_mo check`)
Tests each interface in `.env.example` with one minimal live call and prints a table: `interface · key present · HTTP status · latency · note`. Never prints key values.
- Gateway: one 1-question `/v1/evaluate` call (or 1 chat call when `JUDGE=chat`). **Required**: a failure here exits 1.
- GitHub: `GET /rate_limit`. Shows search and core limits, plus the token's expiry from the `github-authentication-token-expiration` header, with a warning when it's under 14 days away.
- YouTube: 1 `mostPopular` call with `maxResults=1`.
- ecosyste.ms: 1 package-list call with `per_page=1`.
- Optional feeds that fail are warnings (exit 0). A missing `STATE_DIR`/`EDITION_DIR` is created.

## Curator (agent, after select)
One `POST /v1/chat/completions` call per edition with `CURATOR_MODEL` (default `moonshotai/kimi-k3`). The prompt carries the system brief (`USER_GOAL`, `VISION.md`, and this file's Layout block) plus the printed items, and asks for JSON notes: `what` (one sentence), `apply` (the concrete change to this system: module, file, step), `effort` S/M/L, `effect` sellable/efficient/simpler. Malformed entries are dropped. Any failure falls back to the plain blurb and the footer says `curator failed`, so it never blocks an edition. Cost is read from `usage.cost`. Live 2026-10-07: 5 notes, about $0.067.

## Grading
Each note ends with `Grade: [ ] great [ ] good [ ] bad` and a hidden `<!-- id: … -->`. The owner ticks one box in any editor (synced folder, phone), or runs `python -m jp_mo grade 1=great 2=bad` (an agent can run this from chat). Every build, and `python -m jp_mo grades`, harvests all `edition_*.md` into `state/grades.json` (`{"date|id": grade}`). The edition files stay the source of truth. `grades` also reports calibration-loop readiness (20 new grades since the last round in `context/calibration_log.md`).

## Judge: Jev via Vercel AI Gateway
Setup: run `npx vercel ai-gateway setup`, then make sure `AI_GATEWAY_API_KEY` ends up in `.env`. Use an **API key**, not a `VERCEL_OIDC_TOKEN`: OIDC tokens are short-lived and a 7AM unattended job will find them expired.

Jev is a decision model, not a chat model. It does **not** use `/v1/chat/completions`:
```
POST {AI_GATEWAY_BASE_URL}/v1/evaluate
Authorization: Bearer {AI_GATEWAY_API_KEY}
{
  "model": "typesafe-ai/jev",
  "state": "<state text from filter_rules.md>",
  "questions": {
    "c0": {"type": "boolean", "instructions": "<per-candidate question text>"},
    "c1": {...}
  }
}
```
- Question keys are short (`c0`, `c1`, …) and map back to candidate ids locally.
- Questions in one request are answered independently and in parallel. Limits: 64k tokens total per request, and 32k for state + the longest question. Send **≤ 40 questions per request** (~18 requests per run) and truncate summaries to 500 chars.
- Read `answers[key].probability` (confirmed live 2026-10-07). A missing or non-numeric value means that candidate is `error`: excluded and counted in the footer.
- Record `model` (returns plain `typesafe-ai/jev`, no dated snapshot), cost from `providerMetadata.gateway.cost` (string, USD), and `usage.inputTokens`. Live 2-question call: 525 input tokens, $0.000022, 0.6 s.
- **Two passes:** pass 1 sends every candidate (README ≤ 500 chars). Pass 2 is a second `/v1/evaluate` batch containing only GitHub-backed items with a README and 0.50 ≤ P < 0.75, using README ≤ 1,000 chars. The final P is pass 2's. Constants: `THRESHOLD = 0.75`, `CLOSE_FLOOR = 0.50`, `README_P1 = 500`, `README_P2 = 1000`.
- Retry 429/529/5xx with exponential backoff (1 s, 4 s, 16 s), then fail the judge step. If the judge fails, the run writes "no edition: judge unavailable" and skips calibration.
- Cost is about $0.04 per 1M input tokens, so roughly 700 candidates × 300 tokens ≈ $0.01 per run.

**Fallback `ChatJudge`** (rule 6, model-agnostic): `POST {AI_GATEWAY_BASE_URL}/v1/chat/completions` with `CHAT_MODEL` (any gateway model, e.g. Kimi or Grok), `temperature: 0`, one candidate per call. The model must reply with only `{"p": <0-1>}`. Same threshold. Used when `JUDGE=chat`. Because its probabilities aren't calibrated like Jev's, the footer shows the judge name.

## Done when (acceptance)
1. `pytest` passes offline, covering: each source parser against a recorded fixture; dedupe/merge; momentum_pct; the threshold boundary (0.749 drops, 0.75 passes); sort and diversity; calibration (2-run streak, clamp, skip on failed feed); the ladder-matches-markdown test; velocity (measured from a 12-72 h snapshot, otherwise average over age; pkg age cap 30 d; min age 1 h; snapshot rewritten and pruned); 30-day seen window for gh_popular; Jev response parsing (`probability`, missing); README cleaning (badges/HTML/links stripped, 500/1,000 cuts); two-pass routing (0.49 → no pass 2, 0.50 and 0.749 → pass 2, 0.75 → no pass 2, no README → no pass 2, pass 2 overrides); and render output exactly matching a golden file.
2. `python -m jp_mo check` reports all four interfaces correctly, with the gateway required and the rest warnings.
3. `python -m jp_mo build --dry-run` with fixtures and a stub judge writes a correct edition without network access.
4. A live run with real keys writes `editions/edition_YYYY-MM-DD.md`, appends a log line, and finishes in < 3 min.
5. Removing one feed's key still produces an edition, with that feed listed as failed.
6. `grep` finds no owner name or email in the repo or in editions.

## Build order
1. models, config, state → 2. sources + readme + fixtures → 3. normalize → 4. select, render → 5. judge (stub, then Jev, then chat) → 6. calibrate → 7. CLI (`check` first, then `build`) + scheduler.

## Scheduling
Any runner works. Linux cron: `CRON_TZ=America/New_York` / `0 7 * * * cd /path/jp_mo && python -m jp_mo build`. On macOS use a launchd `StartCalendarInterval` (Hour 7) and make sure the Mac's timezone is ET, or convert the hour.
