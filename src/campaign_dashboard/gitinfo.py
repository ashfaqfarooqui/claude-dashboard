"""Read-only git queries against a campaign's repo. Never writes to the repo."""

import subprocess
from pathlib import Path

from .model import Campaign, GitState


def _git(repo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, timeout=5, check=False
    )


def git_state(c: Campaign) -> GitState:
    st = GitState(path=c.repo)
    if not c.repo:
        st.error = "no repo path recorded in MASTER.md"
        return st
    if not Path(c.repo).is_dir():
        st.error = "repo path does not exist"
        return st
    try:
        top = _git(c.repo, "rev-parse", "--is-inside-work-tree")
        if top.returncode != 0 or top.stdout.strip() != "true":
            st.error = "not a git repository"
            return st
        st.branch = _git(c.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or None
        st.head = _git(c.repo, "rev-parse", "--short", "HEAD").stdout.strip() or None
        st.dirty = len(_git(c.repo, "status", "--porcelain").stdout.splitlines())
        st.last_commit = _git(c.repo, "log", "-1", "--format=%cs").stdout.strip() or None
        if c.commit:
            r = _git(c.repo, "rev-list", "--count", f"{c.commit}..HEAD")
            st.since_start = int(r.stdout) if r.returncode == 0 else None
        recorded = sorted({sha for i in c.issues.values() for sha in i.commits})
        st.missing_commits = [
            sha for sha in recorded if _git(c.repo, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0
        ]
    except subprocess.TimeoutExpired:
        st.error = "git timed out"
    return st
