"""Fetch a repo README and clean it to <= 1,000 chars of plain text."""
import re
import time
from concurrent.futures import ThreadPoolExecutor

from .sources.github import API, headers

README_P1 = 500
README_P2 = 1000
WORKERS = 8
BUDGET_S = 120      # whole README step; repos not started in time are judged without one


def clean(md: str, limit: int = README_P2) -> str:
    t = md or ""
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"```.*?```", " ", t, flags=re.S)                 # code fences
    t = re.sub(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)", " ", t)     # linked badges
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)                  # images
    t = re.sub(r"<[^>]+>", " ", t)                               # HTML tags
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)               # links -> text
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)          # heading marks
    t = re.sub(r"^\s*\[[^\]]+\]:\s*\S+.*$", " ", t, flags=re.M)  # link refs
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def fetch_one(http, token: str, repo: str) -> str:
    h = headers(token)
    h["Accept"] = "application/vnd.github.raw+json"
    try:
        return clean(http.get_text(f"{API}/repos/{repo}/readme", h))
    except Exception:  # 404, rate limit, network: judge on the description alone
        return ""


def attach(http, token: str, candidates, budget_s: float = BUDGET_S, clock=time.monotonic) -> int:
    """Fill c.readme for every repo-backed candidate within the budget. Returns how many got one."""
    pkg_repos = [c.repo for c in candidates if c.sources == ["pkg"]]
    monorepos = {r for r in pkg_repos if pkg_repos.count(r) > 1}
    todo = [c for c in candidates if c.repo and not (c.sources == ["pkg"] and c.repo in monorepos)]
    deadline = clock() + budget_s

    def job(c):
        return fetch_one(http, token, c.repo) if clock() < deadline else ""

    with ThreadPoolExecutor(WORKERS) as pool:
        for c, text in zip(todo, pool.map(job, todo)):
            c.readme = text
    return sum(1 for c in todo if c.readme)
