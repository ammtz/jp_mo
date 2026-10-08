"""CLI: python -m jp_mo build [--date YYYY-MM-DD] [--dry-run] [--judge jev|chat] [--force] | check"""
import argparse
import sys
import time
from dataclasses import replace
from datetime import date, datetime, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from . import config, judge as judging, pipeline
from .dryrun import FixtureHttp
from .net import Http
from .sources.github import API as GITHUB_API, headers as github_headers

ET = ZoneInfo("America/New_York")


def make_judge(cfg, name):
    http = Http(timeout=60, retries=0)
    return (judging.JevJudge if name == "jev" else judging.ChatJudge)(cfg, http)


def cmd_build(args) -> int:
    cfg = config.load()
    now = datetime.now(timezone.utc)
    day = date.fromisoformat(args.date) if args.date else now.astimezone(ET).date()
    if args.dry_run:
        cfg = replace(cfg, youtube_key=cfg.youtube_key or "dry-run")
        http, judge = FixtureHttp(), judging.StubJudge()
    else:
        try:
            cfg.require_gateway()
        except config.ConfigError as e:
            print(e, file=sys.stderr)
            return 1
        http, judge = Http(), make_judge(cfg, args.judge or cfg.judge)
    summary = pipeline.build(cfg, http, judge, now, day, dry_run=args.dry_run, force=args.force)
    return 0 if summary["status"] in ("ok", "skipped: already built") else 1


def timed(fn):
    t = time.time()
    try:
        note = fn()
        return "OK", f"{time.time() - t:.1f}s", note or ""
    except Exception as e:
        return "FAIL", f"{time.time() - t:.1f}s", str(e)[:90]


def cmd_check(args) -> int:
    cfg = config.load()
    http = Http(timeout=20, retries=0)
    rows = []

    def gateway():
        cfg.require_gateway()
        j = make_judge(cfg, cfg.judge)
        p = j.ask(judging.state_text(cfg.goal), {"ping": "Does 2 + 2 equal 4? a: yes. b: no."})["ping"]
        if p is None:
            raise RuntimeError("no probability in response")
        return f"{j.meta.model or cfg.judge} answered P={p:.2f}"

    def github():
        status, hdrs, body = http.request("GET", f"{GITHUB_API}/rate_limit", github_headers(cfg.github_token))
        r = body["resources"]
        note = f"search {r['search']['limit']}/min, core {r['core']['limit']}/h"
        exp = {k.lower(): v for k, v in hdrs.items()}.get("github-authentication-token-expiration")
        if exp:
            left = (datetime.strptime(exp[:19], "%Y-%m-%d %H:%M:%S") - datetime.now()).days
            note += f", token expires in {left}d" + (" ⚠ RENEW SOON" if left < 14 else "")
        elif not cfg.github_token:
            note += " (anonymous: READMEs will be rate-limited)"
        return note

    def youtube():
        if not cfg.youtube_key:
            raise RuntimeError("YOUTUBE_API_KEY not set (feed will be skipped)")
        q = urlencode({"part": "id", "chart": "mostPopular", "regionCode": "US", "maxResults": 1, "key": cfg.youtube_key})
        http.get_json("https://www.googleapis.com/youtube/v3/videos?" + q)

    def ecosystems():
        http.get_json("https://packages.ecosyste.ms/api/v1/registries/npmjs.org/packages?per_page=1")

    for name, key, required, fn in [
        ("Vercel AI Gateway (judge)", cfg.gateway_key, True, gateway),
        ("GitHub", cfg.github_token, False, github),
        ("YouTube", cfg.youtube_key, False, youtube),
        ("ecosyste.ms", "n/a", False, ecosystems),
    ]:
        status, latency, note = timed(fn)
        if status == "FAIL" and not required:
            status = "WARN"
        key_state = "n/a" if key == "n/a" else ("set" if key else "empty")
        rows.append((name, key_state, status, latency, note))

    for d in (cfg.state_dir, cfg.edition_dir):
        d.mkdir(parents=True, exist_ok=True)

    widths = [max(len(str(r[i])) for r in rows + [("interface", "key", "status", "time", "note")]) for i in range(5)]
    for r in [("interface", "key", "status", "time", "note")] + rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(r, widths)))
    return 1 if rows[0][2] == "FAIL" else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="jp_mo")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build today's edition")
    b.add_argument("--date", help="edition date (YYYY-MM-DD), default today in ET")
    b.add_argument("--dry-run", action="store_true", help="fixtures + stub judge, no network, no state writes")
    b.add_argument("--judge", choices=["jev", "chat"])
    b.add_argument("--force", action="store_true", help="rebuild a day that already has an edition")
    sub.add_parser("check", help="verify every interface in .env")
    args = p.parse_args(argv)
    return cmd_build(args) if args.cmd == "build" else cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
