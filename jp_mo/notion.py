"""Notion delivery: one database row per news note, graded with a one-tap Grade select.

Plain HTTP against the Notion API (no SDK). The database is created on first use inside the page
the integration is connected to. Grades are read back every build, with no expiry.
"""
import re
from datetime import date, timedelta

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
DB_TITLE = "jp_mo notes"
GRADE_OPTIONS = (("GREAT", "green"), ("GOOD", "blue"), ("BAD", "red"))
HARVEST_DAYS = 60
TEXT_LIMIT = 2000


def page_id(value: str) -> str:
    """Accept a Notion URL or id; return the dashed 32-hex id."""
    hexes = re.findall(r"[0-9a-f]{32}", (value or "").replace("-", "").lower())
    if not hexes:
        raise ValueError("NOTION_PAGE_ID must be a Notion page URL or id")
    h = hexes[-1]
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def text(s: str) -> list:
    return [{"type": "text", "text": {"content": (s or "")[:TEXT_LIMIT]}}]


def plain(rich: list) -> str:
    return "".join(r.get("plain_text") or r.get("text", {}).get("content", "") for r in rich or [])


def select(name: str) -> dict:
    return {"select": {"name": name}} if name and name != "?" else {"select": None}


class Notion:
    def __init__(self, http, token: str):
        self.http, self.token = http, token

    def _call(self, method: str, path: str, body=None):
        headers = {"Authorization": "Bearer " + self.token, "Notion-Version": VERSION}
        return self.http.request(method, API + path, headers, body)[2]

    # --- database -------------------------------------------------------------
    def ensure_db(self, parent: str) -> str:
        cursor = None
        while True:
            q = "?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            res = self._call("GET", f"/blocks/{parent}/children{q}")
            for b in res.get("results", []):
                if b.get("type") == "child_database" and b["child_database"].get("title") == DB_TITLE:
                    return b["id"]
            if not res.get("has_more"):
                break
            cursor = res.get("next_cursor")
        db = self._call("POST", "/databases", {
            "parent": {"type": "page_id", "page_id": parent},
            "title": text(DB_TITLE),
            "properties": {
                "Note": {"title": {}},
                "Grade": {"select": {"options": [{"name": n, "color": c} for n, c in GRADE_OPTIONS]}},
                "Date": {"date": {}},
                "What": {"rich_text": {}},
                "For jp_mo": {"rich_text": {}},
                "Effort": {"select": {"options": [{"name": n} for n in ("S", "M", "L")]}},
                "Effect": {"select": {"options": [{"name": n} for n in ("sellable", "efficient", "simpler")]}},
                "Source": {"select": {}},
                "P": {"number": {"format": "number"}},
                "Link": {"url": {}},
                "Item ID": {"rich_text": {}},
            },
        })
        return db["id"]

    def _query(self, db: str, flt: dict) -> list:
        rows, cursor = [], None
        while True:
            body = {"filter": flt, "page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            res = self._call("POST", f"/databases/{db}/query", body)
            rows += res.get("results", [])
            if not res.get("has_more"):
                return rows
            cursor = res.get("next_cursor")

    def owner(self) -> str | None:
        """The workspace's only person, if there is exactly one (for the morning @mention)."""
        people = [u["id"] for u in self._call("GET", "/users?page_size=100").get("results", []) if u.get("type") == "person"]
        return people[0] if len(people) == 1 else None

    # --- deliver --------------------------------------------------------------
    def push(self, db: str, day: date, items, judgements, notes: dict, sources_label, mention: str | None = None) -> int:
        """Replace the day's ungraded rows with today's notes. Graded rows are never touched."""
        stale = self._query(db, {"and": [{"property": "Date", "date": {"equals": day.isoformat()}},
                                         {"property": "Grade", "select": {"is_empty": True}}]})
        for row in stale:
            self._call("PATCH", f"/pages/{row['id']}", {"archived": True})
        for n, c in enumerate(items):
            note = notes.get(c.id)
            what = note.what if note else (c.summary or c.readme)[:300]
            body = []
            if n == 0 and mention:
                body.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [
                    {"type": "mention", "mention": {"type": "user", "user": {"id": mention}}},
                    {"type": "text", "text": {"content": f" your jp_mo for {day.isoformat()} is ready."}}]}})
            if note:
                body.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": text(note.apply)}})
            self._call("POST", "/pages", {
                "parent": {"database_id": db},
                "properties": {
                    "Note": {"title": text(f"{n + 1}. {c.title}")},
                    "Date": {"date": {"start": day.isoformat()}},
                    "What": {"rich_text": text(what)},
                    "For jp_mo": {"rich_text": text(note.apply if note else "")},
                    "Effort": select(note.effort if note else ""),
                    "Effect": select(note.effect if note else ""),
                    "Source": select(sources_label(c)),
                    "P": {"number": round(judgements[c.id].p, 2)},
                    "Link": {"url": c.url},
                    "Item ID": {"rich_text": text(c.id)},
                },
                "children": body,
            })
        return len(items)

    # --- grades ---------------------------------------------------------------
    def harvest(self, db: str, today: date) -> dict:
        since = (today - timedelta(days=HARVEST_DAYS)).isoformat()
        rows = self._query(db, {"and": [{"property": "Date", "date": {"on_or_after": since}},
                                        {"property": "Grade", "select": {"is_not_empty": True}}]})
        out = {}
        for r in rows:
            p = r["properties"]
            d = (p.get("Date", {}).get("date") or {}).get("start")
            cid = plain(p.get("Item ID", {}).get("rich_text"))
            g = (p.get("Grade", {}).get("select") or {}).get("name", "")
            if d and cid and g.lower() in ("great", "good", "bad"):
                out[f"{d[:10]}|{cid}"] = g.lower()
        return out
