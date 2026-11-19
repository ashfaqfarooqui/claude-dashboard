"""Plain data parsed out of a campaign folder. Missing data is None / empty, never an error."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

DONE = "☑"
IN_PROGRESS = "◐"
BLOCKED = "⊘"
WONT_FIX = "✗"
READY = "☐"
GLYPHS = (DONE, IN_PROGRESS, BLOCKED, WONT_FIX, READY)
CLOSED = (DONE, WONT_FIX)


@dataclass
class Issue:
    id: str
    status: str | None = None  # one of GLYPHS, None when unknown
    model: str | None = None
    commits: list[str] = field(default_factory=list)
    outcome: str | None = None
    doc: str | None = None  # filename inside the campaign folder
    title: str | None = None
    severity: str | None = None
    depends: str | None = None
    wave: str | None = None


@dataclass
class Wave:
    name: str
    issue_ids: list[str]
    files: dict[str, str]  # issue id -> files held

    def done(self, issues: dict[str, Issue]) -> bool:
        return all(i in issues and issues[i].status in CLOSED for i in self.issue_ids)


@dataclass
class Decision:
    id: str
    subject: str
    text: str
    open: bool


@dataclass
class LogEntry:
    date: date
    text: str
    gate: str | None = None  # usage gate state at the end of the line: go | caution | stop | unknown
    five_hour: int | None = None  # percent; None when the line gives n/a or no value
    seven_day: int | None = None
    over_gate: bool = False  # a dispatch made at `stop`, or at `caution` for an opus issue


# The clarity checklist of campaign:brainstorm: one DESIGN.md section each.
CHECKLIST = ("Problem", "Who and why now", "Success", "Constraints", "Scope", "Approach", "Risks", "Verification")


@dataclass
class Design:
    """DESIGN.md, the brief campaign:brainstorm writes before a campaign is planned."""

    status: str | None = None  # "in progress" | "agreed YYYY-MM-DD"
    verdict: str | None = None  # build | build smaller | don't build | open
    settled: dict[str, bool] = field(default_factory=dict)  # checklist item -> section has real content
    disagreements: int = 0
    decisions: list[Decision] = field(default_factory=list)

    @property
    def agreed(self) -> bool:
        return (self.status or "").lower().startswith("agreed")


@dataclass
class GitState:
    path: str | None
    error: str | None = None
    branch: str | None = None
    head: str | None = None
    dirty: int | None = None
    since_start: int | None = None
    last_commit: str | None = None
    missing_commits: list[str] = field(default_factory=list)


@dataclass
class Campaign:
    slug: str
    path: Path
    prefix: str | None = None
    repo: str | None = None
    commit: str | None = None
    branch: str | None = None
    start_here: dict[str, str] = field(default_factory=dict)  # normalised label -> markdown
    start_here_md: str | None = None
    issues: dict[str, Issue] = field(default_factory=dict)
    waves: list[Wave] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    log: list[LogEntry] = field(default_factory=list)
    findings: dict[str, dict[str, int]] = field(default_factory=dict)  # by_severity / by_verification
    design: Design | None = None
    files: list[str] = field(default_factory=list)
    has_status_table: bool = False
    errors: list[str] = field(default_factory=list)
    git: GitState | None = None
    last_activity: date | None = None

    @property
    def stage(self) -> str | None:
        """Where the folder is in brainstorm → audit → plan: the last step whose file exists."""
        if "MASTER.md" in self.files:
            return "planned"
        if "FINDINGS.md" in self.files:
            return "audited"
        if "DESIGN.md" in self.files:
            return "brainstorm"
        return None

    def counts(self) -> dict[str, int]:
        c = {g: 0 for g in GLYPHS}
        c["unknown"] = 0
        for i in self.issues.values():
            c[i.status or "unknown"] += 1
        return c

    def current_wave(self) -> Wave | None:
        """First wave with an issue still to do; blocked-only waves do not hold the pointer back."""
        active = (IN_PROGRESS, READY, None)
        return next(
            (w for w in self.waves if any(self.issues[i].status in active for i in w.issue_ids if i in self.issues)),
            None,
        )

    def unwaved_issues(self) -> list[Issue]:
        in_waves = {i for w in self.waves for i in w.issue_ids}
        return [i for i in self.issues.values() if i.id not in in_waves]

    def waves_done(self) -> int:
        return sum(w.done(self.issues) for w in self.waves)

    def open_decisions(self) -> list[Decision]:
        return [d for d in self.decisions if d.open]
