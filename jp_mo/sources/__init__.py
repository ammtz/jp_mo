"""Feeds. Each module exposes fetch(cfg, http, now) -> list[Candidate] and raises on failure."""
from . import github_popular, github_stars, packages, youtube

FEEDS = {
    "yt": youtube.fetch,
    "gh_stars": github_stars.fetch,
    "gh_popular": github_popular.fetch,
    "pkg": packages.fetch,
}
