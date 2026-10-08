"""Owner grades live in the edition files themselves: tick one box on each note's grade line.

    Grade: [x] great [ ] good [ ] bad
    <!-- id: gh_stars:owner/name -->

`harvest` reads every edition in EDITION_DIR into state/grades.json ({"date|id": grade}), so the
files stay the source of truth and grading works from any text editor or synced folder.
"""
import json
import re
from datetime import date
from pathlib import Path

GRADES = ("great", "good", "bad")
GRADE_LINE = "Grade: [ ] great [ ] good [ ] bad"
LOOP_MIN_NEW = 20   # skills/calibrate_filter.md: weekly loop needs this many new grades

_ID = re.compile(r"<!-- id: (.+?) -->")
_EDITION = re.compile(r"edition_(\d{4}-\d{2}-\d{2})\.md$")


def parse_line(line: str) -> str | None:
    ticked = re.findall(r"\[[xX]\]\s*(great|good|bad)", line, re.I)
    return ticked[0].lower() if len(ticked) == 1 else None


def parse_edition(text: str) -> list:
    """[(item id, grade or None)] in note order."""
    out, pending = [], None
    for line in text.splitlines():
        if line.startswith("Grade:"):
            pending = parse_line(line)
            continue
        m = _ID.search(line)
        if m:
            out.append((m.group(1), pending))
            pending = None
    return out


def harvest(edition_dir: Path) -> dict:
    grades = {}
    for f in sorted(Path(edition_dir).glob("edition_*.md")):
        m = _EDITION.search(f.name)
        if not m:
            continue
        for cid, g in parse_edition(f.read_text()):
            if g:
                grades[f"{m.group(1)}|{cid}"] = g
    return grades


def save(state_dir: Path, grades: dict):
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "grades.json").write_text(json.dumps(grades, indent=1, sort_keys=True))


def count_since(grades: dict, since: date | None) -> int:
    return sum(1 for k in grades if since is None or date.fromisoformat(k.split("|", 1)[0]) > since)


def set_grades(path: Path, marks: dict) -> list:
    """Tick boxes in an edition file. marks = {note number (1-based): grade}. Returns what changed."""
    lines = path.read_text().splitlines()
    grade_rows = [i for i, l in enumerate(lines) if l.startswith("Grade:")]
    done = []
    for n, g in marks.items():
        if g not in GRADES:
            raise ValueError(f"grade must be one of {GRADES}, got '{g}'")
        if not 1 <= n <= len(grade_rows):
            raise ValueError(f"note {n} doesn't exist (this edition has {len(grade_rows)})")
        lines[grade_rows[n - 1]] = GRADE_LINE.replace(f"[ ] {g}", f"[x] {g}")
        done.append((n, g))
    path.write_text("\n".join(lines) + "\n")
    return done
