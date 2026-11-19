"""The state of the Claude Code archive job (`claude-archive`): read only.

The job copies idle transcripts, plans, memory and the prompt history into an encrypted git repo. It
keeps `last-push` (epoch seconds of the last good push) and `manifest` (one line per archived file:
mtime TAB size TAB path without `.zst.age`) in its state folder. This module reads both, the settings
file and the sizes of the repo. It never runs the job, never decrypts and never writes.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

IDLE_DAYS = 2  # the job's default IDLE_DAYS: a transcript is archived when it was idle for this long
STALE_DAYS = 3  # the status line warns when the last push is older than this
RETENTION_DAYS = 3650  # the status line warns when cleanupPeriodDays is anything else
DAY = 86400


def default_state_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "claude-archive"


@dataclass
class Pending:
    rel: str  # projects/<project>/<session>.jsonl, as in the manifest
    mtime: datetime  # the newest file of the session
    size: int  # bytes of the transcript and its session folder


@dataclass
class Archive:
    set_up: bool = False
    last_push: datetime | None = None
    retention_days: int | None = None
    settings_symlink: bool = False
    pending: list[Pending] = field(default_factory=list)
    manifest_files: int = 0
    repo_bytes: int | None = None
    year_bytes: int | None = None  # the repo size after one year at the rate since its first reflog entry
    warnings: list[str] = field(default_factory=list)


def _manifest(path: Path) -> dict[str, tuple[int, int]]:
    out = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return out
    for line in lines:
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            out[parts[2]] = (int(parts[0]), int(parts[1]))
    return out


def _newest_and_total(paths: list[Path]) -> tuple[int, int]:
    """The newest whole-second mtime and the total size of the files, as `newest_and_total` in the job."""
    newest = total = 0
    for top in paths:
        if top.is_dir():
            files = [Path(d) / f for d, _, names in os.walk(top) for f in names]
        else:
            files = [top]
        for f in files:
            try:
                st = f.lstat()
            except OSError:
                continue
            if f.is_symlink() or not f.is_file():
                continue
            newest, total = max(newest, int(st.st_mtime)), total + st.st_size
    return newest, total


def _pending(projects: Path, manifest: dict[str, tuple[int, int]], now: float) -> list[Pending]:
    """The transcripts the job will archive on its next run (step 1 and `should_write` of the job)."""
    out = []
    for log in sorted(projects.glob("*/*.jsonl")):
        if not log.is_file():
            continue
        session = log.with_suffix("")
        members = [log] + ([session] if session.is_dir() else [])
        newest, total = _newest_and_total(members)
        if newest >= now - IDLE_DAYS * DAY or total == 0:
            continue
        rel = f"projects/{log.parent.name}/{log.stem}.jsonl"
        if rel in manifest:
            old_mtime, old_size = manifest[rel]
            if newest <= old_mtime or total < old_size:  # unchanged, or the source got shorter
                continue
        out.append(Pending(rel, datetime.fromtimestamp(newest), total))
    return out


def _dir_bytes(path: Path) -> int | None:
    if not path.is_dir():
        return None
    return sum(f.lstat().st_size for d, _, names in os.walk(path) for n in names
               if (f := Path(d) / n).is_file() and not f.is_symlink())


def _first_reflog_time(git_dir: Path) -> float | None:
    """The time of the first line of `.git/logs/HEAD` (a clone or a first commit). Read as text, no `git`."""
    try:
        first = (git_dir / "logs" / "HEAD").read_text(encoding="utf-8").split("\n", 1)[0]
        return float(first.split("\t", 1)[0].rsplit(" ", 2)[-2])
    except (OSError, ValueError, IndexError):
        return None


def load_archive(claude_dir: Path, state_dir: Path, repo_dir: Path) -> Archive:
    now = time.time()
    a = Archive()
    settings = claude_dir / "settings.json"
    try:
        value = json.loads(settings.read_text(encoding="utf-8")).get("cleanupPeriodDays")
        a.retention_days = value if isinstance(value, int) else None
    except (OSError, ValueError, AttributeError):
        pass
    a.settings_symlink = settings.is_symlink()
    if a.retention_days != RETENTION_DAYS:  # a missing key means Claude Code's default of 30 days
        a.warnings.append(f"retention {30 if a.retention_days is None else a.retention_days}d")
    if not a.settings_symlink:
        a.warnings.append("settings untracked")

    if not state_dir.is_dir():
        return a
    a.set_up = True
    try:
        a.last_push = datetime.fromtimestamp(int((state_dir / "last-push").read_text().strip()))
    except (OSError, ValueError):
        pass
    if a.last_push and (days := int((now - a.last_push.timestamp()) // DAY)) > STALE_DAYS:
        a.warnings.insert(0, f"archive {days}d old")
    manifest = _manifest(state_dir / "manifest")
    a.manifest_files = len(manifest)
    a.pending = _pending(claude_dir / "projects", manifest, now)

    a.repo_bytes = _dir_bytes(repo_dir / ".git")
    since = _first_reflog_time(repo_dir / ".git")
    if a.repo_bytes is not None and since and (now - since) >= DAY:
        a.year_bytes = round(a.repo_bytes / (now - since) * 365 * DAY)
    return a
