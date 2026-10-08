import json
from datetime import date

import pytest

from jp_mo import __main__ as cli, curator, grades, pipeline
from jp_mo.dryrun import FixtureHttp
from jp_mo.judge import JudgeError, StubJudge
from tests.conftest import NOW, ROOT, cand
from tests.test_judge import FakeHttp

DAY = date(2026, 10, 7)


# --- curator ----------------------------------------------------------------------
def test_parse_keeps_well_formed_notes_only():
    content = 'Here you go:\n[{"id": "a", "what": "W", "apply": "A", "effort": "m", "effect": "Simpler"},' \
              ' {"id": "b", "what": "", "apply": "A"}, {"id": "zzz", "what": "W", "apply": "A"},' \
              ' {"id": "c", "what": "W", "apply": "A", "effort": "huge", "effect": "fun"}]'
    notes = curator.parse(content, {"a", "b", "c"})
    assert set(notes) == {"a", "c"}
    assert (notes["a"].effort, notes["a"].effect) == ("M", "simpler")
    assert (notes["c"].effort, notes["c"].effect) == ("?", "?")
    assert curator.parse("no json here", {"a"}) == {}
    assert curator.parse("[not json]", {"a"}) == {}


def test_curator_request_carries_system_brief_and_items(cfg):
    reply = {"choices": [{"message": {"content": '[{"id": "gh:a", "what": "W", "apply": "A", "effort": "S", "effect": "efficient"}]'}}],
             "providerMetadata": {"gateway": {"cost": "0.03"}}}
    http = FakeHttp([reply])
    cfg.root = ROOT
    c = curator.Curator(cfg, http)
    notes = c.write([cand("gh:a", readme="r" * 50)], cfg.goal, ROOT)
    url, body, _ = http.posts[0]
    prompt = body["messages"][0]["content"]
    assert url.endswith("/v1/chat/completions") and body["model"] == "moonshotai/kimi-k3"
    assert "Vision" in prompt and "pipeline.py" in prompt and "id: gh:a" in prompt
    assert notes["gh:a"].effect == "efficient" and c.meta.cost_usd == pytest.approx(0.03)


def test_system_brief_reads_vision_and_layout():
    vision, layout = curator.system_brief(ROOT)
    assert vision.startswith("# Vision") and "judge.py" in layout


# --- grades -----------------------------------------------------------------------
EDITION = """# jp_mo · Wed 2026-10-07

## 1. a
Grade: [x] great [ ] good [ ] bad
<!-- id: gh:a -->

## 2. b
Grade: [ ] great [ ] good [ ] bad
<!-- id: gh:b -->

## 3. c
Grade: [X] great [x] good [ ] bad
<!-- id: gh:c -->
"""


def test_parse_edition_reads_ticks_and_ignores_ambiguous():
    assert grades.parse_edition(EDITION) == [("gh:a", "great"), ("gh:b", None), ("gh:c", None)]


def test_harvest_and_count_since(tmp_path):
    (tmp_path / "edition_2026-10-07.md").write_text(EDITION)
    (tmp_path / "edition_2026-10-09.md").write_text(EDITION.replace("[x] great", "[x] bad"))
    (tmp_path / "dryrun_2026-10-09.md").write_text(EDITION)            # never counted
    g = grades.harvest(tmp_path)
    assert g == {"2026-10-07|gh:a": "great", "2026-10-09|gh:a": "bad"}
    assert grades.count_since(g, date(2026, 10, 7)) == 1 and grades.count_since(g, None) == 2


def test_set_grades_ticks_one_box_and_validates(tmp_path):
    p = tmp_path / "edition_2026-10-07.md"
    p.write_text(EDITION)
    grades.set_grades(p, {2: "good", 1: "bad"})
    assert grades.parse_edition(p.read_text())[:2] == [("gh:a", "bad"), ("gh:b", "good")]
    with pytest.raises(ValueError):
        grades.set_grades(p, {9: "good"})
    with pytest.raises(ValueError):
        grades.set_grades(p, {1: "meh"})


# --- pipeline + CLI ------------------------------------------------------------------
def passing_judge():
    j = StubJudge()
    j.ask = lambda state, qs: {k: 0.9 for k in qs}
    return j


def test_build_with_curator_writes_notes_and_sums_cost(cfg):
    cur = curator.StubCurator()
    cur.meta.cost_usd = 0.04
    s = pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY, curator=cur)
    text = (cfg.edition_dir / "edition_2026-10-07.md").read_text()
    assert s["notes"] == 5 and text.count("**For jp_mo:**") == 5 and text.count("Grade: [ ]") == 5
    assert s["cost_usd"] == pytest.approx(0.04) and "curator stub" in text


def test_curator_failure_never_blocks_the_edition(cfg):
    s = pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY, curator=curator.StubCurator(fail=True))
    text = (cfg.edition_dir / "edition_2026-10-07.md").read_text()
    assert s["status"] == "ok" and s["notes"] == 0 and "curator failed" in text
    assert text.count("Grade: [ ]") == 5


def test_build_harvests_grades_from_past_editions(cfg):
    cfg.edition_dir.mkdir(parents=True)
    (cfg.edition_dir / "edition_2026-10-06.md").write_text(EDITION)
    pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY)
    assert json.loads((cfg.state_dir / "grades.json").read_text()) == {"2026-10-06|gh:a": "great"}


def test_cli_grade_and_grades(cfg, monkeypatch, capsys):
    pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY)
    monkeypatch.setattr(cli.config, "load", lambda: cfg)
    assert cli.main(["grade", "--date", "2026-10-07", "1=great", "2=BAD"]) == 0
    assert cli.main(["grade", "--date", "2026-10-07", "9=great"]) == 1
    capsys.readouterr()
    assert cli.main(["grades"]) == 0
    out = capsys.readouterr().out
    assert "2 total (1 great, 0 good, 1 bad)" in out and "waiting for grades (2/20)" in out


def test_cost_read_from_chat_usage_and_jev_metadata(cfg):
    from jp_mo.judge import JevJudge
    j = JevJudge(cfg, None)
    j._account({"usage": {"cost": 0.002, "prompt_tokens": 10}})
    j._account({"providerMetadata": {"gateway": {"cost": "0.001"}}, "usage": {"inputTokens": 5}})
    assert j.meta.cost_usd == pytest.approx(0.003) and j.meta.input_tokens == 15


def test_readme_budget_skips_unstarted_fetches():
    from jp_mo import readme
    ticks = iter([0, 0, 999, 999, 999, 999])
    cs = [cand(f"gh:{i}", repo=f"o/r{i}") for i in range(3)]
    readme.WORKERS, saved = 1, readme.WORKERS
    try:
        readme.attach(FixtureHttp(), "", cs, budget_s=10, clock=lambda: next(ticks))
    finally:
        readme.WORKERS = saved
    assert cs[0].readme and not cs[1].readme and not cs[2].readme
