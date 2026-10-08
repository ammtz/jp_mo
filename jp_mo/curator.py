"""Agent curator: turns each printed item into a news note about applying it to *this* system.

One chat call per edition. Never blocks an edition: on any failure the notes fall back to the
plain blurb and the footer says so.
"""
import json
import re
from dataclasses import dataclass

from .judge import JudgeError, _Retrying

EFFORTS = ("S", "M", "L")
EFFECTS = ("sellable", "efficient", "simpler")

PROMPT = """You are the curator of a personal morning newsletter. The reader built the system described below and reads this paper to find things to implement in it.

THE SYSTEM
Goal: {goal}

{vision}

Code layout:
{layout}

TODAY'S ITEMS (already filtered as relevant)
{items}

For EACH item, write a short news note about how to apply it to THIS system specifically. Be concrete: name the module, file, or step it would change, and what would change. No hype, no generic advice. If an item would let the system drop code or a dependency, say so.

Reply with only a JSON array, one object per item, in the same order:
[{{"id": "<item id>", "what": "<one sentence: what it is>", "apply": "<2-3 sentences: the concrete change to this system>", "effort": "S|M|L", "effect": "sellable|efficient|simpler"}}]"""


@dataclass
class Note:
    what: str
    apply: str
    effort: str
    effect: str


def system_brief(root) -> tuple[str, str]:
    """VISION.md and the SPEC.md layout block: the curator's picture of the system."""
    vision = (root / "VISION.md").read_text() if (root / "VISION.md").exists() else ""
    spec = (root / "SPEC.md").read_text() if (root / "SPEC.md").exists() else ""
    m = re.search(r"## Layout\s*```\s*(.*?)```", spec, re.S)
    return vision.strip(), (m.group(1).strip() if m else "")


def item_block(c) -> str:
    lines = [f"- id: {c.id}", f"  title: {c.title}", f"  url: {c.url}"]
    if c.summary:
        lines.append(f"  summary: {c.summary}")
    if c.readme:
        lines.append(f"  readme: {c.readme[:1000]}")
    return "\n".join(lines)


def parse(content: str, ids) -> dict:
    """{id: Note} for every well-formed entry; anything malformed is simply missing."""
    m = re.search(r"\[.*\]", content or "", re.S)
    if not m:
        return {}
    try:
        rows = json.loads(m.group(0))
    except ValueError:
        return {}
    out = {}
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict) or r.get("id") not in ids:
            continue
        what, apply = str(r.get("what") or "").strip(), str(r.get("apply") or "").strip()
        if not (what and apply):
            continue
        effort = str(r.get("effort") or "").strip().upper()[:1]
        effect = str(r.get("effect") or "").strip().lower()
        out[r["id"]] = Note(what, apply, effort if effort in EFFORTS else "?", effect if effect in EFFECTS else "?")
    return out


class Curator(_Retrying):
    def write(self, items, goal: str, root) -> dict:
        """Returns {id: Note}. Raises JudgeError only on transport failure."""
        if not items:
            return {}
        vision, layout = system_brief(root)
        prompt = PROMPT.format(goal=goal, vision=vision, layout=layout,
                               items="\n".join(item_block(c) for c in items))
        resp = self._post("/v1/chat/completions", {
            "model": self.cfg.curator_model,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}],
        })
        self._account(resp)
        self.meta.model = self.meta.model or self.cfg.curator_model
        try:
            content = resp["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise JudgeError("curator: no content in response")
        return parse(content, {c.id for c in items})


class StubCurator:
    """Offline curator for --dry-run and tests."""
    def __init__(self, notes: dict | None = None, fail: bool = False):
        self.notes, self.fail = notes, fail
        self.meta = type("Meta", (), {"model": "stub", "cost_usd": 0.0})()

    def write(self, items, goal, root):
        if self.fail:
            raise JudgeError("curator down")
        if self.notes is not None:
            return self.notes
        return {c.id: Note(f"{c.title} in one line.", f"Apply {c.title} to the pipeline.", "S", "simpler")
                for c in items}
