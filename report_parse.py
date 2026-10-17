"""Parse a MarketPulse Markdown report into structured pieces for the UI (pure, no Streamlit)."""
from __future__ import annotations

import re

import pandas as pd

BASE_COLUMNS = ["Competitor", "Price", "Price Value", "Channel", "Strength", "Weakness"]
_HEAD = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$", re.M)
_NUMBERING = re.compile(r"^\s*(?:\d+|[ivx]+)[.):]\s+", re.I)
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_URL = re.compile(r"https?://[^\s)>\]|]+", re.I)


def strip_code_fence(md) -> str:
    """Remove a wrapping ```markdown ... ``` fence that LLMs often put around a whole document."""
    text = (md or "").strip()
    m = re.match(r"^```[a-zA-Z]*[ \t]*\n(.*?)\n?```$", text, re.DOTALL)
    return m.group(1).strip() + "\n" if m else (md or "")


def _norm_title(t: str) -> str:
    t = re.sub(r"[*_`]", "", t)  # strip emphasis markers
    t = _NUMBERING.sub("", t.strip())
    return " ".join(t.split()).strip(" :")


def parse_sections(md) -> dict[str, str]:
    """Map normalised heading text ('## 1. Key Competitors' -> 'Key Competitors') to its body."""
    if not isinstance(md, str):
        return {}
    heads = list(_HEAD.finditer(md))
    out = {}
    for i, h in enumerate(heads):
        title = _norm_title(h.group(1))
        end = heads[i + 1].start() if i + 1 < len(heads) else len(md)
        if title and title not in out:
            out[title] = md[h.end():end].strip()
    return out


def _price_value(text: str):
    """First number in a price string ('Rs 180 per meal' -> 180.0, '₹1,200/month' -> 1200.0)."""
    m = _NUMBER.search(text or "")
    if not m:
        return None
    try:
        return float(m.group().replace(",", ""))
    except ValueError:
        return None


def _rows(body: str) -> list[list[str]]:
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) or not c for c in cells):
            continue  # separator row
        rows.append(cells)
    return rows


def _find_col(header: list[str], key: str):
    for i, h in enumerate(header):
        if key in h.lower():
            return i
    return None


def parse_competitors(md) -> pd.DataFrame:
    """Key Competitors table -> DataFrame. Empty (with base columns) when absent; never raises."""
    empty = pd.DataFrame(columns=BASE_COLUMNS)
    try:
        sec = next((b for t, b in parse_sections(md).items() if "key competitors" in t.lower()), "")
        rows = _rows(sec)
        if len(rows) < 2:
            return empty
        header, data = rows[0], rows[1:]
        idx = {k: _find_col(header, k.lower()) for k in ("Competitor", "Price", "Channel", "Strength", "Weakness")}
        if idx["Competitor"] is None:
            idx["Competitor"] = 0  # first column is the name by convention
        used = {i for i in idx.values() if i is not None}
        extras = [(i, h) for i, h in enumerate(header) if i not in used and h and h not in BASE_COLUMNS]

        def cell(r, i):
            return r[i] if i is not None and i < len(r) else ""

        recs = []
        for r in data:
            price = cell(r, idx["Price"])
            rec = {"Competitor": cell(r, idx["Competitor"]), "Price": price,
                   "Price Value": _price_value(price), "Channel": cell(r, idx["Channel"]),
                   "Strength": cell(r, idx["Strength"]), "Weakness": cell(r, idx["Weakness"])}
            for i, h in extras:
                rec.setdefault(h, cell(r, i))
            recs.append(rec)
        df = pd.DataFrame(recs, columns=BASE_COLUMNS + list(dict.fromkeys(h for _, h in extras)))
        df["Price Value"] = df["Price Value"].astype(object).where(df["Price Value"].notna(), None)
        return df
    except Exception:  # noqa: BLE001 - UI helper: an odd report must never crash the page
        return empty


def price_chart_data(df):
    """Competitor + Price Value rows with numeric prices, or None if fewer than 2."""
    try:
        if df is None or df.empty or "Price Value" not in df or "Competitor" not in df:
            return None
        vals = pd.to_numeric(df["Price Value"], errors="coerce")
        out = pd.DataFrame({"Competitor": df["Competitor"], "Price Value": vals}).dropna(subset=["Price Value"])
        out = out[out["Competitor"].astype(str).str.strip() != ""].reset_index(drop=True)
        return out if len(out) >= 2 else None
    except Exception:  # noqa: BLE001
        return None


def sources_with_titles(md) -> list[tuple[str, str]]:
    """(label, url) pairs from the Sources section, deduped by URL, in order.

    Label is the link text / text before the URL (list markers stripped), else the URL's host.
    """
    sec = next((b for t, b in parse_sections(md).items() if t.lower() == "sources"), "")
    out, seen = [], set()
    for line in sec.splitlines():
        m = _URL.search(line)
        if not m:
            continue
        url = m.group().rstrip(".,;")
        if url in seen:
            continue
        seen.add(url)
        md_link = re.search(r"\[([^\]]+)\]\(\s*" + re.escape(m.group()), line)
        label = md_link.group(1) if md_link else line[:m.start()]
        label = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*", "", label)
        label = label.strip(" -:[(*_`–—")
        if not label:
            label = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        out.append((label, url))
    return out
