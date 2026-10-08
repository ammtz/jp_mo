import pytest

from jp_mo.dryrun import FixtureHttp
from jp_mo.net import HttpError
from jp_mo.sources import github_popular, github_stars, packages, youtube
from jp_mo.sources.text import github_repo, plain
from tests.conftest import NOW


def test_youtube_parses_both_chart_calls(cfg):
    items = youtube.fetch(cfg, FixtureHttp(), NOW)
    assert len(items) == 5                       # 3 unfiltered + 2 from category 28 (deduped later)
    v = items[0]
    assert v.id == "yt:vid001" and v.source == "yt"
    assert v.url == "https://www.youtube.com/watch?v=vid001"
    assert v.metric == 480000 and v.repo is None


def test_youtube_without_key_fails_feed(cfg):
    cfg.youtube_key = ""
    with pytest.raises(RuntimeError):
        youtube.fetch(cfg, FixtureHttp(), NOW)


def test_youtube_category_call_is_best_effort(cfg):
    class Flaky(FixtureHttp):
        def get_json(self, url, headers=None):
            if "videoCategoryId" in url:
                raise HttpError(400, "bad category")
            return super().get_json(url, headers)
    assert len(youtube.fetch(cfg, Flaky(), NOW)) == 3


def test_github_stars_query_and_fields(cfg):
    http = FixtureHttp()
    items = github_stars.fetch(cfg, http, NOW)
    assert "created%3A%3E2026-09-30" in http.urls[0]
    c = items[0]
    assert (c.id, c.repo, c.metric) == ("gh_stars:example/tiny-cron-ui", "example/tiny-cron-ui", 2100)
    assert items[2].summary == ""                # null description


def test_github_popular_query(cfg):
    http = FixtureHttp()
    items = github_popular.fetch(cfg, http, NOW)
    assert "stars%3A%3E5000+pushed%3A%3E2026-10-06" in http.urls[0]
    assert {c.source for c in items} == {"gh_popular"}


def test_github_first_page_failure_fails_feed(cfg):
    class Down(FixtureHttp):
        def get_json(self, url, headers=None):
            raise HttpError(503, "down")
    with pytest.raises(HttpError):
        github_stars.fetch(cfg, Down(), NOW)


def test_packages_github_only_and_both_registries(cfg):
    items = packages.fetch(cfg, FixtureHttp(), NOW)
    names = [c.title for c in items]
    assert "no-github-pkg" not in names
    assert {"tiny-cron-ui", "quote-js-string", "csv-sql"} == set(names)
    q = next(c for c in items if c.title == "quote-js-string")
    assert q.repo == "someone/quote-js-string"   # .git stripped
    assert q.id == "pkg:npmjs.org:quote-js-string"


def test_packages_one_registry_down_is_ok_both_down_fails(cfg):
    class HalfDown(FixtureHttp):
        def get_json(self, url, headers=None):
            if "pypi" in url:
                raise HttpError(503, "down")
            return super().get_json(url, headers)
    assert len(packages.fetch(cfg, HalfDown(), NOW)) == 2

    class Down(FixtureHttp):
        def get_json(self, url, headers=None):
            raise HttpError(503, "down")
    with pytest.raises(RuntimeError):
        packages.fetch(cfg, Down(), NOW)


def test_text_helpers():
    assert plain("  a\n\n b  ", 3) == "a b"
    assert github_repo("git+https://github.com/Owner/Name.git") == "owner/name"
    assert github_repo("https://gitlab.com/a/b") is None


def test_package_without_any_date_is_skipped_not_fatal():
    p = {"name": "x", "repository_url": "https://github.com/o/x", "downloads": 5}
    assert packages.to_candidate(p, "npmjs.org") is None
