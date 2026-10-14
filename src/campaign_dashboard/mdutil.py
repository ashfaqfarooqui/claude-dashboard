"""Small helpers for the markdown shapes the campaign files use: sections, tables, SHAs."""

import re

_HEX = re.compile(r"\b[0-9a-f]{7,40}\b")


def split_sections(text: str, level: int = 2) -> list[tuple[str, str]]:
    """Split on headings of exactly `level`; returns (heading, body). Text before the first is ('', body)."""
    marker = re.compile(rf"^{'#' * level} (.+)$", re.M)
    out: list[tuple[str, str]] = []
    pos, heading = 0, ""
    for m in marker.finditer(text):
        out.append((heading, text[pos : m.start()]))
        heading, pos = m.group(1).strip(), m.end()
    out.append((heading, text[pos:]))
    return out


def find_section(sections: list[tuple[str, str]], *prefixes: str) -> str | None:
    """Body of the first section whose heading (minus a leading ▶) starts with any prefix, case-insensitive."""
    for heading, body in sections:
        h = heading.lstrip("▶ ").lower()
        if any(h.startswith(p.lower()) for p in prefixes):
            return body
    return None


def split_row(line: str) -> list[str]:
    """Split a `| a | b |` row on pipes that are not inside backticks or escaped."""
    cells, cur, in_code = [], [], False
    s = line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    prev = ""
    for ch in s:
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code and prev != "\\":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        prev = ch
    cells.append("".join(cur).strip())
    return cells


def tables(text: str) -> list[tuple[list[str], list[list[str]]]]:
    """Every pipe table in `text` as (header cells, body rows). Rows may be shorter or longer than the header."""
    out = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            header = split_row(lines[i])
            rows = []
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            out.append((header, rows))
        elif lines[i].lstrip().startswith("|") and out:
            # rows split off by a blank line: keep them under the previous table's header
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            out.append((out[-1][0], rows))
        else:
            i += 1
    return out


def column(header: list[str], *names: str) -> int | None:
    """Index of the first header cell starting with any of `names`, case-insensitive."""
    for idx, h in enumerate(header):
        if any(h.lower().startswith(n.lower()) for n in names):
            return idx
    return None


def shas(text: str) -> list[str]:
    """Hex tokens that look like commit ids (7–40 chars, at least one digit)."""
    return [m for m in _HEX.findall(text) if any(c.isdigit() for c in m)]
