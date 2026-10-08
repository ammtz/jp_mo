"""yt: YouTube mostPopular chart, unfiltered + Science & Technology (category 28)."""
from urllib.parse import urlencode

from ..models import Candidate
from .text import plain

API = "https://www.googleapis.com/youtube/v3/videos"


def fetch(cfg, http, now):
    if not cfg.youtube_key:
        raise RuntimeError("YOUTUBE_API_KEY not set")
    out = []
    for category in (None, "28"):
        q = {"part": "snippet,statistics", "chart": "mostPopular", "regionCode": "US",
             "maxResults": 50, "key": cfg.youtube_key}
        if category:
            q["videoCategoryId"] = category
        try:
            items = http.get_json(API + "?" + urlencode(q))["items"]
        except Exception:
            if category is None:
                raise
            continue  # category call is best effort
        out.extend(to_candidate(v) for v in items)
    return out


def to_candidate(v: dict) -> Candidate:
    s = v["snippet"]
    return Candidate(
        id=f"yt:{v['id']}",
        source="yt",
        title=s["title"],
        url=f"https://www.youtube.com/watch?v={v['id']}",
        summary=plain(s.get("description")),
        published_at=s["publishedAt"],
        metric=float(v.get("statistics", {}).get("viewCount") or 0),
        extra={"channel": s.get("channelTitle"), "category": s.get("categoryId")},
    )
