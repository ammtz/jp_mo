"""Shared GitHub repository search for gh_stars and gh_popular."""
from urllib.parse import urlencode

from ..models import Candidate
from .text import plain

API = "https://api.github.com"
PAGES = 3
PER_PAGE = 50


def headers(token: str) -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = "Bearer " + token
    return h


def search(http, token: str, query: str, source: str) -> list:
    """Pages 1-3 sorted by stars. Page 1 failing fails the feed; later pages are best effort."""
    out = []
    for page in range(1, PAGES + 1):
        url = f"{API}/search/repositories?" + urlencode(
            {"q": query, "sort": "stars", "order": "desc", "per_page": PER_PAGE, "page": page})
        try:
            items = http.get_json(url, headers(token))["items"]
        except Exception:
            if page == 1:
                raise
            break
        out.extend(to_candidate(r, source) for r in items)
        if len(items) < PER_PAGE:
            break
    return out


def to_candidate(r: dict, source: str) -> Candidate:
    repo = r["full_name"].lower()
    return Candidate(
        id=f"{source}:{repo}",
        source=source,
        title=r["full_name"],
        url=r["html_url"],
        summary=plain(r.get("description")),
        published_at=r["created_at"],
        metric=float(r.get("stargazers_count") or 0),
        repo=repo,
        extra={"language": r.get("language"), "stars": r.get("stargazers_count")},
    )
