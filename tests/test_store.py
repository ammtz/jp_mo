import json
from datetime import date

from jp_mo import pipeline
from jp_mo.dryrun import FixtureHttp
from jp_mo.judge import StubJudge
from jp_mo.state import FileStore, RedisStore, State
from tests.conftest import NOW, cand


class FakeUpstash:
    """In-memory Redis behind Upstash's REST shape: POST [cmd, *args] -> {"result": ...}."""
    def __init__(self):
        self.kv, self.lists, self.calls = {}, {}, []

    def post_json(self, url, body, headers=None):
        assert url == "https://x.upstash.io" and headers["Authorization"] == "Bearer t"
        self.calls.append(body)
        cmd, *args = body
        if cmd == "GET":
            return {"result": self.kv.get(args[0])}
        if cmd == "SET":
            self.kv[args[0]] = args[1]
            return {"result": "OK"}
        if cmd == "RPUSH":
            self.lists.setdefault(args[0], []).append(args[1])
            return {"result": len(self.lists[args[0]])}
        if cmd == "LRANGE":
            items = self.lists.get(args[0], [])
            return {"result": items[args[1]:] if args[2] == -1 else items[args[1]:args[2] + 1]}
        if cmd == "PING":
            return {"result": "PONG"}
        raise AssertionError(cmd)


def redis():
    return RedisStore(FakeUpstash(), "https://x.upstash.io/", "t")


def test_redis_store_roundtrip_and_log():
    s = redis()
    assert s.read("state") is None
    s.write("state", {"level": 1})
    assert s.read("state") == {"level": 1}
    for i in range(70):
        s.append_log({"i": i})
    assert [e["i"] for e in s.recent_log()] == list(range(10, 70))      # last 60
    assert s.http.kv["jp_mo:state"] == '{"level": 1}'


def test_state_works_the_same_on_both_stores(tmp_path):
    day = date(2026, 10, 7)
    for store in (FileStore(tmp_path), redis()):
        st = State(store=store)
        st.core["level"] = -1
        st.mark_seen([cand("gh_stars:o/a", repo="o/a")], day)
        st.save()
        st.append_log({"date": "2026-10-07", "status": "ok"})
        again = State(store=store)
        assert again.core["level"] == -1 and again.was_seen(cand("pkg:r:a", "pkg", repo="o/a"), day)
        assert again.logged_ok(day) and not again.logged_ok(date(2026, 10, 8))


def test_dry_run_never_writes_to_redis():
    store = redis()
    State(store=store, persist=False).save()
    assert not any(c[0] in ("SET", "RPUSH") for c in store.http.calls)


def test_pipeline_runs_on_redis_and_keeps_local_disk_clean(cfg):
    store = redis()
    j = StubJudge()
    j.ask = lambda state, qs: {k: 0.9 for k in qs}
    s = pipeline.build(cfg, FixtureHttp(), j, NOW, date(2026, 10, 7), store=store)
    assert s["status"] == "ok"
    kv = store.http.kv
    assert {"jp_mo:state", "jp_mo:seen", "jp_mo:snapshots", "jp_mo:grades"} <= set(kv)
    assert len(store.http.lists["jp_mo:log"]) == 1 and json.loads(kv["jp_mo:snapshots"])
    assert not cfg.state_dir.exists()
    # same day again: refused, using the log in Redis
    assert pipeline.build(cfg, FixtureHttp(), j, NOW, date(2026, 10, 7), store=store)["status"] == "skipped: already built"
