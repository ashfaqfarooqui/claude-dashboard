"""campaign-dashboard: render ~/.claude/plans/<slug>/ campaign folders as an HTML site, written once or served live."""

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote

from .archive import default_state_dir, load_archive
from .gitinfo import git_state
from .model import Campaign
from .parse import parse_campaign
from .projects import attribute_plans, group, load_loose_plans
from .render import Renderer
from .server import Site, serve
from .sessions import load_sessions
from .skills import in_place_roots, load_skills


GIT_FILES = ("HEAD", "index", "logs/HEAD")  # change on commit, checkout and staging


def _git_sig(repo: str | None) -> tuple:
    out = []
    for name in GIT_FILES:
        try:
            st = (Path(repo) / ".git" / name).stat()
            out.append((st.st_mtime_ns, st.st_size))
        except (OSError, TypeError):
            out.append(None)
    return tuple(out)


def load(plans_dir: Path, with_git: bool, git_cache: dict | None = None) -> list[Campaign]:
    """With `git_cache`, a repo's git state is queried again only when its HEAD, index or reflog changed."""
    campaigns = []
    for folder in sorted(p for p in plans_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        c = parse_campaign(folder)
        if with_git:
            key = (c.slug, c.repo, c.commit, tuple(sorted(sha for i in c.issues.values() for sha in i.commits)))
            sig = _git_sig(c.repo)
            if git_cache is not None and (hit := git_cache.get(key)) and hit[0] == sig:
                c.git = hit[1]
            else:
                c.git = git_state(c)
                if git_cache is not None:
                    git_cache[key] = (sig, c.git)
        campaigns.append(c)
    return campaigns


def build_site(args, session_cache: dict | None = None, git_cache: dict | None = None) -> Renderer:
    campaigns = load(args.plans_dir, with_git=not args.no_git, git_cache=git_cache)
    plans = load_loose_plans(args.plans_dir)
    sessions = load_sessions(args.sessions_dir, args.live_dir, cache=session_cache, history=args.history)
    attribute_plans(plans, sessions)
    projects, unassigned = group(campaigns, plans, sessions)
    skills = load_skills(args.claude_dir, [p.dir for p in projects])
    r = Renderer(args.plans_dir, date.today(), live=args.serve)
    archive = load_archive(args.claude_dir, args.archive_state, args.archive_repo)
    r.register(projects, unassigned, skills, archive)
    r.summary = (f"{len(projects)} projects, {len(campaigns)} campaigns, {len(plans)} plans "
                 f"({len(unassigned.plans)} unassigned), {len(sessions)} sessions, "
                 f"{len(skills)} skills and commands")
    for c in campaigns:
        for e in c.errors:
            print(f"  {c.slug}: {e}", file=sys.stderr)
    return r


def watched(args) -> list[tuple[Path, str]]:
    """The inputs the live server stats each poll. Campaign repos' git files are added per campaign."""
    roots = [(args.plans_dir, "**/*"), (args.sessions_dir, "*/*.jsonl"), (args.sessions_dir, "*/*/subagents/*.jsonl"),
             (args.live_dir, "*.json"), (args.history, ""), (args.claude_dir / "skills", "**/*"), (args.claude_dir / "commands", "*.md"),
             (args.claude_dir / "plugins" / "installed_plugins.json", ""), (args.claude_dir / "settings.json", ""),
             (args.archive_state / "last-push", ""), (args.archive_state / "manifest", "")]
    roots += [(root / "skills", "**/*") for root in in_place_roots(args.claude_dir).values()]
    if not args.no_git:
        repos = {c.repo for c in load(args.plans_dir, with_git=False) if c.repo}
        roots += [(Path(r) / ".git" / name, "") for r in sorted(repos) for name in GIT_FILES]
    return roots


def broken_links(out: Path) -> list[str]:
    """Relative hrefs in generated pages that do not resolve to a generated file."""
    bad = []
    for page in out.rglob("*.html"):
        for tag in re.findall(r"<a\s[^>]*>", page.read_text(encoding="utf-8")):
            m = re.search(r'href="([^"#]+)', tag)
            if not m or "unresolved" in tag or re.match(r"^[a-z][a-z0-9+.-]*:", m.group(1)):
                continue
            href = m.group(1)
            if not (page.parent / unquote(href)).exists():
                bad.append(f"{page.relative_to(out)} -> {href}")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plans-dir", type=Path, default=Path.home() / ".claude" / "plans")
    ap.add_argument("--out", type=Path, default=Path.home() / ".cache" / "campaign-dashboard")
    ap.add_argument("--sessions-dir", type=Path, default=Path.home() / ".claude" / "projects",
                    help="Claude Code session logs: listed per project, and used to place loose plans")
    ap.add_argument("--history", type=Path, default=Path.home() / ".claude" / "history.jsonl",
                    help="Claude Code's prompt history: shows sessions whose log was deleted, from their prompts")
    ap.add_argument("--live-dir", type=Path, default=Path.home() / ".claude" / "sessions",
                    help="Claude Code's running-process files, used to mark live sessions")
    ap.add_argument("--claude-dir", type=Path, default=Path.home() / ".claude",
                    help="where skills, commands and plugins are installed")
    ap.add_argument("--archive-state", type=Path, default=default_state_dir(),
                    help="state folder of the claude-archive job (last-push and manifest)")
    ap.add_argument("--archive-repo", type=Path, default=Path.home() / "claude-archive",
                    help="the archive git repo, whose size the Archive tab shows")
    ap.add_argument("--no-git", action="store_true", help="skip the read-only git queries")
    ap.add_argument("--open", action="store_true", help="open the dashboard with xdg-open")
    ap.add_argument("--serve", action="store_true",
                    help="serve the dashboard on 127.0.0.1 and update open pages when the files change")
    ap.add_argument("--port", type=int, default=8765, help="port for --serve (default 8765)")
    ap.add_argument("--check-links", action="store_true", help="fail if a generated relative link is broken")
    args = ap.parse_args()

    if args.serve:
        git_cache: dict = {}
        site = Site(lambda sessions: build_site(args, sessions, git_cache), watched(args))
        httpd = serve(site, args.plans_dir, args.port)
        url = f"http://127.0.0.1:{args.port}/"
        print(f"{site.renderer.summary} → {url}", flush=True)
        if args.open:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        return

    r = build_site(args)
    r.build(args.out)
    index = args.out / "index.html"
    print(f"{r.summary} → {index}")

    if args.check_links:
        bad = broken_links(args.out)
        for b in bad:
            print(f"broken link: {b}", file=sys.stderr)
        if bad:
            sys.exit(1)
    if args.open:
        subprocess.Popen(["xdg-open", str(index)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
