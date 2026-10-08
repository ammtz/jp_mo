"""Edition markdown. Never includes the owner's name."""
from datetime import date

from .models import MOMENTUM_UNITS, SOURCE_LABELS

SUMMARY_CHARS = 200


def short(text: str, limit: int = SUMMARY_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def footer(stats: dict) -> str:
    parts = [
        f"scanned {stats['scanned']}",
        f"2nd-pass {stats['second_pass']}",
        f"passed {stats['passed']}",
        f"level {stats['level']}",
        "feeds failed: " + (", ".join(stats["feeds_failed"]) or "none"),
        f"judge {stats['judge_model']}",
        f"cost ${stats['cost_usd']:.4f}",
    ]
    if stats.get("errors"):
        parts.append(f"judge errors {stats['errors']}")
    if stats.get("recalibrate"):
        parts.append("recalibrate: question")
    return " · ".join(parts)


def header(day: date) -> str:
    return f"# jp_mo · {day:%a} {day.isoformat()}"


def edition(day: date, items, judgements, stats: dict) -> str:
    out = [header(day), ""]
    if len(items) < 4:
        out += [f"_Only {len(items)} item(s) cleared the filter today._", ""]
    for i, c in enumerate(items, 1):
        sources = " + ".join(SOURCE_LABELS[s] for s in c.sources)
        blurb = short(c.summary or c.readme)
        out += [
            f"## {i}. {c.title}",
            f"{sources} · +{c.momentum:,.0f} {MOMENTUM_UNITS[c.source]} · P {judgements[c.id].p:.2f}",
            c.url,
        ]
        if blurb:
            out.append(blurb)
        out.append("")
    out += ["---", footer(stats), ""]
    return "\n".join(out)


def no_edition(day: date, reason: str, feeds_failed) -> str:
    return "\n".join([
        header(day), "",
        f"No edition today: {reason}.", "",
        "---", "feeds failed: " + (", ".join(feeds_failed) or "none"), "",
    ])
