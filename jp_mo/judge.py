"""The only place a model is used. Jev via Vercel AI Gateway, or any gateway chat model."""
import hashlib
import json
import re
import time

from .models import MOMENTUM_UNITS, Judgement, JudgeMeta
from .net import HttpError
from .readme import README_P1, README_P2
from .select import THRESHOLD

CLOSE_FLOOR = 0.50
BATCH = 40
BACKOFF = (1, 4, 16)

# Must match the table in context/filter_rules.md (a test enforces it).
LADDER = {
    -2: "Could this item be useful in any way for the reader's newsletter system? a: yes. b: no, it's entertainment or news.",
    -1: "Is there a concrete way to apply this item to the reader's self-improving newsletter system (fetching, filtering, agent curation, writing notes, grading and learning, publishing to readers, running it cheaply, or selling it) that would make the system noticeably more sellable, more efficient, or simpler? a: yes. b: no, it's entertainment, news, too heavy for one person to adopt, or unrelated to the system.",
    0: "Is there a concrete way to apply this item to the reader's self-improving newsletter system (fetching, filtering, agent curation, writing notes, grading and learning, publishing to readers, running it cheaply, or selling it) that would make the system noticeably more sellable, more efficient, or simpler? a: yes. b: no, it's entertainment, news, a well-known general-purpose tool they likely already use, too heavy for one person to adopt, or unrelated to the system.",
    1: 'Same as level 0, plus: the item is new or little-known to the reader, and specific rather than broad.',
    2: 'Same as level +1, plus: the improvement would be large, not incremental.',
}
LEVEL_MIN, LEVEL_MAX = min(LADDER), max(LADDER)


class JudgeError(Exception):
    pass


def instructions(level: int) -> str:
    """Levels +1/+2 build on the lower rungs, so spell the full chain out for the model."""
    if level <= 0:
        return LADDER[level]
    extra = [LADDER[i].split("plus: ", 1)[1].rstrip(".") for i in range(1, level + 1)]
    return f"{LADDER[0]} Also required for a: " + "; and ".join(extra) + "."


STATE = (
    "Reader: a solo engineer building one system: {goal}. It fetches what's rising on GitHub, npm/PyPI and "
    "YouTube; a decision model filters candidates; an agent curator writes each news note; the reader grades "
    "every note GREAT, GOOD or BAD; and the system improves itself from those grades. Stack: small Python "
    "scripts, markdown, AI agents; could become a sellable product. They want \"diamonds in the rough\": items "
    "that could hugely improve this system by making it more sellable, more efficient, or simpler. Removing "
    "complexity counts as much as adding features. Not news or entertainment for its own sake."
)


def state_text(goal: str) -> str:
    g = goal.strip().rstrip(".")
    return STATE.format(goal=g[:1].lower() + g[1:])


def question(level: int, c, n: int) -> str:
    lines = [instructions(level), "", f"Item ({c.source}): {c.title}", c.url]
    if c.summary:
        lines.append(c.summary)
    lines.append(f"Signals: +{c.momentum:,.0f} {MOMENTUM_UNITS[c.source]}")
    if c.readme:
        lines.append(f"README (first {n} chars): {c.readme[:n]}")
    return "\n".join(lines)


def _prob(v):
    return float(v) if isinstance(v, (int, float)) and 0 <= v <= 1 else None


class _Retrying:
    def __init__(self, cfg, http, sleep=time.sleep):
        self.cfg, self.http, self.sleep = cfg, http, sleep
        self.meta = JudgeMeta()

    def _post(self, path, body):
        headers = {"Authorization": "Bearer " + self.cfg.gateway_key}
        for wait in BACKOFF + (None,):
            try:
                self.meta.requests += 1
                return self.http.post_json(self.cfg.gateway_base + path, body, headers)
            except HttpError as e:
                if wait is None or not (e.status in (0, 429, 529) or e.status >= 500):
                    raise JudgeError(str(e)) from e
                self.sleep(wait)

    def _account(self, resp):
        """Jev reports cost in providerMetadata.gateway.cost; chat completions in usage.cost."""
        gw = (resp.get("providerMetadata") or {}).get("gateway") or {}
        usage = resp.get("usage") or {}
        try:
            self.meta.cost_usd += float(gw.get("cost") or usage.get("cost") or 0)
        except (TypeError, ValueError):
            pass
        self.meta.input_tokens += int(usage.get("inputTokens") or usage.get("prompt_tokens") or 0)
        self.meta.model = resp.get("model") or self.meta.model


class JevJudge(_Retrying):
    name = "jev"

    def ask(self, state: str, questions: dict) -> dict:
        ids, out = list(questions), {}
        for start in range(0, len(ids), BATCH):
            chunk = ids[start:start + BATCH]
            keys = {f"c{i}": cid for i, cid in enumerate(chunk)}
            resp = self._post("/v1/evaluate", {
                "model": self.cfg.jev_model,
                "state": state,
                "questions": {k: {"type": "boolean", "instructions": questions[cid]} for k, cid in keys.items()},
            })
            self._account(resp)
            answers = resp.get("answers") or {}
            for k, cid in keys.items():
                out[cid] = _prob((answers.get(k) or {}).get("probability"))
        return out


class ChatJudge(_Retrying):
    name = "chat"
    SYSTEM = ("You judge one item for a reader. Context:\n{state}\n\n"
              "Answer the question with the probability that the answer is a. "
              'Reply with only JSON: {{"p": <number from 0 to 1>}}')

    def ask(self, state: str, questions: dict) -> dict:
        out = {}
        for cid, text in questions.items():
            resp = self._post("/v1/chat/completions", {
                "model": self.cfg.chat_model,
                "temperature": 0,
                "messages": [{"role": "system", "content": self.SYSTEM.format(state=state)},
                             {"role": "user", "content": text}],
            })
            self._account(resp)
            out[cid] = parse_chat(resp)
        self.meta.model = self.meta.model or self.cfg.chat_model
        return out


def parse_chat(resp: dict):
    try:
        content = resp["choices"][0]["message"]["content"]
        m = re.search(r"\{[^{}]*\}", content)
        return _prob(json.loads(m.group(0)).get("p")) if m else None
    except (KeyError, IndexError, TypeError, ValueError):
        return None


class StubJudge:
    """Offline judge for --dry-run and tests. Deterministic per candidate id (or a given map)."""
    name = "stub"

    def __init__(self, probs: dict | None = None):
        self.probs = probs
        self.meta = JudgeMeta(model="stub")
        self.calls = []

    def ask(self, state: str, questions: dict) -> dict:
        self.calls.append(dict(questions))
        self.meta.requests += 1
        if self.probs is not None:
            return {cid: self.probs.get(cid) for cid in questions}
        return {cid: int(hashlib.sha1(cid.encode()).hexdigest()[:4], 16) / 0xFFFF for cid in questions}


def run(judge, candidates, level: int, goal: str):
    """Two passes (filter_rules.md). Returns ({id: Judgement}, second_pass_count)."""
    state = state_text(goal)
    p1 = judge.ask(state, {c.id: question(level, c, README_P1) for c in candidates})
    result = {cid: Judgement(p) for cid, p in p1.items()}

    close = [c for c in candidates
             if len(c.readme) > README_P1
             and p1.get(c.id) is not None and CLOSE_FLOOR <= p1[c.id] < THRESHOLD]
    if close:
        p2 = judge.ask(state, {c.id: question(level, c, README_P2) for c in close})
        for cid, p in p2.items():
            if p is not None:
                result[cid] = Judgement(p, passes=2)
    return result, len(close)
