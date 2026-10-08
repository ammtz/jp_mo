# Skill: first-run setup

**Trigger:** run this before anything else when `.env` does not exist **and** `AI_GATEWAY_API_KEY` is not set in the environment, or when the user says "set me up", "setup", or "install".

Goal: a person who has only cloned the repo into an agent (Claude Code on desktop or phone) ends with working keys, a passing `check`, a first edition, and optionally the 7AM job. Keep it conversational: one step at a time, short messages, no jargon.

`.env.example` is the source of truth for which keys exist, whether each is required, where to get it, and what permissions it needs. Read it; don't hard-code the list here.

## Key-handling rules (always)
- **Never print, `cat`, echo, or log the contents of `.env`** or any key. Check keys only by presence, length, and prefix.
- Best path: the user pastes keys into a file **on their own machine**, so keys never enter the chat.
- If a key is pasted into chat anyway (the fallback), write it to `.env` with a script without echoing it back. Tell the user once: "That key is now in this chat's history. It's scoped and low-risk, but you can rotate it later."
- `.env` is gitignored and gets `chmod 600`. Never commit it, and never put keys anywhere else in the repo.

## Steps

### 1. Where are we running?
Detect it, don't ask: if `uname`/`$OS` show macOS, Windows or Linux with a desktop, it's **desktop**. Claude Code on the web or phone (cloud session, `CLAUDE_CODE_REMOTE=true` or no GUI available) is **cloud**.

Check `python3 --version` ≥ 3.11. If it's older or missing, tell the user how to install it (macOS: `brew install python@3.12` or python.org) and stop until it's done.

### 2. Create `.env`
Copy `.env.example` to `.env` (skip if it exists; never overwrite one that has keys), then `chmod 600 .env`.

### 3. Tell the user which keys to get
From `.env.example`, list the keys in order **required → recommended → optional**. For each one give a single line: what it's for, the link, and the 1-2 settings that matter. Example:
- **AI_GATEWAY_API_KEY (required):** the judge. https://vercel.com/dashboard → AI Gateway → API Keys → Create. Or run `npx vercel ai-gateway setup`. Use a real API key, not an OIDC token.
- **GITHUB_TOKEN (recommended):** https://github.com/settings/personal-access-tokens/new → "Public repositories (read-only)", no permissions, long expiry.
- **YOUTUBE_API_KEY (optional):** https://console.cloud.google.com/apis/library/youtube.googleapis.com → Enable → Credentials → API key → restrict it to YouTube Data API v3.

Tell them that only the first key is needed to start, and they can add the rest any time.

### 4. Get the keys in
**Desktop:** open `.env` in their editor and say: "Paste each key right after its `=`, no spaces or quotes, then save and tell me 'done'."
- macOS: `open -e .env`. Windows: `notepad .env`. Linux: `xdg-open .env`, or `nano .env` for them to run with `!`.
- Remind macOS users that Finder hides dotfiles (Cmd+Shift+. shows them).

**Cloud:** offer, in this order:
1. Add the keys as **environment variables** in the cloud environment's settings, then start a new session. Real env vars override `.env`, so no file is needed.
2. Fallback: paste them in chat and follow the key-handling rules above.

### 5. Verify
Report each key as present or empty, with its length, without showing values. Flag wrapping quotes and spaces.

Then run `python -m jp_mo check` and show its table.
- Gateway failing → fix it before going on (wrong key, OIDC token instead of API key, or no gateway credits).
- Any other failure → explain what's lost (see `.env.example`) and continue.
- If the code isn't built yet, do the same checks by hand with the calls listed under "Wiring check" in `SPEC.md`.

### 6. First edition
Run `python -m jp_mo build` and show the edition. Explain: "Tomorrow's ranking will be sharper; velocity needs one day of history." Then explain grading: tick one box per note in the file, or tell the agent "grade 1 great, 2 bad" (it runs `python -m jp_mo grade 1=great 2=bad`). Grades drive the weekly calibration loop.

### 7. Schedule (ask, don't assume)
"Want this every day at 7AM ET?" Recommended: **GitHub Actions + Upstash Redis + Notion**, with no machine left on. Steps: create the Upstash database (see `.env.example`), add its URL and token to `.env`, run `check`, then set the repo secrets from `.env` with `gh secret set NAME` (pipe the values; never echo them), and trigger the workflow once from the Actions tab. Local alternatives:
- **macOS:** write `~/Library/LaunchAgents/com.jp_mo.morning.plist` (`StartCalendarInterval` Hour 7 converted to local time, `WorkingDirectory` = repo, `ProgramArguments` = python3 -m jp_mo build), then `launchctl load` it.
- **Linux:** add a crontab line with `CRON_TZ=America/New_York`.
- **Windows:** `schtasks /create /sc daily /st 07:00 ...` adjusted to ET.
- **Cloud/phone only:** a scheduled cloud agent can run the build, but each run starts fresh. Velocity falls back to averages and calibration stays at level 0. Say this plainly and recommend a desktop or always-on machine for the full experience.

Ask how they want to read and grade. Recommended: **Notion** (`NOTION_TOKEN` + `NOTION_PAGE_ID`, see `.env.example`): notes land in a database on their phone, with a one-tap Grade. Otherwise point `EDITION_DIR` at a synced folder (iCloud Drive, Dropbox) and grade by ticking boxes in the file.

### 8. Wrap up
In 3 lines or fewer: what's working, what's skipped (missing optional keys), and when the next edition arrives. Don't commit or push anything.
