"""Loose plan files (~/.claude/plans/*.md) and grouping of campaigns + plans into projects.

A loose plan names no project, so it is placed by the Claude Code session that wrote it: the
session logs record each Write/Edit tool call with its file path, and each line carries the
session's `cwd` (see sessions.py). Mentions alone are not used — any session that lists the plans
folder mentions every plan. Sessions themselves land in the project their cwd is inside.
"""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .model import Campaign
from .sessions import Session


@dataclass
class LoosePlan:
    name: str  # filename
    path: Path
    title: str
    modified: date
    project: str | None = None  # project dir it belongs to
    writers: Counter[str] = field(default_factory=Counter)  # cwd -> write/edit calls


@dataclass
class Project:
    dir: str
    label: str = ""
    key: str = ""  # page slug
    campaigns: list[Campaign] = field(default_factory=list)
    plans: list[LoosePlan] = field(default_factory=list)
    sessions: list[Session] = field(default_factory=list)

    @property
    def last_activity(self) -> date | None:
        dates = ([c.last_activity for c in self.campaigns if c.last_activity] + [p.modified for p in self.plans]
                 + [s.ended.date() for s in self.sessions if s.ended])
        return max(dates, default=None)

    @property
    def cost(self) -> float:
        return sum(s.cost or 0 for s in self.sessions)


def load_loose_plans(plans_dir: Path) -> list[LoosePlan]:
    out = []
    for p in sorted(plans_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^# (.+)$", text, re.M)
        out.append(LoosePlan(
            name=p.name, path=p, title=(m.group(1).strip() if m else p.stem),
            modified=datetime.fromtimestamp(p.stat().st_mtime).date(),
        ))
    return out


def attribute_plans(plans: list[LoosePlan], sessions: list[Session]) -> None:
    """Fill each plan's `writers` from the sessions' plan writes and pick the cwd with the most."""
    by_name = {p.name: p for p in plans}
    for s in sessions:
        for (cwd, rel), n in s.plan_writes.items():
            if plan := by_name.get(rel):
                plan.writers[cwd] += n
    for p in plans:
        if p.writers:
            p.project = p.writers.most_common(1)[0][0]


def group(campaigns: list[Campaign], plans: list[LoosePlan],
          sessions: list[Session] = ()) -> tuple[list[Project], Project]:
    """Projects keyed by directory; a directory inside another project's directory rolls up into it.

    Returns (projects sorted by last activity, the unassigned bucket).
    """
    dirs = {c.repo.rstrip("/") for c in campaigns if c.repo} | {p.project.rstrip("/") for p in plans if p.project}
    roots = sorted(d for d in dirs if not any(d != o and d.startswith(o + "/") for o in dirs))

    def root_of(d: str | None) -> str | None:
        if not d:
            return None
        d = d.rstrip("/")
        return next((r for r in roots if d == r or d.startswith(r + "/")), None)

    projects: dict[str, Project] = {r: Project(dir=r) for r in roots}
    unassigned = Project(dir="", label="Unassigned", key="unassigned")
    for c in campaigns:
        (projects.get(root_of(c.repo)) or unassigned).campaigns.append(c)
    for p in plans:
        (projects.get(root_of(p.project)) or unassigned).plans.append(p)
    for s in sessions:  # already newest first
        (projects.get(root_of(s.cwd)) or unassigned).sessions.append(s)

    _label(list(projects.values()))
    ordered = sorted(projects.values(), key=lambda p: p.last_activity or date.min, reverse=True)
    for p in [*ordered, unassigned]:
        p.campaigns.sort(key=lambda c: c.last_activity or date.min, reverse=True)
        p.plans.sort(key=lambda pl: pl.modified, reverse=True)
    return ordered, unassigned


def _label(projects: list[Project]) -> None:
    """Shortest trailing path that is unique across projects (`main` is not; `OpenScenario-rs/main` is)."""
    parts = {p.dir: Path(p.dir).parts for p in projects}
    for p in projects:
        n = 1
        while n < len(parts[p.dir]) and sum(parts[o.dir][-n:] == parts[p.dir][-n:] for o in projects) > 1:
            n += 1
        p.label = "/".join(parts[p.dir][-n:])
    used: defaultdict[str, int] = defaultdict(int)
    for p in projects:
        base = re.sub(r"[^a-z0-9]+", "-", p.label.lower()).strip("-") or "project"
        used[base] += 1
        p.key = base if used[base] == 1 else f"{base}-{used[base]}"
