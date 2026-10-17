"""Markdown -> PDF export (fpdf2, core fonts) and source-URL extraction. Never raises on odd input."""
from __future__ import annotations

import re

_URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+", re.I)
_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
_REPLACEMENTS = {
    "₹": "Rs ", "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
    "−": "-", "•": "-", "…": "...", " ": " ", "→": "->", "←": "<-", "✓": "v",
    "✔": "v", "×": "x", "​": "", "﻿": "", "≈": "~", "≤": "<=", "≥": ">=",
}


def extract_sources(md: str) -> list[str]:
    """Return unique URLs found in the markdown, in order of first appearance."""
    seen: list[str] = []
    for m in _URL_RE.finditer(md or ""):
        u = m.group(0).rstrip(".,;:!?*_`")
        if u and u not in seen:
            seen.append(u)
    return seen


def _break_long(text: str, width: int = 60) -> str:
    return " ".join(re.sub(rf"(\S{{{width}}})(?=\S)", r"\1 ", w) for w in text.split(" "))


def _clean(text) -> str:
    text = str(text or "")
    for k, v in _REPLACEMENTS.items():
        text = text.replace(k, v)
    text = _LINK_RE.sub(lambda m: f"{m.group(1)} ({m.group(2)})" if m.group(1) != m.group(2) else m.group(2), text)
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", text)
    text = text.replace("`", "")
    text = text.encode("latin-1", "replace").decode("latin-1")
    text = text.replace("\t", "    ")
    text = "".join(c if ord(c) >= 32 else " " for c in text)
    return _break_long(text)


def _is_sep(line: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*", line))


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _table(pdf, rows: list[list[str]]) -> None:
    rows = [r for r in rows if r]
    if not rows:
        return
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(pdf.l_margin)
    try:
        with pdf.table(first_row_as_headings=True, text_align="LEFT", line_height=4.8) as t:
            for r in rows:
                row = t.row()
                for c in r:
                    row.cell(_clean(c) or " ")
        pdf.ln(3)
    except Exception:  # fallback: plain text rows
        pdf.set_x(pdf.l_margin)
        for r in rows:
            pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 5, _clean(" | ".join(r)) or " ",
                           new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)


def _render(md: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    def para(text: str, size=10.5, style="", indent=0.0, h=5.5, gap=1.0):
        pdf.set_font("Helvetica", style, size)
        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - indent, h, _clean(text) or " ",
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(gap)

    lines = (md or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        b = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", raw)
        if not s:
            pdf.ln(2)
        elif m:
            lvl = len(m.group(1))
            size = {1: 20, 2: 15, 3: 12.5}.get(lvl, 11)
            pdf.ln(2 if lvl > 1 else 0)
            para(m.group(2), size, "B", h=size * 0.5 + 2, gap=1.5)
        elif re.fullmatch(r"[-*_]{3,}", s):
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(3)
        elif s.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                if not _is_sep(lines[i]):
                    block.append(_cells(lines[i]))
                i += 1
            i -= 1
            _table(pdf, block)
        elif b:
            depth = len(b.group(1).replace("\t", "  ")) // 2
            bullet = "-" if b.group(2) in ("-", "*", "+") else b.group(2)
            para(f"{bullet} {b.group(3)}", indent=4 + 5 * depth, gap=0.5)
        elif s.startswith(">"):
            para(s.lstrip("> "), style="I", indent=4)
        else:
            para(s)
        i += 1
    return bytes(pdf.output())


def markdown_to_pdf(md: str) -> bytes:
    """Render markdown to PDF bytes. Falls back to plain rendering; never raises."""
    text = md if isinstance(md, str) else ("" if md is None else str(md))
    try:
        return _render(text)
    except Exception:  # noqa: BLE001
        try:
            return _render(re.sub(r"[#*_`|>]", "", text))
        except Exception:  # noqa: BLE001
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, "Report could not be rendered to PDF. Please download the Markdown version.")
            return bytes(pdf.output())
