from datetime import date

import pytest

from jp_mo import notion, pipeline
from jp_mo.curator import Note, StubCurator
from jp_mo.dryrun import FixtureHttp
from jp_mo.judge import StubJudge
from jp_mo.models import Judgement
from tests.conftest import NOW, cand

DAY = date(2026, 10, 7)
PAGE = "3f3e25c8-4dd1-805f-a426-e665d99d34b7"


class FakeNotion:
    """Minimal in-memory Notion API: blocks, databases, pages, query."""
    def __init__(self, existing_db=False, rows=None, stale=None, fail_on=None):
        """rows: graded rows (harvest query); stale: ungraded same-day rows (push query)."""
        self.calls, self.rows, self.stale, self.fail_on = [], list(rows or []), list(stale or []), fail_on
        self.children = [{"type": "paragraph"}]
        if existing_db:
            self.children.append({"type": "child_database", "id": "db-1", "child_database": {"title": notion.DB_TITLE}})

    def request(self, method, url, headers=None, body=None, raw=False):
        path = url.replace(notion.API, "")
        self.calls.append((method, path, body))
        assert headers["Notion-Version"] == notion.VERSION and headers["Authorization"] == "Bearer tok"
        if self.fail_on and self.fail_on in path:
            raise RuntimeError("notion down")
        if method == "GET" and "/children" in path:
            return 200, {}, {"results": self.children, "has_more": False}
        if method == "POST" and path == "/databases":
            return 200, {}, {"id": "db-new"}
        if method == "POST" and path.endswith("/query"):
            ungraded = "is_empty" in str(body["filter"])
            return 200, {}, {"results": self.stale if ungraded else self.rows, "has_more": False}
        if method == "GET" and path.startswith("/users"):
            return 200, {}, {"results": [{"type": "person", "id": "u-1"}, {"type": "bot", "id": "b"}]}
        return 200, {}, {"id": "x"}


def test_page_id_accepts_url_or_id():
    url = "https://app.notion.com/p/someone/jp_mo-3f3e25c84dd1805fa426e665d99d34b7"
    assert notion.page_id(url) == PAGE == notion.page_id(PAGE)
    with pytest.raises(ValueError):
        notion.page_id("nope")


def test_ensure_db_reuses_or_creates():
    assert notion.Notion(FakeNotion(existing_db=True), "tok").ensure_db(PAGE) == "db-1"
    fake = FakeNotion()
    assert notion.Notion(fake, "tok").ensure_db(PAGE) == "db-new"
    props = fake.calls[-1][2]["properties"]
    assert [o["name"] for o in props["Grade"]["select"]["options"]] == ["GREAT", "GOOD", "BAD"]


def test_push_archives_only_ungraded_same_day_rows_then_creates_notes():
    stale = [{"id": "old-1"}]
    fake = FakeNotion(stale=stale)
    a, b = cand("gh:a", summary="sum a"), cand("gh:b", summary="sum b")
    notes = {"gh:a": Note("W", "Apply A.", "S", "simpler")}
    n = notion.Notion(fake, "tok").push("db-1", DAY, [a, b], {"gh:a": Judgement(0.812), "gh:b": Judgement(0.8)},
                                        notes, lambda c: "GitHub new", mention="u-1")
    assert n == 2
    query = next(c for c in fake.calls if c[1].endswith("/query"))[2]["filter"]["and"]
    assert {"property": "Grade", "select": {"is_empty": True}} in query
    assert ("PATCH", "/pages/old-1", {"archived": True}) in fake.calls
    pages = [c[2] for c in fake.calls if c[:2] == ("POST", "/pages")]
    first, second = pages
    assert first["properties"]["Note"]["title"][0]["text"]["content"] == "1. gh:a"
    assert first["properties"]["P"]["number"] == 0.81 and first["properties"]["Effect"] == {"select": {"name": "simpler"}}
    assert first["children"][0]["paragraph"]["rich_text"][0]["mention"]["user"]["id"] == "u-1"
    assert second["properties"]["What"]["rich_text"][0]["text"]["content"] == "sum b"      # no note: blurb
    assert second["properties"]["Effort"] == {"select": None}


def test_harvest_reads_grades():
    row = {"properties": {"Date": {"date": {"start": "2026-10-06"}},
                          "Item ID": {"rich_text": [{"plain_text": "gh:a"}]},
                          "Grade": {"select": {"name": "GREAT"}}}}
    junk = {"properties": {"Date": {"date": None}, "Item ID": {"rich_text": []}, "Grade": {"select": None}}}
    assert notion.Notion(FakeNotion(rows=[row, junk]), "tok").harvest("db-1", DAY) == {"2026-10-06|gh:a": "great"}


def passing_judge():
    j = StubJudge()
    j.ask = lambda state, qs: {k: 0.9 for k in qs}
    return j


def test_pipeline_delivers_and_merges_notion_grades(cfg):
    import json
    cfg.notion_page = PAGE
    graded = {"properties": {"Date": {"date": {"start": "2026-10-06"}},
                             "Item ID": {"rich_text": [{"plain_text": "gh:z"}]},
                             "Grade": {"select": {"name": "BAD"}}}}
    fake = FakeNotion(existing_db=True, rows=[graded])
    s = pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY, curator=StubCurator(),
                       notion=notion.Notion(fake, "tok"))
    assert s["delivered"] == "notion"
    assert sum(1 for c in fake.calls if c[:2] == ("POST", "/pages")) == 5
    assert json.loads((cfg.state_dir / "grades.json").read_text()) == {"2026-10-06|gh:z": "bad"}


def test_notion_failure_never_blocks_the_edition(cfg):
    cfg.notion_page = PAGE
    s = pipeline.build(cfg, FixtureHttp(), passing_judge(), NOW, DAY,
                       notion=notion.Notion(FakeNotion(existing_db=True, fail_on="/pages"), "tok"))
    assert s["status"] == "ok" and s["delivered"] == "notion failed"
    assert (cfg.edition_dir / "edition_2026-10-07.md").exists()
