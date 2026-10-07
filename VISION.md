# Vision

jp_mo is a **filtered, sorted morning newspaper**. Every day at 7AM ET it surfaces the 4-5 things worth the owner's time, the crème de la crème, and nothing else. It exists to feed one goal: ideas and solutions the owner can implement and manage.

## Principles
1. **Signal over volume.** Roughly 10 items clear the filter per run; the top 4-5 get printed. Fewer, better.
2. **One question decides.** Every candidate faces the same binary question (see `context/filter_rules.md`). Pass = Jev score >= 0.75.
3. **Self-calibrating.** If the filter passes too much or too little, the question gets tightened or loosened, never the threshold.
4. **Interview-built.** Context lives in `/context`, process lives in `/skills`. Both grow by interviewing the owner.
5. **Agent-agnostic and cheap.** Plain markdown and plain scripts; any model can run it. Models only do judgment.
6. **FSL-1.1-MIT.** We don't intend to monetize, but destiny is all. License keeps the option open. Nothing added may conflict with it.
7. **Anonymous by default.** The code is public; the owner isn't. Nothing carrying the owner's name or email goes public without explicit approval.

## Non-goals
Feeds, infinite scroll, dashboards, anything that makes the morning longer. Vendor lock-in.
