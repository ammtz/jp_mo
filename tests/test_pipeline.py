import json
from datetime import date

from jp_mo import config, pipeline, render
from jp_mo.dryrun import FixtureHttp
from jp_mo.judge import StubJudge
from jp_mo.curator import Note
from jp_mo.models import Judgement
from jp_mo.net import HttpError
from tests.conftest import NOW, ROOT, cand

DAY = date(2026, 10, 7)


def test_render_matches_golden():
    a = cand("gh_stars:o/a", momentum=1234.4, summary="First item.")
    a.title, a.url, a.sources = "o/a", "https://github.com/o/a", ["gh_stars", "pkg"]
    b = cand("yt:v", "yt", momentum=50000, summary="word " * 60)
    b.title, b.url = "A video", "https://www.youtube.com/watch?v=v"
    stats = {"scanned": 412, "second_pass": 9, "passed": 10, "level": 0, "feeds_failed": [],
             "judge_model": "typesafe-ai/jev", "curator_model": "moonshotai/kimi-k3", "cost_usd": 0.0449}
    notes = {a.id: Note("A tiny thing.", "Swap it into jp_mo/net.py to drop retries code.", "S", "simpler")}
    text = render.edition(DAY, [a, b], {a.id: Judgement(0.91), b.id: Judgement(0.8)}, stats, notes)
    assert text == (ROOT / "tests" / "fixtures" / "golden_edition.md").read_text()


def test_no_edition_note():
    text = render.no_edition(DAY, "judge unavailable", ["yt"])
    assert "No edition today: judge unavailable." in text and "feeds failed: yt" in text


def every_repo_passes(cid):
    return 0.9 if cid.startswith(("gh_", "pkg")) else 0.1


def test_full_build_offline_persists_state(cfg):
    judge = StubJudge()
    judge.ask = lambda state, qs: {k: every_repo_passes(k) for k in qs}
    s = pipeline.build(cfg, FixtureHttp(), judge, NOW, DAY)
    assert s["status"] == "ok" and s["feeds_failed"] == []
    edition = (cfg.edition_dir / "edition_2026-10-07.md").read_text()
    assert edition.startswith("# jp_mo · Wed 2026-10-07")
    assert edition.count("\n## ") == 5
    assert "YouTube" not in edition
    st = cfg.state_dir
    assert json.loads((st / "state.json").read_text())["level"] == 0
    assert len((st / "log.jsonl").read_text().splitlines()) == 1
    assert len(json.loads((st / "seen.json").read_text())) >= 5
    assert json.loads((st / "snapshots.json").read_text())

    # next day: printed items are filtered out as seen
    s2 = pipeline.build(cfg, FixtureHttp(), judge, NOW, date(2026, 10, 8))
    assert s2["scanned"] < s["scanned"]


def test_failed_feed_listed_and_calibration_skipped(cfg):
    cfg.youtube_key = ""
    judge = StubJudge()
    judge.ask = lambda state, qs: {k: 0.9 for k in qs}       # far above band
    for d in (DAY, date(2026, 10, 8), date(2026, 10, 9)):
        pipeline.build(cfg, FixtureHttp(), judge, NOW, d)
    edition = (cfg.edition_dir / "edition_2026-10-09.md").read_text()
    assert "feeds failed: yt" in edition
    assert json.loads((cfg.state_dir / "state.json").read_text())["level"] == 0


def test_judge_down_writes_no_edition_and_keeps_level(cfg):
    class Down(StubJudge):
        def ask(self, state, qs):
            from jp_mo.judge import JudgeError
            raise JudgeError("gateway 503")
    s = pipeline.build(cfg, FixtureHttp(), Down(), NOW, DAY)
    assert s["status"] == "no edition: judge unavailable"
    assert "No edition today" in (cfg.edition_dir / "edition_2026-10-07.md").read_text()


def test_all_feeds_down_writes_no_edition(cfg):
    class Down(FixtureHttp):
        def get_json(self, url, headers=None):
            raise HttpError(503, "down")
    s = pipeline.build(cfg, Down(), StubJudge(), NOW, DAY)
    assert s["status"].startswith("no edition") and len(s["feeds_failed"]) == 4


def test_dry_run_writes_nothing_to_state(cfg):
    pipeline.build(cfg, FixtureHttp(), StubJudge(), NOW, DAY, dry_run=True)
    assert (cfg.edition_dir / "dryrun_2026-10-07.md").exists()
    assert not cfg.state_dir.exists()


def test_config_env_overrides_file_and_strips_quotes(tmp_path):
    (tmp_path / ".env").write_text('AI_GATEWAY_API_KEY="from-file"\nJUDGE=jev\nGITHUB_TOKEN=\n')
    c = config.load(tmp_path, environ={})
    assert c.gateway_key == "from-file" and c.github_token == ""
    c = config.load(tmp_path, environ={"AI_GATEWAY_API_KEY": "from-env"})
    assert c.gateway_key == "from-env"
    assert c.goal == config.DEFAULT_GOAL


def test_goal_read_from_agents_md(cfg):
    assert cfg.goal == "Build small things."


# --- review fixes (PR #2) --------------------------------------------------------
def passing_judge():
    j = StubJudge()
    j.ask = lambda state, qs: {k: 0.9 for k in qs}
    return j


def test_same_day_rerun_is_refused_without_force(cfg):
    pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY)
    first = (cfg.edition_dir / "edition_2026-10-07.md").read_text()
    s = pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY)
    assert s["status"] == "skipped: already built"
    assert (cfg.edition_dir / "edition_2026-10-07.md").read_text() == first
    assert len((cfg.state_dir / "log.jsonl").read_text().splitlines()) == 1


def test_force_rebuild_reproduces_the_day_and_skips_calibration(cfg):
    pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY)
    first = (cfg.edition_dir / "edition_2026-10-07.md").read_text()
    streak = json.loads((cfg.state_dir / "state.json").read_text())["streak"]
    s = pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY, force=True)
    assert s["status"] == "ok" and s["rebuild"] is True
    assert (cfg.edition_dir / "edition_2026-10-07.md").read_text() == first   # same items, not the next 5
    assert json.loads((cfg.state_dir / "state.json").read_text())["streak"] == streak


def test_no_edition_day_can_be_retried_without_force(cfg):
    class Down(StubJudge):
        def ask(self, state, qs):
            from jp_mo.judge import JudgeError
            raise JudgeError("gateway 503")
    pipeline.build(cfg, FixtureHttp(), Down(), NOW, DAY)
    assert pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY)["status"] == "ok"


def test_log_records_each_printed_p_and_histogram(cfg):
    pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY)
    entry = json.loads((cfg.state_dir / "log.jsonl").read_text().splitlines()[-1])
    assert all(item["p"] == 0.9 and item["pass"] == 1 for item in entry["printed"])
    assert sum(entry["p_hist"]) == entry["scanned"] and entry["p_hist"][9] == entry["scanned"]


def test_monorepo_packages_get_no_repo_readme(cfg):
    from jp_mo import readme
    a = cand("pkg:npmjs.org:@s/a", "pkg", repo="o/mono")
    b = cand("pkg:npmjs.org:@s/b", "pkg", repo="o/mono")
    solo = cand("pkg:npmjs.org:solo", "pkg", repo="o/solo")
    readme.attach(FixtureHttp(), "", [a, b, solo])
    assert a.readme == "" and b.readme == "" and solo.readme
