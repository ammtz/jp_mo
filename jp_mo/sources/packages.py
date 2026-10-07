"""pkg: packages new to npm/PyPI in the last 30 days (ecosyste.ms), GitHub-linked only."""
from datetime import timedelta
from urllib.parse import urlencode

from ..models import Candidate
from .text import github_repo, plain

API = "https://packages.ecosyste.ms/api/v1/registries/{reg}/packages"
REGISTRIES = ("npmjs.org", "pypi.org")
PAGES = 3
PER_PAGE = 50


def fetch(cfg, http, now):
    since = (now.date() - timedelta(days=30)).isoformat()
    out, failures = [], 0
    for reg in REGISTRIES:
        try:
            out.extend(fetch_registry(http, reg, since))
        except Exception:
            failures += 1
    if failures == len(REGISTRIES):
        raise RuntimeError("all package registries failed")
    return out


def fetch_registry(http, reg, since):
    out = []
    for page in range(1, PAGES + 1):
        url = API.format(reg=reg) + "?" + urlencode(
            {"sort": "downloads", "order": "desc", "per_page": PER_PAGE, "page": page, "created_after": since})
        try:
            items = http.get_json(url)
        except Exception:
            if page == 1:
                raise
            break
        for p in items:
            c = to_candidate(p, reg)
            if c:
                out.append(c)
        if len(items) < PER_PAGE:
            break
    return out


def to_candidate(p: dict, reg: str) -> Candidate | None:
    repo = github_repo(p.get("repository_url"))
    if not repo:
        return None
    return Candidate(
        id=f"pkg:{reg}:{p['name']}",
        source="pkg",
        title=p["name"],
        url=p.get("registry_url") or p.get("homepage") or p["repository_url"],
        summary=plain(p.get("description")),
        published_at=p.get("first_release_published_at") or p.get("created_at"),
        metric=float(p.get("downloads") or 0),
        repo=repo,
        extra={"registry": reg, "downloads_period": p.get("downloads_period")},
    )
