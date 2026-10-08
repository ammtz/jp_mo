# Sources

Four feeds. Each is fetched by a plain script (no model). Any feed that errors is recorded in the footer as failed; the run continues with the rest. Endpoints checked 2026-10-07.

| id | What | Endpoint | Auth | Pool |
|---|---|---|---|---|
| `yt` | YouTube popular | `GET https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&chart=mostPopular&regionCode=US&maxResults=50` (twice: no category, and `videoCategoryId=28` Science & Technology) | `YOUTUBE_API_KEY` (Data API v3, 1 quota unit per call) | up to 100 |
| `gh_stars` | GitHub star trends (new repos) | `GET https://api.github.com/search/repositories?q=created:>{today-7d}&sort=stars&order=desc&per_page=50`, pages 1-3 | `GITHUB_TOKEN` | 150 |
| `gh_popular` | GitHub popular repos | `GET https://api.github.com/search/repositories?q=stars:>5000+pushed:>{today-1d}&sort=stars&order=desc&per_page=50`, pages 1-3 | `GITHUB_TOKEN` | 150 |
| `pkg` | GitHub download trends | `GET https://packages.ecosyste.ms/api/v1/registries/{reg}/packages?sort=downloads&order=desc&per_page=50&created_after={today-30d}`, pages 1-3, for `reg` in `npmjs.org`, `pypi.org` | none (send a `User-Agent`) | up to 300 |

The APIs can only sort by volume, so pools are deliberately wide (3 pages). Ranking by velocity happens locally.

## Momentum = velocity, not volume
Totals barely move day to day. What matters is how fast something is growing, and new items grow fastest. Every feed uses the same rule:

1. **Measured velocity (preferred, all feeds except `pkg`):** `(metric_now - metric_prev) / days_between`, from `state/snapshots.json` (`{candidate id: {metric, at}}`), when the previous snapshot is 12-72 h old.
2. **Average velocity (first sight, or a stale snapshot):** `metric_now / age_in_days`, where age counts from creation or publish (minimum 1 hour). For `pkg`, `metric_now` is the last-month download count and age is capped at 30 days.
`pkg` always uses the average: its metric is a rolling last-month window, so a day-over-day difference measures acceleration, not velocity.
3. Rewrite the snapshot for every candidate fetched, every run. Prune entries older than 30 days.

| feed | metric | footer label |
|---|---|---|
| `yt` | `viewCount` (age from `publishedAt`) | `+N views/day` |
| `gh_stars`, `gh_popular` | `stargazers_count` (age from `created_at`) | `+N stars/day` |
| `pkg` | `downloads` (age from `first_release_published_at`) | `+N downloads/day` |

## Notes per feed
- **yt:** if the category call errors, skip it and keep the unfiltered call.
- **gh_stars:** GitHub has no official trending API, so this means repos created in the last 7 days. Don't scrape github.com/trending.
- **gh_popular:** established repos (more than 5k stars) pushed in the last day. Items from this feed stay in the seen-filter for **30 days** instead of 7, so giants don't come back weekly.
- **pkg:** GitHub doesn't publish download counts, so this uses packages new to npm/PyPI (last 30 days, by ecosyste.ms index date). Keep only packages whose `repository_url` is on github.com. Confirmed by owner 2026-10-07.

## README excerpt (GitHub-backed items)
For every candidate with a `repo` (all `gh_stars` and `gh_popular`, and `pkg` items after the github.com filter): `GET https://api.github.com/repos/{repo}/readme` with `Accept: application/vnd.github.raw+json`.
- **Clean before counting:** drop HTML tags, image/badge markdown (`![...](...)`, `[![...](...)](...)`), link URLs (keep the link text), code fences, headings' `#`, and collapse whitespace.
- Store the first **1,000** cleaned chars as `readme`. Pass 1 uses `readme[:500]`; pass 2 uses `readme[:1000]`.
- No README or 404 → `readme = ""` (judged on description only, single pass). Fetch errors don't fail the feed.

## Normalized candidate (all feeds)
`id` (`{source}:{native id}`), `source`, `title`, `url`, `summary` (≤ 500 chars, plain text), `published_at` (ISO 8601), `momentum` (float, velocity per day), `repo` (lowercase `owner/name` or null), `readme` (cleaned, ≤ 1,000 chars, or empty), `extra` (dict, raw metrics).

## Dedupe
1. Same `url` → one candidate.
2. Same `repo` across **different** feeds (`gh_stars`, `gh_popular`, `pkg`) → merge into one candidate: keep the title and URL in that order of preference, and record all sources. Packages from one monorepo (same feed, same repo) stay separate items, and they get no README excerpt, because the repo README describes the monorepo, not the package.
3. Anything printed in the last 7 editions (30 for `gh_popular`; a merged item uses the longest window among its feeds; see `state/seen.json`) is dropped. Printing a repo blocks its packages too. Printing a package doesn't block its monorepo siblings.
