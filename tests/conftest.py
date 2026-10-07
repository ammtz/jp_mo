from datetime import datetime, timezone
from pathlib import Path

import pytest

from jp_mo import config
from jp_mo.models import Candidate

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 10, 7, 11, 0, tzinfo=timezone.utc)   # 7:00 AM ET


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / "AGENTS.md").write_text("- `USER_GOAL`: Build small things. (DRAFT, owner to confirm)\n")
    return config.load(tmp_path, environ={
        "AI_GATEWAY_API_KEY": "test-key", "YOUTUBE_API_KEY": "yt-key", "GITHUB_TOKEN": "gh-token"})


def cand(id="gh_stars:a/b", source="gh_stars", metric=100.0, published_at="2026-10-06T11:00:00Z",
         repo=None, readme="", momentum=0.0, pct=0.0, url=None, summary="s"):
    c = Candidate(id=id, source=source, title=id, url=url or f"https://x/{id}", summary=summary,
                  published_at=published_at, metric=metric, repo=repo, readme=readme)
    c.momentum, c.momentum_pct = momentum, pct
    return c
