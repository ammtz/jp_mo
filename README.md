# jp_mo

A filtered, sorted morning newspaper. Every day at 7AM ET it scans what's rising on GitHub, npm/PyPI and YouTube, asks one question about each item, and prints only the 4-5 worth your time.

## Quick start
1. Clone this repo into Claude Code (desktop or phone) or any coding agent.
2. Say **"set me up"**.
3. Paste the keys it asks for into the file it opens. Only one is required: a Vercel AI Gateway key.

The agent handles the rest (`skills/setup.md`): config, a connection check, your first edition, and the daily schedule.

## Keys
See `.env.example`: what each key is for, where to get it, and what happens without it.

## How it works
`VISION.md` → `AGENTS.md` → `SPEC.md`. Decisions are in `DECISIONS.md`.

## License
FSL-1.1-MIT (`LICENSE.md`): becomes MIT two years after each release.
