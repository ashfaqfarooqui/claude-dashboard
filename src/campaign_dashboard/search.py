"""Search the prompts and the assistant's text of every session (live mode only).

The text is already in memory: `parse_session` keeps each session's prompts and replies, and the
session cache keeps them between reloads, so a query is one scan over those strings.
"""

from dataclasses import dataclass
from datetime import datetime

from .projects import Project
from .sessions import NEVER, Session

LIMIT = 50
CONTEXT = 150  # characters of text on each side of the match
ROLES = ("user", "assistant")


@dataclass
class Hit:
    at: datetime | None
    role: str
    session: Session
    project: Project
    snippet: str


def snippet(text: str, query: str) -> str:
    """The text around the first case-insensitive match of `query`, on one line."""
    i = text.lower().find(query.lower())
    start, end = max(0, i - CONTEXT), min(len(text), i + len(query) + CONTEXT)
    return ("…" if start else "") + " ".join(text[start:end].split()) + ("…" if end < len(text) else "")


def search(projects: list[Project], query: str, project: str = "", role: str = "") -> list[Hit]:
    """The newest `LIMIT` messages that contain `query`, optionally of one project key and one role."""
    q = query.lower()
    if not q.strip():
        return []
    hits = []
    for p in projects:
        if project and p.key != project:
            continue
        for s in p.sessions:
            for r, messages in (("user", s.prompt_log), ("assistant", s.replies)):
                if role and r != role:
                    continue
                hits += [(m.at, r, s, p, m.text) for m in messages if q in m.text.lower()]
    hits.sort(key=lambda h: h[0] or NEVER, reverse=True)
    return [Hit(at, r, s, p, snippet(text, query)) for at, r, s, p, text in hits[:LIMIT]]
