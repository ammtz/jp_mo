# Skill: write a PR

Every PR body follows this shape, so the owner can review in one line and only reads further when the line says to. Adapted from Matt Pocock's `pr` skill (MIT), whose Summary visuals come from Dex Horthy's `show-me`. See Credits.

## The two questions (the whole review system)
Every PR answers exactly two questions, as booleans, on the first line of the body:

1. **Complete** = TRUE when every feature in this PR is fully implemented and wired end to end: no stubs, TODOs, fake data, or dead paths. FALSE otherwise, and the body must say what's missing.
2. **Irreversible** = TRUE when merging, or anything the PR has already done, can't be undone by `git revert`. See the one-way list below.

**Verdict line** (first line of the body, nothing above it):

| Complete | Irreversible | Verdict | Owner does |
|---|---|---|---|
| TRUE | FALSE | `🟢 MERGE` | skim the Summary, merge |
| TRUE | TRUE | `🟡 READ` | read Merge Danger slowly, then decide |
| FALSE | any | `🔴 NOT READY` | don't merge (open it as a draft) |

Format: `**Complete: TRUE · Irreversible: FALSE → 🟢 MERGE**`

Be hardest on yourself when claiming 🟢. The agent that wrote the change is grading it. When in doubt, Irreversible = TRUE.

## One-way list (this repo always counts these as Irreversible = TRUE)
- Sensitive things becoming public: secrets, personal data, private notes, or anything not meant for an open-source repo (pushing ordinary code and docs here is expected and doesn't count). Releases and deliveries that leave the machine (email, push) count too. A push can't be "unseen", even if the merge is reverted.
- License text or license grants. FSL's future MIT grant is irrevocable for every version already published.
- Owner's name or email, or any secret, in a file, commit, or metadata. Git history keeps it, so treat it as leaked and rotate the secret.
- Deleting or changing the format of `state/` (calibration level, run log, seen items, velocity snapshots) without a migration. History can't be refetched.
- Changing the 0.75 threshold (hard rule: never), or a scheduler change that can double-send or skip editions.
- New paid usage or a new external account/key requirement.

Everything else (code, docs, prompts, ladder wording, sort weights) is a two-way door.

## Body template
```markdown
**Complete: <TRUE|FALSE> · Irreversible: <TRUE|FALSE> → <🟢 MERGE|🟡 READ|🔴 NOT READY>**

## Summary
<one small visual + ≤ 3 lines of text>

## Evidence
- **Before:** <output / failing test / "doesn't exist">
- **After:** <output / passing test>

## Merge Danger
**Door:** <one-way | two-way>. <one line why>
**Blast radius:** <one word>. <one line on what breaks if this is wrong>

## Not done   ← only when Complete = FALSE
- <missing piece>
```

## Writing rules
- **No preamble.** The body starts with the verdict line. Keep prose short. Use the repo's words (edition, feed, ladder, level, velocity, judge).
- **Summary:** pick the *smallest* view that shows the change. Usually one, rarely more:
  - **file tree** for new or moved files,
  - **call tree** for runtime flow (`build → fetch → judge → select → render`),
  - **pseudocode** for logic,
  - **shaped `diff`** of any of the above when the point is what changed,
  - **Mermaid** only for multi-party flows (it renders on GitHub, not in a terminal).
- **Evidence** is a before/after, not a claim. Test output that failed and now passes, a real edition excerpt, or `check` output. "Tests pass" on its own isn't evidence. A docs-only PR shows the before/after of the docs' shape.
- **Merge Danger:** state the door as a claim the owner can disagree with. Blast radius names what breaks: e.g. *editions* (wrong items printed), *state* (calibration or velocity history), *setup* (new users can't get running), *public* (exposure).
- If the PR is too big to summarize in one visual, say so and propose a split. Don't hide it in a wall of text.
- Rewrite the body when the PR changes meaningfully during review.
- End with the attribution line your agent uses, if any.

## Credits
Format and Summary visuals adapted from [Matt Pocock's `pr` skill](https://github.com/mattpocock/skills/tree/main/skills/engineering/pr) (MIT), whose Summary visuals come from [Dex Horthy's `show-me`](https://github.com/humanlayer/skills) skill. The two-question verdict and the one-way list are jp_mo's own.
