"""Turn a campaign folder into a Campaign. Each extractor tolerates missing or drifted sections."""

import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from .mdutil import column, find_section, shas, split_sections, tables
from .model import CHECKLIST, GLYPHS, Campaign, Decision, Design, Issue, LogEntry, Wave

ID_RE = re.compile(r"\b([A-Z]{2,4})-(\d{2,3})\b")
ISSUE_FILE_RE = re.compile(r"^([A-Z]{2,4})-\d{2,3}(?:-\d{2,3})*-.+\.md$")
DATE_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
# `- 2026-09-30 — …` (current format) or `**2026-09-22** — …` / `**2026-09-18 — X**` (older campaigns)
LOG_LINE_RE = re.compile(r"^(?:- \*{0,2}|\*\*)(20\d\d-\d\d-\d\d)\*{0,2}\s*[—–-]+\s*(.*)$")
# The usage gate reading that campaign:run ends a Log line with:
# `stop: five_hour: 80% (resets Thu 15:00) · seven_day: 57% (resets Mon 18:00) · snapshot 0 min old`
# Older lines drop the colons, the reset times or the seven_day part.
GATE_RE = re.compile(r"\b(go|caution|stop|unknown): five_hour:? (n/a|\d+)%?[^·\n]*(?:· seven_day:? (n/a|\d+)%?)?")
LABEL_RE = re.compile(r"^\*\*([^*]+?):\*\*", re.M)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
MODELS = ("haiku", "sonnet", "opus", "fable")

# A template slot left unfilled: `<The problem as …>`, `<…>`. Not `<T>` or an HTML tag with attributes.
PLACEHOLDER_RE = re.compile(r"<(?:[^<>\n=\"]*\s[^<>\n=\"]*|…)>")

# START HERE labels vary across campaigns; map them onto the four the overview shows.
LABEL_KEYS = (
    ("status", ("status",)),
    ("next", ("next", "do next")),
    ("hazards", ("live hazards",)),
    ("awaiting", ("awaiting the user", "open for the user")),
)


def parse_campaign(folder: Path) -> Campaign:
    c = Campaign(slug=folder.name, path=folder)
    c.files = sorted(p.name for p in folder.iterdir() if p.is_file())
    issue_files = [f for f in c.files if ISSUE_FILE_RE.match(f)]
    prefixes = Counter(ISSUE_FILE_RE.match(f).group(1) for f in issue_files)
    c.prefix = prefixes.most_common(1)[0][0] if prefixes else None

    if "DESIGN.md" in c.files:
        try:
            c.design = parse_design(c, (folder / "DESIGN.md").read_text(encoding="utf-8"))
        except Exception as e:
            c.errors.append(f"DESIGN.md: {type(e).__name__}: {e}")

    master = folder / "MASTER.md"
    if not master.exists():
        if c.stage is None:  # a brainstorm or an audit has no MASTER.md yet; anything else is broken
            c.errors.append("no MASTER.md")
        elif c.design:
            c.decisions = c.design.decisions
    else:
        try:
            _parse_master(c, master.read_text(encoding="utf-8"))
        except Exception as e:  # one malformed campaign must not stop the others
            c.errors.append(f"MASTER.md: {type(e).__name__}: {e}")

    for f in issue_files:
        try:
            _merge_issue_file(c, f, (folder / f).read_text(encoding="utf-8"))
        except Exception as e:
            c.errors.append(f"{f}: {type(e).__name__}: {e}")

    for issue in c.issues.values():
        if issue.doc not in c.files:  # MASTER can name an issue file that was never written or was renamed
            issue.doc = None

    for e in c.log:
        e.over_gate = _over_gate(e, c.issues)

    if "FINDINGS.md" in c.files:
        c.findings = parse_findings((folder / "FINDINGS.md").read_text(encoding="utf-8"))

    dates = [e.date for e in c.log]
    if not dates:
        dates = [datetime.fromtimestamp((folder / f).stat().st_mtime).date() for f in c.files]
    c.last_activity = max(dates, default=None)
    return c


def _parse_master(c: Campaign, text: str) -> None:
    sections = split_sections(text)
    head = "\n".join(text.splitlines()[:15])
    if m := re.search(r"`(/[^`]+)`", head):
        c.repo = m.group(1).rstrip("/")
    if m := re.search(r"commit `([0-9a-f]{7,40})`", head):
        c.commit = m.group(1)
    if m := re.search(r"branch `([^`]+)`", head):
        c.branch = m.group(1)

    if (body := find_section(sections, "start here")) is not None:
        c.start_here_md = body.strip().strip("-").strip()
        c.start_here = parse_labels(body)

    if (body := find_section(sections, "status")) is not None:
        _parse_status_table(c, body)

    if (body := find_section(sections, "wave plan")) is not None:
        _parse_waves(c, body)

    for heading, body in sections:
        if heading.lower().startswith("decisions"):
            # "## Decisions taken (date)" in older campaigns: every entry under it is settled
            c.decisions = parse_decisions(body, all_settled="taken" in heading.lower())
            break

    c.log = parse_log(text)


def parse_labels(body: str) -> dict[str, str]:
    """`**Label:** text` paragraphs → {normalised key: markdown}. Unrecognised labels keep their own name."""
    out: dict[str, str] = {}
    matches = list(LABEL_RE.finditer(body))
    for m, nxt in zip(matches, matches[1:] + [None]):
        end = nxt.start() if nxt else len(body)
        label = m.group(1).strip()
        content = body[m.end() : end].strip().rstrip("-").strip()
        key = next(
            (k for k, starts in LABEL_KEYS if any(label.lower().startswith(s) for s in starts)),
            label,
        )
        if key == "status" and (d := DATE_RE.search(label)):
            content = f"*{d.group(1)}* — {content}"
        out.setdefault(key, content)
    return out


def _parse_status_table(c: Campaign, body: str) -> None:
    for header, rows in tables(body):
        id_col = column(header, "id")
        if id_col is None:
            continue
        st_col = column(header, "status")
        model_col = column(header, "model", "agent")
        commit_col = column(header, "commit")
        for row in rows:
            if id_col >= len(row) or not (m := ID_RE.search(row[id_col])):
                continue
            issue = c.issues.setdefault(m.group(0), Issue(id=m.group(0)))
            c.has_status_table = True
            if st_col is not None and st_col < len(row):
                issue.status = next((g for g in GLYPHS if row[st_col].startswith(g)), None)
            if model_col is not None and model_col < len(row):
                issue.model = next((mo for mo in MODELS if mo in row[model_col].lower()), None) or (
                    row[model_col] or None
                )
            rest = " ".join(row[commit_col:] if commit_col is not None else row[id_col + 1 :])
            issue.commits = shas(rest.split("[doc]")[0])
            if link := re.search(r"\[doc\]\(([^)]+)\)", " ".join(row)) or LINK_RE.search(row[id_col]):
                issue.doc = link.group(1)
            last = row[-1]
            outcome = re.sub(r"\s*·?\s*\[doc\]\([^)]*\)\s*$", "", last).strip()
            if commit_col is not None and len(row) > commit_col + 1 and not outcome:
                outcome = re.sub(r"^`?[0-9a-f]{7,40}`?\s*[—–-]?\s*", "", row[commit_col]).strip()
            issue.outcome = outcome or None


def _parse_waves(c: Campaign, body: str) -> None:
    for heading, wbody in split_sections(body, level=3)[1:]:
        if not heading.lower().startswith("wave"):
            continue
        wave = Wave(name=heading, issue_ids=[], files={})
        for header, rows in tables(wbody):
            id_col = column(header, "id")
            title_col = column(header, "title")
            sev_col = column(header, "sev")
            files_col = column(header, "files")
            if id_col is None:
                continue
            for row in rows:
                if id_col >= len(row) or not (m := ID_RE.search(row[id_col])):
                    continue
                iid = m.group(0)
                wave.issue_ids.append(iid)
                issue = c.issues.setdefault(iid, Issue(id=iid))
                issue.wave = heading
                if title_col is not None and title_col < len(row) and not issue.title:
                    issue.title = row[title_col] or None
                if sev_col is not None and sev_col < len(row) and not issue.severity:
                    issue.severity = row[sev_col].strip("*") or None
                if files_col is not None and files_col < len(row):
                    wave.files[iid] = row[files_col]
                if not issue.doc and (link := LINK_RE.search(row[id_col])):
                    issue.doc = link.group(1)
        c.waves.append(wave)


def parse_decisions(body: str, all_settled: bool = False) -> list[Decision]:
    """Top-level `- **D<n> …**` bullets, each running until the next top-level bullet or heading."""
    out = []
    # current: `- **D1 / X — q.**`; older: `**D1 — q.**` paragraphs or `1. **D1 / X — …**` lists
    start = r"^(?:- |\d+\. )?\*\*D\d+"
    for block in re.split(rf"(?={start})", body, flags=re.M):
        m = re.match(r"(?:- |\d+\. )?\*\*(D\d+)\b(.*?)\*\*", block, re.S)
        if not m:
            continue
        text = re.split(r"\n(?=#|---)", block, maxsplit=1)[0].rstrip()
        subject = m.group(2).strip(" /—-.")
        settled = r"\b(resolved|settled|superseded|withdrawn|answered|delegated|decided)\b"
        is_open = not all_settled and not re.search(settled, block, re.I)
        out.append(Decision(id=m.group(1), subject=subject, text=text, open=is_open))
    return out


def parse_log(text: str) -> list[LogEntry]:
    """Every `- YYYY-MM-DD — …` line anywhere in the file, newest first."""
    out = []
    for line in text.splitlines():
        if m := LOG_LINE_RE.match(line.strip()):
            entry = LogEntry(date=date.fromisoformat(m.group(1)), text=m.group(2).strip())
            if g := list(GATE_RE.finditer(entry.text)):  # the reading is at the end; take the last one
                state, five, seven = g[-1].groups()
                entry.gate = state
                entry.five_hour = int(five) if five and five.isdigit() else None
                entry.seven_day = int(seven) if seven and seven.isdigit() else None
            out.append(entry)
    out.sort(key=lambda e: e.date, reverse=True)  # stable: same-day lines keep file order
    return out


def _over_gate(e: LogEntry, issues: dict[str, Issue]) -> bool:
    """A dispatch line is over the gate at `stop`, or at `caution` when an issue it names is opus."""
    if not re.search(r"\bdispatched\b", e.text, re.IGNORECASE):
        return False
    if e.gate == "stop":
        return True
    named = {m.group(0) for m in ID_RE.finditer(e.text)}
    return e.gate == "caution" and any(issues[i].model == "opus" for i in named if i in issues)


def _merge_issue_file(c: Campaign, fname: str, text: str) -> None:
    iid = ID_RE.match(fname).group(0)
    issue = c.issues.setdefault(iid, Issue(id=iid))
    issue.doc = issue.doc or fname
    fields = parse_issue_header(text)
    if not issue.title and (m := re.match(r"#\s+\S+\s+[—–-]\s+(.+)", text)):
        issue.title = m.group(1).strip()
    issue.severity = issue.severity or fields.get("severity")
    issue.model = issue.model or fields.get("model")
    issue.depends = fields.get("depends on")
    if issue.status is None and "status" in fields:
        issue.status = next((g for g in GLYPHS if g in fields["status"]), None)


def parse_issue_header(text: str) -> dict[str, str]:
    """`**Field:** value` pairs from the lines between the title and the first `##` section."""
    head = text.split("\n## ", 1)[0]
    out = {}
    for m in re.finditer(r"\*\*([A-Za-z ]+):\*\*\s*(.+?)(?=\s*·\s*\*\*|\s*\*\*[A-Za-z ]+:\*\*|\n\n|$)", head, re.S):
        out[m.group(1).strip().lower()] = " ".join(m.group(2).split()).strip(" ·")
    return out


def parse_findings(text: str) -> dict[str, dict[str, int]]:
    sev: Counter[str] = Counter()
    ver: Counter[str] = Counter()
    for m in re.finditer(r"^### F\d+\s*\(([^)]*)\).*?(?:\*([^*\n]+)\*\s*)?$", text, re.M):
        sev[m.group(1).strip() or "—"] += 1
        v = (m.group(2) or "unstated").strip().rstrip(".").lower()
        ver["running" if "running" in v else "source" if "source" in v else "unverified" if "unverified" in v or "inspection" in v else "unstated"] += 1
    return {"by_severity": dict(sev), "by_verification": dict(ver)} if sev else {}


def parse_design(c: Campaign, text: str) -> Design:
    """DESIGN.md header fields and checklist coverage. The repo it names places the folder in a project
    until MASTER.md exists, which overrides it."""
    header = parse_issue_header(text)
    d = Design(**{k: v for k in ("status", "verdict") if (v := header.get(k)) and not PLACEHOLDER_RE.search(v)})
    if m := re.search(r"`(/[^`]+)`", header.get("repo", "")):
        c.repo = m.group(1).rstrip("/")
    if m := re.search(r"commit `([0-9a-f]{7,40})`", header.get("repo", "")):
        c.commit = m.group(1)
    if m := re.search(r"branch `([^`]+)`", header.get("repo", "")):
        c.branch = m.group(1)
    sections = split_sections(text)
    for item in CHECKLIST:
        body = find_section(sections, item)
        d.settled[item] = body is not None and _filled(body)
    if (body := find_section(sections, "disagreements")) is not None:
        d.disagreements = sum(1 for line in _strip_template(body).splitlines() if re.match(r"- \*\*.*\w", line))
    if (body := find_section(sections, "decisions")) is not None:
        d.decisions = parse_decisions(_strip_template(body))
    return d


def _strip_template(body: str) -> str:
    """Drop HTML comments and lines still holding a template slot."""
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    return "\n".join(line for line in body.splitlines() if not PLACEHOLDER_RE.search(line))


def _filled(body: str) -> bool:
    """A section counts as settled when something other than template slots, labels and table rules is
    written in it, and it does not say TBD."""
    lines = body.splitlines()
    # a table's header row is template text; only its data rows can settle the section
    lines = [ln for ln, nxt in zip(lines, lines[1:] + [""]) if not re.match(r"\s*\|[\s:|-]+\|\s*$", nxt)]
    rest = PLACEHOLDER_RE.sub("", re.sub(r"<!--.*?-->", "", "\n".join(lines), flags=re.S))
    rest = re.sub(r"\*\*[^*]+:\*\*|[|:\-*#>]", " ", rest)
    return bool(re.search(r"\w{3,}", rest)) and not re.search(r"\bTBD\b", rest)
