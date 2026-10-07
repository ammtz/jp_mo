# jp_mo: North Star (agent-agnostic)

Canonical instructions for any coding/chat agent (Claude, Kimi, Grok, Codex, etc.). Tool-specific files like `CLAUDE.md` only point here.

A filtered, sorted morning newspaper. Read `VISION.md` first. What we know lives in `context/`; how we do things lives in `skills/`. Load the relevant files before any task. Assumptions are the enemy: if the answer isn't in the files, ask.

## First run
If `.env` doesn't exist and `AI_GATEWAY_API_KEY` isn't set in the environment, or the user says "set me up", follow `skills/setup.md` before anything else. Never print key values.

## Init (global variables, referenced by the filter question)
- `USER_NAME`: [owner]   (placeholder on purpose; real name stays out of public files)
- `USER_GOAL`: Come up with ideas and solutions I can personally implement and manage, solved through interviews. (DRAFT, owner to confirm)

## Stack
Python backend. Frontend: JS/TS, HTML, CSS. Mobile welcome (Android/iOS, usable on an iPad or Surface-class tablet). Prefer small, boring, single-owner-maintainable choices.

## Working style
- Peer, not assistant. Short and sweet. Act, then report in a line or two.
- Owner is an engineer. Skip basics.
- Minimal tool/connector use. Prefer plain git, local files, and plain HTTP/search.
- Cost matters: do deterministic work (fetch, count, sort, format) in plain scripts, and use a model only for judgment.

## Hard rules
1. License is FSL-1.1-MIT (`LICENSE.md`). Nothing conflicting goes in (no GPL/AGPL code, etc.). Flag doubts.
2. Nothing with the owner's name or email goes into any public file, commit, or metadata without explicit approval.
3. No push, publish, or release without explicit approval.
4. The Jev threshold stays **0.75**. Calibrate by changing the question, never the threshold.
5. Lasting decisions go in `DECISIONS.md`, one line, dated.
6. Stay model-agnostic: no instructions that only work in one vendor's tool.

## Map
- `context/`: sources.md, filter_rules.md, sort_rules.md, memory.md
- `skills/`: setup.md, edition_build.md, calibrate_filter.md
- `SCHEDULED.md`: the 7AM job
- `SPEC.md`: build spec (code layout, Jev call, acceptance)
