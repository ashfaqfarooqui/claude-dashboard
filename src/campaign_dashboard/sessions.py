"""Claude Code sessions, read from their logs in ~/.claude/projects/<dir>/<id>.jsonl.

A session's own log gives its directory, title, prompts, cost and timing. Its subagents' logs
(<id>/subagents/agent-<id>.jsonl, with a .meta.json naming the agent) add their tool calls and file
writes. Writes to the plans folder are how loose plans and campaigns are tied back to the sessions
that worked on them. ~/.claude/sessions/<pid>.json lists the processes that are running now.
Claude Code deletes old logs, but ~/.claude/history.jsonl keeps one line for each prompt you typed. A
session that has prompts there and no log is shown from those prompts alone ("prompt-only").
"""

import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from pathlib import Path

WRITE_RE = re.compile(r'"name":"(?:Write|Edit)","input":\{"file_path":"([^"]*/\.claude/plans/[^"]+)"')
CWD_RE = re.compile(r'"cwd":"((?:[^"\\]|\\.)*)"')
COMMAND_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
PROMPT_MAX = 300  # first_prompt, shown in tables
PROMPT_KEEP = 20_000  # each prompt on the session page
FILE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
NEVER = datetime.min.replace(tzinfo=timezone.utc)  # sort key for a log with no timestamps


@dataclass
class ToolStats:
    """Tool calls by name, and how many of each came back as an error, rejected by you, or denied by
    a permission rule or the auto-mode classifier."""
    calls: Counter[str] = field(default_factory=Counter)
    errors: Counter[str] = field(default_factory=Counter)
    rejected: Counter[str] = field(default_factory=Counter)
    denied: Counter[str] = field(default_factory=Counter)
    skills: Counter[str] = field(default_factory=Counter)  # Skill tool calls by skill name
    files: Counter[str] = field(default_factory=Counter)  # paths written by Write/Edit/NotebookEdit

    def add(self, other: "ToolStats") -> None:
        for name in ("calls", "errors", "rejected", "denied", "skills", "files"):
            getattr(self, name).update(getattr(other, name))


@dataclass
class Prompt:
    at: datetime | None
    text: str


@dataclass
class SubAgent:
    id: str
    type: str | None = None
    description: str | None = None
    tools: ToolStats = field(default_factory=ToolStats)


@dataclass
class Session:
    id: str
    path: Path  # the log; for a prompt-only session, the history file
    cwd: str | None = None
    title: str | None = None
    prompt_log: list[Prompt] = field(default_factory=list)
    commands: Counter[str] = field(default_factory=Counter)  # slash commands you typed
    started: datetime | None = None
    ended: datetime | None = None
    branch: str | None = None
    cost: float | None = None
    lines_added: int = 0
    lines_removed: int = 0
    models: list[str] = field(default_factory=list)
    agents: list[SubAgent] = field(default_factory=list)
    tools: ToolStats = field(default_factory=ToolStats)  # this session and its subagents
    prs: list[str] = field(default_factory=list)
    continued_in: str | None = None
    # (cwd of the writing agent, path under the plans folder) for every Write/Edit there
    plan_writes: Counter[tuple[str, str]] = field(default_factory=Counter)
    live: str | None = None  # "busy" / "idle" while a process is running it
    live_name: str | None = None
    prompt_only: bool = False  # the log is deleted; only the prompts in history.jsonl remain

    @property
    def prompts(self) -> int:
        return len(self.prompt_log)

    @property
    def first_prompt(self) -> str | None:
        return self.prompt_log[0].text[:PROMPT_MAX] if self.prompt_log else None

    @property
    def subagents(self) -> int:
        return len(self.agents)

    @property
    def label(self) -> str:
        return self.title or self.first_prompt or self.live_name or self.id[:8]

    def touched(self, prefix: str) -> bool:
        """Did this session write under plans/<prefix> (a campaign folder, or one loose plan file)?"""
        return any(rel == prefix or rel.startswith(prefix + "/") for _, rel in self.plan_writes)


def _ts(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(s).astimezone() if s else None
    except ValueError:
        return None


def _prompt_text(msg: dict) -> str | None:
    """A typed prompt, not a tool result, slash-command echo or injected caveat."""
    c = msg.get("content")
    if isinstance(c, list):
        c = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text") or None
    if not isinstance(c, str) or not c.strip() or c.lstrip().startswith("<"):
        return None
    return c.strip()


def _plan_writes(line: str, plans_marker: str = "/.claude/plans/") -> list[tuple[str, str]]:
    if plans_marker not in line:
        return []
    cwd = CWD_RE.search(line)
    if not cwd:
        return []
    cwd_s = json.loads(f'"{cwd.group(1)}"')
    return [(cwd_s, p.split(plans_marker, 1)[1]) for p in WRITE_RE.findall(line)]


def _result_text(block: dict) -> str:
    c = block.get("content")
    if isinstance(c, list):
        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
    return c if isinstance(c, str) else ""


def _tool_events(d: dict, stats: ToolStats, names: dict[str, str]) -> None:
    """Count tool_use blocks in an assistant line and failed tool_result blocks in a user line.
    `names` maps tool_use ids to tool names so a result can be charged to its tool."""
    content = (d.get("message") or {}).get("content")
    if not isinstance(content, list):
        return
    for b in content:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "tool_use":
            name = b.get("name") or "?"
            names[b.get("id", "")] = name
            stats.calls[name] += 1
            inp = b.get("input") if isinstance(b.get("input"), dict) else {}
            if name == "Skill" and inp.get("skill"):
                stats.skills[inp["skill"]] += 1
            if (key := FILE_TOOLS.get(name)) and isinstance(inp.get(key), str):
                stats.files[inp[key]] += 1
        elif b.get("type") == "tool_result" and b.get("is_error"):
            name = names.get(b.get("tool_use_id", ""), "?")
            text = _result_text(b)
            if "doesn't want to proceed" in text:
                stats.rejected[name] += 1
            elif "denied" in text and "ermission" in text:
                stats.denied[name] += 1
            else:
                stats.errors[name] += 1


def parse_session(log: Path) -> Session:
    s = Session(id=log.stem, path=log)
    models: Counter[str] = Counter()
    names: dict[str, str] = {}
    with log.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            for w in _plan_writes(line):
                s.plan_writes[w] += 1
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = d.get("type")
            ts = _ts(d.get("timestamp"))
            if ts:
                s.started = min(s.started or ts, ts)
                s.ended = max(s.ended or ts, ts)
            if t in ("user", "assistant"):
                s.cwd = s.cwd or d.get("cwd")
                s.branch = d.get("gitBranch") or s.branch
                _tool_events(d, s.tools, names)
            if t == "user" and not d.get("isMeta") and (d.get("origin") or {}).get("kind", "human") == "human":
                msg = d.get("message") or {}
                if text := _prompt_text(msg):
                    s.prompt_log.append(Prompt(ts, text[:PROMPT_KEEP]))
                elif isinstance(msg.get("content"), str):
                    s.commands.update(COMMAND_RE.findall(msg["content"]))
            elif t == "system" and d.get("subtype") == "local_command" and isinstance(d.get("content"), str):
                s.commands.update(COMMAND_RE.findall(d["content"]))
            elif t == "assistant":
                m = (d.get("message") or {}).get("model")
                if m and not m.startswith("<"):
                    models[m] += 1
            elif t == "ai-title":
                s.title = d.get("aiTitle") or s.title
            elif t == "agent-name":
                s.title = d.get("agentName") or s.title
            elif t == "cost-state":  # running totals; the last one wins
                s.cost = d.get("totalCostUSD")
                s.lines_added = d.get("totalLinesAdded") or 0
                s.lines_removed = d.get("totalLinesRemoved") or 0
            elif t == "pr-link" and (url := d.get("prUrl")) and url not in s.prs:
                s.prs.append(url)
            elif t == "continued-in":
                s.continued_in = d.get("continuedInSessionId")
    s.models = [m for m, _ in models.most_common()]
    return s


def parse_subagent(log: Path, plan_writes: Counter[tuple[str, str]]) -> SubAgent:
    """Tool calls and plan writes only; lines with neither are skipped without parsing."""
    a = SubAgent(id=log.stem.removeprefix("agent-"))
    try:
        meta = json.loads(log.with_suffix(".meta.json").read_text(encoding="utf-8"))
        a.type, a.description = meta.get("agentType"), meta.get("description")
    except (OSError, ValueError, AttributeError):
        pass
    names: dict[str, str] = {}
    with log.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            for w in _plan_writes(line):
                plan_writes[w] += 1
            if '"tool_use"' not in line and '"is_error":true' not in line:
                continue
            try:
                _tool_events(json.loads(line), a.tools, names)
            except (json.JSONDecodeError, AttributeError):
                continue
    return a


def load_history(history: Path, skip: set[str]) -> list[Session]:
    """One prompt-only Session for each sessionId in `history` that is not in `skip`.

    Only `display`, `timestamp`, `project` and `sessionId` are read. `pastedContents` can hold pasted
    secrets and is never read."""
    out: dict[str, Session] = {}
    try:
        fh = history.open(encoding="utf-8", errors="replace")
    except OSError:
        return []
    with fh:
        for line in fh:
            try:
                d = json.loads(line)
                sid, text, ms = d["sessionId"], d["display"], d["timestamp"]
                at = datetime.fromtimestamp(ms / 1000, UTC).astimezone()
            except (ValueError, KeyError, TypeError, OverflowError, OSError):
                continue
            if not isinstance(sid, str) or not isinstance(text, str) or sid in skip:
                continue
            s = out.setdefault(sid, Session(id=sid, path=history, prompt_only=True))
            s.cwd = s.cwd or (d.get("project") if isinstance(d.get("project"), str) else None)
            s.started = min(s.started or at, at)
            s.ended = max(s.ended or at, at)
            s.prompt_log.append(Prompt(at, text[:PROMPT_KEEP]))
            if text.startswith("/") and (name := text[1:].split(None, 1)[:1]):
                s.commands[name[0]] += 1
    return list(out.values())


def load_sessions(sessions_dir: Path, live_dir: Path | None = None,
                  cache: dict[Path, tuple[tuple, Session]] | None = None,
                  history: Path | None = None) -> list[Session]:
    """Every <project>/<id>.jsonl under `sessions_dir`, newest first; unreadable logs are skipped.
    With `history`, sessions that have prompts there and no log are added as prompt-only sessions.

    With `cache` (kept by the caller between calls), a log whose files have the same size and mtime as
    last time is not parsed again."""
    out: dict[str, Session] = {}
    for log in sessions_dir.glob("*/*.jsonl") if sessions_dir.is_dir() else ():
        sub = log.parent / log.stem / "subagents"
        slogs = sorted(sub.glob("*.jsonl")) if sub.is_dir() else []
        try:
            sig = tuple((st.st_mtime_ns, st.st_size) for st in map(Path.stat, [log, *slogs]))
        except OSError:
            continue
        if cache is not None and (hit := cache.get(log)) and hit[0] == sig:
            out[hit[1].id] = hit[1]
            continue
        try:
            s = parse_session(log)
        except OSError:
            continue
        for slog in slogs:
            try:
                a = parse_subagent(slog, s.plan_writes)
            except OSError:
                continue
            s.agents.append(a)
            s.tools.add(a.tools)
        out[s.id] = s
        if cache is not None:
            cache[log] = (sig, s)
    if history:
        for s in load_history(history, set(out)):
            out[s.id] = s
    for s in out.values():
        s.live = s.live_name = None
    if live_dir:
        _mark_live(out, live_dir)
    return sorted(out.values(), key=lambda s: s.ended or NEVER, reverse=True)


def _mark_live(sessions: dict[str, Session], live_dir: Path) -> None:
    for f in live_dir.glob("*.json") if live_dir.is_dir() else ():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        s = sessions.get(d.get("sessionId", ""))
        if s is None or not _alive(d.get("pid")):
            continue
        s.live = d.get("status") or "running"
        s.live_name = d.get("name")


def _alive(pid: object) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@dataclass
class UsageRow:
    name: str
    count: int = 0
    sessions: int = 0
    last: datetime | None = None
    errors: int = 0
    rejected: int = 0
    denied: int = 0
    extra: int = 0  # skills: times you typed it as a slash command


def usage(sessions: list[Session]) -> dict[str, list[UsageRow]]:
    """Tool, MCP-server, skill, slash-command and subagent-type tallies across `sessions`,
    each list sorted by count."""
    tables: dict[str, dict[str, UsageRow]] = {k: {} for k in ("tools", "mcp", "skills", "commands", "agents")}

    def bump(table: str, name: str, s: Session, n: int, seen: set[tuple[str, str]], **extra: int) -> None:
        if not n and not any(extra.values()):
            return
        r = tables[table].setdefault(name, UsageRow(name))
        r.count += n
        for k, v in extra.items():
            setattr(r, k, getattr(r, k) + v)
        if (table, name) not in seen:
            seen.add((table, name))
            r.sessions += 1
            if s.ended and (r.last is None or s.ended > r.last):
                r.last = s.ended

    known_skills = {k for s in sessions for k in s.tools.skills}
    for s in sessions:
        seen: set[tuple[str, str]] = set()
        t = s.tools
        for name in t.calls.keys() | t.errors.keys() | t.rejected.keys() | t.denied.keys():
            bump("tools", name, s, t.calls[name], seen,
                 errors=t.errors[name], rejected=t.rejected[name], denied=t.denied[name])
            if name.startswith("mcp__"):
                server = name.split("__")[1]
                bump("mcp", server.removeprefix("claude_ai_").replace("_", " "), s, t.calls[name], seen)
        for name in t.skills.keys() | s.commands.keys():
            if name in known_skills:
                bump("skills", name, s, t.skills[name], seen, extra=s.commands[name])
            else:
                bump("commands", name, s, s.commands[name], seen)
        for a in s.agents:
            bump("agents", a.type or "unknown", s, 1, seen, extra=sum(a.tools.calls.values()))
    return {k: sorted(v.values(), key=lambda r: (-(r.count + r.extra), r.name)) for k, v in tables.items()}
