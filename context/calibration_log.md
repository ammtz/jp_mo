# Calibration log

The owner's grades are the answer key for the filter question. Each round of the calibration loop (`skills/calibrate_filter.md`) appends here. Later rounds override earlier grades for the same item.

## Round 1: 2026-10-07
Pool: 682 candidates (one live fetch). 24 items graded across two passes. Each variant was scored on the full pool with Jev (~$0.008 per variant, ~$0.07 total).

**Owner's criteria:** grades are GREAT / GOOD / BAD (grey, not binary). Wants "diamonds in the rough" that make *the system itself* (this newsletter) more sellable, more efficient, or simpler; removing things counts. Speed of action doesn't matter. In scope: AI agents & dev tools, self-hosted & infra, data. Hard no: entertainment & news. Old, well-known, broad tools are BAD (no novelty).

| variant | state | order¹ | BAD avg P | pool ≥ 0.75 | BAD passing |
|---|---|---|---|---|---|
| old level 0 | generic reader | 61% | 0.53 | 19 | yes |
| v5 | system | 78% | 0.28 | 11 | ollama |
| v6 (novelty required) | system | 82% | 0.22 | 1 | none |
| **v7 (novelty as exclusion) → level 0** | system | **81%** | **0.22** | **6** | **none** |

¹ Share of (better-graded, worse-graded) pairs that Jev ranks in the right order.

Adopted: v7 as level 0, v5 as level -1 (natural loosening step, since v7 passes 6, below the 8-12 band), and novelty/specificity as level +1.

### Grades
| item | grade |
|---|---|
| `gh_popular:immich-app/immich` | GREAT |
| `gh_popular:juliusbrussee/caveman` | GREAT |
| `gh_popular:tashfeenahmed/freellmapi` | GREAT |
| `gh_popular:tryghost/ghost` | GREAT |
| `gh_stars:elstongun/leviathan` | GREAT |
| `gh_stars:kodama-technology/chat_ui` | GREAT |
| `pkg:npmjs.org:@deepseek-ai/dsh-experimental-tool-agent-team` | GREAT |
| `pkg:pypi.org:agentic-evals` | GREAT |
| `pkg:pypi.org:decider-ai` | GREAT |
| `pkg:pypi.org:decision-circuits` | GREAT |
| `pkg:pypi.org:octop-memory` | GREAT |
| `gh_popular:astral-sh/uv` | GOOD |
| `gh_stars:hiteater-wzm/eeo` | GOOD |
| `gh_stars:nuglifeleoji/sentry` | GOOD |
| `gh_stars:zzzz7788990213-ops/evovlm` | GOOD |
| `pkg:pypi.org:diff_cover` | GOOD |
| `gh_popular:kubernetes/kubernetes` | BAD |
| `gh_popular:ollama/ollama` | BAD |
| `gh_stars:atmirrr/persian-motion-director` | BAD |
| `gh_stars:jarrodwatts/claude-image-view` | BAD |
| `pkg:pypi.org:audio-transcribe-cli-mcp` | BAD |
| `yt:n8y4bTDNf18` | BAD |
| `yt:w2OuOI4hzi4` | BAD |
