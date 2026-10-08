import re

import pytest

from jp_mo import judge
from jp_mo.net import HttpError
from tests.conftest import ROOT, cand


class FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
        self.posts = []

    def post_json(self, url, body, headers=None):
        self.posts.append((url, body, headers))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r(body) if callable(r) else r


def jev_answer(body):
    return {"answers": {k: {"type": "boolean", "probability": 0.8} for k in body["questions"]},
            "model": "typesafe-ai/jev", "usage": {"inputTokens": 10},
            "providerMetadata": {"gateway": {"cost": "0.00001"}}}


# --- ladder must match the spec table ----------------------------------------
def test_ladder_matches_filter_rules_md():
    md = (ROOT / "context" / "filter_rules.md").read_text()
    rows = re.findall(r"^\|\s*\**([+-]?\d)\**\s*\|\s*(.+?)\s*\|\s*$", md, re.M)
    assert {int(lvl): text for lvl, text in rows} == judge.LADDER


def test_higher_levels_spell_out_the_full_chain():
    text = judge.instructions(2)
    assert text.startswith(judge.LADDER[0]) and "weekend" in text and "nothing well known" in text
    assert "Same as level" not in text


def test_question_includes_readme_only_when_present():
    c = cand(readme="r" * 900, momentum=1234)
    q = judge.question(0, c, 500)
    assert q.endswith("README (first 500 chars): " + "r" * 500)
    assert "+1,234 stars/day" in q
    assert "README" not in judge.question(0, cand(), 500)


# --- Jev ----------------------------------------------------------------------
def test_jev_request_shape_parsing_and_accounting(cfg):
    http = FakeHttp([jev_answer])
    j = judge.JevJudge(cfg, http, sleep=lambda s: None)
    out = j.ask("state", {"gh:a": "q1", "gh:b": "q2"})
    url, body, headers = http.posts[0]
    assert url == "https://ai-gateway.vercel.sh/v1/evaluate"
    assert headers["Authorization"] == "Bearer test-key"
    assert body["model"] == "typesafe-ai/jev" and body["state"] == "state"
    assert body["questions"]["c0"] == {"type": "boolean", "instructions": "q1"}
    assert out == {"gh:a": 0.8, "gh:b": 0.8}
    assert j.meta.cost_usd == pytest.approx(0.00001) and j.meta.model == "typesafe-ai/jev"


def test_jev_missing_or_bad_probability_is_none(cfg):
    resp = {"answers": {"c0": {"probability": "high"}, "c1": {}}}
    out = judge.JevJudge(cfg, FakeHttp([resp])).ask("s", {"a": "q", "b": "q", "c": "q"})
    assert out == {"a": None, "b": None, "c": None}


def test_jev_batches_of_40(cfg):
    http = FakeHttp([jev_answer, jev_answer, jev_answer])
    out = judge.JevJudge(cfg, http).ask("s", {f"id{i}": "q" for i in range(95)})
    assert [len(b["questions"]) for _, b, _ in http.posts] == [40, 40, 15]
    assert len(out) == 95


def test_jev_retries_429_529_5xx_with_backoff(cfg):
    waits = []
    http = FakeHttp([HttpError(429, ""), HttpError(529, ""), HttpError(503, ""), jev_answer])
    out = judge.JevJudge(cfg, http, sleep=waits.append).ask("s", {"a": "q"})
    assert waits == [1, 4, 16] and out == {"a": 0.8}


def test_jev_gives_up_and_does_not_retry_4xx(cfg):
    http = FakeHttp([HttpError(503, "")] * 4)
    with pytest.raises(judge.JudgeError):
        judge.JevJudge(cfg, http, sleep=lambda s: None).ask("s", {"a": "q"})
    http = FakeHttp([HttpError(401, "bad key")])
    with pytest.raises(judge.JudgeError):
        judge.JevJudge(cfg, http, sleep=lambda s: None).ask("s", {"a": "q"})
    assert len(http.posts) == 1


# --- chat fallback --------------------------------------------------------------
def test_chat_judge_parses_json_reply(cfg):
    reply = {"choices": [{"message": {"content": 'Sure: {"p": 0.82}'}}]}
    http = FakeHttp([reply, {"choices": [{"message": {"content": "no idea"}}]}])
    out = judge.ChatJudge(cfg, http).ask("s", {"a": "q", "b": "q"})
    assert out == {"a": 0.82, "b": None}
    assert http.posts[0][0].endswith("/v1/chat/completions")
    assert http.posts[0][1]["model"] == "moonshotai/kimi-k3"


# --- two-pass routing -------------------------------------------------------------
@pytest.mark.parametrize("p1, readme_len, second", [
    (0.49, 900, False),     # big NO
    (0.50, 900, True),      # close
    (0.749, 900, True),     # close
    (0.75, 900, False),     # already passes
    (0.60, 0, False),       # no README
    (0.60, 400, False),     # README fits in pass 1: nothing new to show
])
def test_two_pass_routing(p1, readme_len, second):
    c = cand("gh:x", readme="r" * readme_len)
    stub = judge.StubJudge({"gh:x": p1})
    _, n = judge.run(stub, [c], 0, "goal")
    assert (n == 1) == second and len(stub.calls) == (2 if second else 1)


def test_pass_two_overrides_pass_one():
    c = cand("gh:x", readme="r" * 900)

    class TwoStep(judge.StubJudge):
        def ask(self, state, questions):
            self.calls.append(questions)
            return {k: (0.6 if len(self.calls) == 1 else 0.3) for k in questions}
    result, _ = judge.run(TwoStep(), [c], 0, "goal")
    assert result["gh:x"].p == 0.3 and result["gh:x"].passes == 2
