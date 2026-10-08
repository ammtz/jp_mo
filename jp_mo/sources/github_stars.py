"""gh_stars: repos created in the last 7 days, by stars (velocity is ranked locally)."""
from datetime import timedelta

from . import github


def fetch(cfg, http, now):
    since = (now.date() - timedelta(days=7)).isoformat()
    return github.search(http, cfg.github_token, f"created:>{since}", "gh_stars")
