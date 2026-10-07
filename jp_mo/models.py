from dataclasses import dataclass, field

# Source ids, in title/URL preference order for merges.
SOURCES = ("gh_stars", "gh_popular", "pkg", "yt")

SOURCE_LABELS = {
    "yt": "YouTube",
    "gh_stars": "GitHub new",
    "gh_popular": "GitHub popular",
    "pkg": "Packages",
}

MOMENTUM_UNITS = {
    "yt": "views/day",
    "gh_stars": "stars/day",
    "gh_popular": "stars/day",
    "pkg": "downloads/day",
}


@dataclass
class Candidate:
    id: str                      # "{source}:{native id}"
    source: str
    title: str
    url: str
    summary: str                 # plain text, <= 500 chars
    published_at: str            # ISO 8601
    metric: float                # raw count velocity is computed from
    repo: str | None = None      # lowercase "owner/name"
    readme: str = ""             # cleaned, <= 1,000 chars
    extra: dict = field(default_factory=dict)
    sources: list = field(default_factory=list)
    momentum: float = 0.0        # velocity per day
    momentum_pct: float = 0.0    # percentile within source, 0-1

    def __post_init__(self):
        if not self.sources:
            self.sources = [self.source]


@dataclass
class Judgement:
    p: float | None              # None = judge error
    passes: int = 1              # which pass decided it


@dataclass
class JudgeMeta:
    model: str = ""
    cost_usd: float = 0.0
    input_tokens: int = 0
    requests: int = 0
