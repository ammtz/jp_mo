"""normalize, velocity, select, calibrate, state, readme cleaning."""
from datetime import date, timedelta

from jp_mo import calibrate, normalize, select, velocity
from jp_mo.models import Judgement
from jp_mo.readme import clean
from jp_mo.state import State
from tests.conftest import NOW, cand


# --- dedupe / merge -------------------------------------------------------
def test_dedupe_merges_repo_across_feeds_keeping_preferred():
    pkg = cand("pkg:npmjs.org:x", "pkg", repo="o/x", url="https://npm/x")
    star = cand("gh_stars:o/x", "gh_stars", repo="o/x", url="https://github.com/o/x")
    out = normalize.dedupe([pkg, star])
    assert len(out) == 1 and out[0].id == "gh_stars:o/x"
    assert out[0].sources == ["gh_stars", "pkg"]


def test_dedupe_same_url():
    a, b = cand("yt:1", "yt", url="u"), cand("yt:1b", "yt", url="u")
    assert len(normalize.dedupe([a, b])) == 1


def test_momentum_pct_is_per_source():
    cs = [cand(f"yt:{i}", "yt", momentum=m) for i, m in enumerate([10, 20, 30])] + [cand("pkg:z", "pkg", momentum=1)]
    normalize.momentum_pct(cs)
    assert [c.momentum_pct for c in cs] == [0.0, 0.5, 1.0, 1.0]


# --- velocity -------------------------------------------------------------
def test_velocity_measured_from_snapshot_in_window():
    c = cand(metric=1300)
    snaps = {c.id: {"metric": 1000, "at": (NOW - timedelta(hours=24)).isoformat()}}
    new = velocity.compute([c], snaps, NOW)
    assert c.momentum == 300
    assert new[c.id] == {"metric": 1300, "at": NOW.isoformat()}


def test_velocity_falls_back_to_average_when_snapshot_stale_or_too_fresh():
    for hours in (6, 80):
        c = cand(metric=200, published_at=(NOW - timedelta(days=4)).isoformat())
        velocity.compute([c], {c.id: {"metric": 0, "at": (NOW - timedelta(hours=hours)).isoformat()}}, NOW)
        assert c.momentum == 50


def test_velocity_min_age_and_pkg_rules():
    fresh = cand(metric=10, published_at=NOW.isoformat())
    velocity.compute([fresh], {}, NOW)
    assert fresh.momentum == 240                     # 10 / (1/24 day)

    old_pkg = cand("pkg:r:p", "pkg", metric=3000, published_at=(NOW - timedelta(days=90)).isoformat())
    snaps = {old_pkg.id: {"metric": 0, "at": (NOW - timedelta(hours=24)).isoformat()}}
    velocity.compute([old_pkg], snaps, NOW)
    assert old_pkg.momentum == 100                   # always average, age capped at 30d


def test_velocity_never_negative_and_snapshots_pruned():
    c = cand(metric=90)
    snaps = {c.id: {"metric": 100, "at": (NOW - timedelta(hours=24)).isoformat()},
             "gone": {"metric": 1, "at": (NOW - timedelta(days=31)).isoformat()}}
    new = velocity.compute([c], snaps, NOW)
    assert c.momentum == 0 and "gone" not in new


# --- select ---------------------------------------------------------------
def test_threshold_boundary():
    a, b = cand("a"), cand("b")
    j = {"a": Judgement(0.749), "b": Judgement(0.75)}
    assert [c.id for c in select.passed([a, b], j)] == ["b"]
    assert select.THRESHOLD == 0.75


def test_errors_never_pass():
    assert select.passed([cand("a")], {"a": Judgement(None)}) == []


def test_score_weights():
    assert select.score(cand(pct=1.0), Judgement(0.8)) == 0.75 * 0.8 + 0.25


def test_pick_diversity_max_two_per_source():
    cs = [cand(f"gh:{i}", "gh_stars", pct=1.0) for i in range(4)] + [cand("yt:1", "yt"), cand("pkg:1", "pkg")]
    j = {c.id: Judgement(0.9) for c in cs}
    ids = {c.id for c in select.pick(cs, j)}
    # without the cap, the top 5 would be gh:0-3 + one other; with it, yt and pkg both make it
    assert ids == {"gh:0", "gh:1", "gh:2", "yt:1", "pkg:1"}


def test_pick_allows_third_when_nothing_else_left():
    cs = [cand(f"gh:{i}", "gh_stars") for i in range(4)]
    top = select.pick(cs, {c.id: Judgement(0.9 - i / 100) for i, c in enumerate(cs)})
    assert [c.id for c in top] == ["gh:0", "gh:1", "gh:2", "gh:3"]


def test_pick_ties_go_to_newer():
    old, new = cand("old", published_at="2026-10-01T00:00:00Z"), cand("new", published_at="2026-10-06T00:00:00Z")
    top = select.pick([old, new], {"old": Judgement(0.8), "new": Judgement(0.8)})
    assert [c.id for c in top] == ["new", "old"]


# --- calibrate ------------------------------------------------------------
BASE = {"level": 0, "streak_dir": None, "streak": 0, "bound_runs": 0}


def test_two_high_runs_raise_level_then_reset():
    s = calibrate.step(BASE, 15, True)
    assert s["level"] == 0 and s["streak"] == 1
    s = calibrate.step(s, 14, True)
    assert s["level"] == 1 and s["streak"] == 0


def test_two_low_runs_lower_level_and_in_band_resets():
    s = calibrate.step(BASE, 3, True)
    s = calibrate.step(s, 10, True)                 # in band: streak broken
    s = calibrate.step(s, 3, True)
    assert s["level"] == 0
    s = calibrate.step(s, 2, True)
    assert s["level"] == -1


def test_ineligible_runs_change_nothing():
    s = calibrate.step(BASE, 30, True)
    assert calibrate.step(s, 30, False) == {**s, "recalibrate": False}


def test_clamp_and_recalibrate_flag_at_bound():
    s = {**BASE, "level": 2}
    for _ in range(5):
        s = calibrate.step(s, 40, True)
    assert s["level"] == 2 and s["recalibrate"] is True


# --- state ----------------------------------------------------------------
def test_seen_windows(tmp_path):
    st = State(tmp_path)
    day = date(2026, 10, 7)
    pop, new = cand("gh_popular:o/p", "gh_popular", repo="o/p"), cand("yt:v", "yt")
    st.mark_seen([pop, new], day)
    later = day + timedelta(days=10)
    assert st.was_seen(pop, later) and not st.was_seen(new, later)
    assert not st.was_seen(pop, day + timedelta(days=30))
    # same repo arriving from another feed is still "seen"
    assert st.was_seen(cand("pkg:r:p", "pkg", repo="o/p"), later)


def test_state_roundtrip_and_dry_run_never_writes(tmp_path):
    st = State(tmp_path)
    st.core["level"] = 1
    st.save()
    assert State(tmp_path).core["level"] == 1
    dry = State(tmp_path / "dry", persist=False)
    dry.save()
    dry.append_log({"x": 1})
    assert not (tmp_path / "dry").exists()


# --- readme cleaning --------------------------------------------------------
def test_readme_clean_strips_noise_and_cuts():
    md = ('<p align="center"><img src="a.png"></p>\n# Title\n'
          '[![CI](https://b/c.svg)](https://ci) ![x](y.png)\n'
          'See the [docs](https://d) now.\n```bash\nrm -rf /\n```\nEnd.')
    assert clean(md) == "Title See the docs now. End."
    assert len(clean("word " * 400)) == 1000
    assert len(clean("word " * 400, 500)) == 500


# --- review fixes (PR #2) --------------------------------------------------------
def test_monorepo_packages_stay_separate_but_cross_feed_still_merges():
    star = cand("gh_stars:vercel/ai", "gh_stars", repo="vercel/ai", url="https://github.com/vercel/ai")
    p1 = cand("pkg:npmjs.org:@ai-sdk/a", "pkg", repo="vercel/ai", url="https://npm/a")
    p2 = cand("pkg:npmjs.org:@ai-sdk/b", "pkg", repo="vercel/ai", url="https://npm/b")
    out = normalize.dedupe([p1, p2])
    assert len(out) == 2
    out = normalize.dedupe([p1, star, p2])
    assert [c.id for c in out] == ["gh_stars:vercel/ai", "pkg:npmjs.org:@ai-sdk/b"]
    assert out[0].sources == ["gh_stars", "pkg"]


def test_printing_a_package_does_not_block_its_monorepo_siblings(tmp_path):
    st, day = State(tmp_path), date(2026, 10, 7)
    st.mark_seen([cand("pkg:npmjs.org:@ai-sdk/a", "pkg", repo="vercel/ai")], day)
    assert not st.was_seen(cand("pkg:npmjs.org:@ai-sdk/b", "pkg", repo="vercel/ai"), day)
    # but printing the repo itself does block its packages
    st.mark_seen([cand("gh_stars:vercel/ai", "gh_stars", repo="vercel/ai")], day)
    assert st.was_seen(cand("pkg:npmjs.org:@ai-sdk/b", "pkg", repo="vercel/ai"), day)


def test_merged_item_keeps_longest_seen_window(tmp_path):
    st, day = State(tmp_path), date(2026, 10, 7)
    merged = cand("gh_stars:o/new", "gh_stars", repo="o/new")
    merged.sources = ["gh_stars", "gh_popular"]
    st.mark_seen([merged], day)
    back = cand("gh_popular:o/new", "gh_popular", repo="o/new")
    assert st.was_seen(back, day + timedelta(days=10))
