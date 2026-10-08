"""gh_popular: established repos (more than 5k stars) pushed in the last day."""
from datetime import timedelta

from . import github


def fetch(cfg, http, now):
    since = (now.date() - timedelta(days=1)).isoformat()
    return github.search(http, cfg.github_token, f"stars:>5000 pushed:>{since}", "gh_popular")
