"""Offline HTTP for --dry-run and tests: serves tests/fixtures by URL pattern."""
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .net import HttpError

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


class FixtureHttp:
    def __init__(self, root: Path = FIXTURES):
        self.root = Path(root)
        self.urls = []

    def _json(self, name):
        return json.loads((self.root / name).read_text())

    def get_json(self, url, headers=None):
        self.urls.append(url)
        u = urlparse(url)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        page = int(q.get("page", 1))
        if "googleapis.com" in u.netloc:
            items = self._json("youtube.json")["items"]
            if q.get("videoCategoryId"):
                items = [v for v in items if v["snippet"]["categoryId"] == q["videoCategoryId"]]
            return {"items": items}
        if u.path.endswith("/search/repositories"):
            name = "gh_popular.json" if q["q"].startswith("stars:") else "gh_stars.json"
            return self._json(name) if page == 1 else {"items": []}
        if "packages.ecosyste.ms" in u.netloc:
            reg = u.path.split("/registries/")[1].split("/")[0]
            return self._json(f"pkg_{reg}.json") if page == 1 else []
        raise HttpError(404, f"no fixture for {url}")

    def get_text(self, url, headers=None):
        self.urls.append(url)
        if url.endswith("/readme"):
            return (self.root / "readme.md").read_text()
        raise HttpError(404, f"no fixture for {url}")

    def post_json(self, url, body, headers=None):
        raise HttpError(0, "dry-run: no network")
