"""Check a MarketPulse Markdown report against the done-checklist.

Usage: python validate_report.py reports/report.md
"""
import re
import sys
from pathlib import Path

SECTIONS = [
    "Key Competitors",
    "What Customers Complain About",
    "Market Gap",
    "Recommended Positioning",
    "30-Day Launch Plan",
    "Sources",
]
MIN_COMPETITORS = 3
# A price is any number (any currency/unit) or the word "free"; the unit is deliberately not checked.
_PRICE = re.compile(r"\d|\bfree\b", re.I)
_URL = re.compile(r"https?://[^\s)>\]]+", re.I)


def _split_sections(md: str) -> dict:
    """Map each known section name to its body text (up to the next heading)."""
    found = {}
    heads = list(re.finditer(r"^#{1,6}\s+(.*?)\s*$", md, re.M))
    for i, h in enumerate(heads):
        title = h.group(1).lower()
        for name in SECTIONS:
            if name.lower() in title and name not in found:
                end = heads[i + 1].start() if i + 1 < len(heads) else len(md)
                found[name] = md[h.end():end]
    return found


def _table_rows(body: str, with_header: bool = False) -> list:
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) or not c for c in cells):
            continue  # separator row
        rows.append(cells)
    return rows if with_header else rows[1:]  # drop header row unless asked


def validate_report(md: str) -> list:
    """Return a list of problems; an empty list means the report passes."""
    if not isinstance(md, str) or not md.strip():
        return ["Report is empty."]
    problems = []
    sections = _split_sections(md)
    for name in SECTIONS:
        if name not in sections:
            problems.append(f"Missing section: {name}")
    if "Key Competitors" in sections:
        all_rows = _table_rows(sections["Key Competitors"], with_header=True)
        header, rows = (all_rows[0], all_rows[1:]) if all_rows else ([], [])
        price_cols = [i for i, h in enumerate(header) if "price" in h.lower()]
        if len(rows) < MIN_COMPETITORS:
            problems.append(
                f"Key Competitors table has {len(rows)} rows; need at least {MIN_COMPETITORS}."
            )
        for r in rows:
            cells = [r[i] for i in price_cols if i < len(r)] if price_cols else r[1:]
            if not _PRICE.search(" ".join(cells)):
                problems.append(f"Competitor '{r[0] if r else '?'}' has no price.")
    if "Sources" in sections and not _URL.search(sections["Sources"]):
        problems.append("Sources section has no http(s) link.")
    return problems


def main(argv: list) -> int:
    if len(argv) != 2:
        print("Usage: python validate_report.py reports/report.md")
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"File not found: {path}")
        return 2
    problems = validate_report(path.read_text(encoding="utf-8"))
    if problems:
        print("FAIL")
        for p in problems:
            print(f"- {p}")
        return 1
    print("OK: report passes the checklist.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
