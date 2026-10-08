import re


def plain(text: str | None, limit: int = 500) -> str:
    """Collapse whitespace and cut to `limit` chars."""
    t = re.sub(r"\s+", " ", text or "").strip()
    return t[:limit]


def github_repo(url: str | None) -> str | None:
    """'https://github.com/Owner/Name.git' -> 'owner/name'. None if not GitHub."""
    m = re.search(r"github\.com[/:]([^/\s]+)/([^/#?\s]+)", url or "")
    if not m:
        return None
    name = re.sub(r"\.git$", "", m.group(2))
    return f"{m.group(1)}/{name}".lower()
