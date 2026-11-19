"""Render the static site.

index.html (All tab) · p/<project>.html (one tab per project, p/unassigned.html) ·
<slug>/index.html + <slug>/<file>.html (campaigns) · plans/<file>.html (loose plans) ·
s/<session id>.html (sessions) · usage.html (tools, skills and subagents across sessions) · archive.html (the claude-archive job) ·
skills/index.html + skills/<skill>/index.html + skills/<skill>/<file>.html (skills and commands)
"""

import re
import shutil
from collections.abc import Callable
from datetime import date, datetime
from importlib.resources import files as pkg_files
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from markupsafe import Markup

from .archive import Archive
from .model import CLOSED, GLYPHS, Campaign
from .parse import parse_issue_header
from .projects import LoosePlan, Project
from .sessions import NEVER, Session, usage
from .skills import SkillDoc

MAX_RENDER_BYTES = 2_000_000
STATUS_NAMES = {"☑": "done", "◐": "in progress", "⊘": "blocked", "✗": "won't fix", "☐": "ready", "unknown": "unknown"}
STATIC = ("style.css", "mermaid.min.js")  # served at the site root
ASSETS = "assets"  # per-campaign folder of images the plan files link to
STATUS_CLASS = {"☑": "done", "◐": "wip", "⊘": "blocked", "✗": "wontfix", "☐": "ready", "unknown": "unknown"}


def page_for(fname: str) -> str:
    return fname[:-3] + ".html" if fname.endswith(".md") else fname + ".html"


def short_path(path: str, cwd: str | None) -> str:
    """`path` relative to `cwd` when inside it, else with the home directory as ~."""
    if cwd and path.startswith(cwd.rstrip("/") + "/"):
        return path[len(cwd.rstrip("/")) + 1:]
    home = str(Path.home())
    return "~" + path[len(home):] if path.startswith(home + "/") else path


def static_file(name: str) -> Path:
    folder = "templates" if name.endswith(".css") else "static"
    return Path(str(pkg_files("campaign_dashboard").joinpath(f"{folder}/{name}")))


def _mermaid(code: str, lang: str, _attrs: str) -> str | None:
    """markdown-it uses a highlighter's output as-is when it starts with <pre; None means the default fence."""
    return f'<pre class="mermaid">{escapeHtml(code)}</pre>\n' if lang == "mermaid" else None


class Renderer:
    """Builds the site as a map of page path -> function that renders it, so a server can render one
    page on request and the static build can render them all."""

    def __init__(self, plans_dir: Path, today: date, live: bool = False):
        self.plans_dir = plans_dir.resolve()
        self.today = today
        self.pages: dict[str, Callable[[], str]] = {}
        self.summary = ""  # one line for the CLI: what was loaded
        self.site_pages: dict[Path, str] = {}  # source file -> its page, for files outside plans_dir
        self.md = MarkdownIt("commonmark", {"html": True, "highlight": _mermaid}).enable(["table", "strikethrough"])
        # add_render_rule binds the function to the markdown renderer, which arrives as its first argument
        self.md.add_render_rule("link_open", lambda r, *a: self._link_open(r, *a))
        self.md.add_render_rule("image", lambda r, *a: self._image(r, *a))
        self.env = Environment(loader=PackageLoader("campaign_dashboard"), autoescape=select_autoescape())
        self.env.globals.update(
            md=self.render_md,
            ago=self.ago,
            duration=self.duration,
            plan_links=self.plan_links,
            file_link=self.file_link,
            short_path=short_path,
            glyphs=GLYPHS,
            status_names=STATUS_NAMES,
            status_class=STATUS_CLASS,
            closed=CLOSED,
            page_for=page_for,
            today=today,
            live=live,
        )

    # --- markdown -------------------------------------------------------------------------

    def _link_open(self, renderer, tokens, idx, options, env):
        tok = tokens[idx]
        href = tok.attrGet("href")
        if isinstance(href, str) and not re.match(r"^([a-z][a-z0-9+.-]*:|#)", href):
            if new := self.rewrite_href(href, env):
                tok.attrSet("href", new)
            else:  # the source file's own link points nowhere; keep it, but say so
                tok.attrSet("class", "unresolved")
                tok.attrSet("title", "not found next to the plan file or in the repo")
        return renderer.renderToken(tokens, idx, options, env)

    def _image(self, renderer, tokens, idx, options, env):
        """A relative image inside the plans folder is linked from the page's depth, not the file's folder."""
        tok = tokens[idx]
        src = tok.attrGet("src")
        if isinstance(src, str) and not re.match(r"^([a-z][a-z0-9+.-]*:|/)", src):
            path = (env["base"] / src).resolve()
            if path.is_file() and path.is_relative_to(self.plans_dir):
                tok.attrSet("src", "../" * env["depth"] + str(path.relative_to(self.plans_dir)))
        return type(renderer).image(renderer, tokens, idx, options, env)

    def rewrite_href(self, href: str, env: dict) -> str | None:
        """Point links at plan files to their rendered pages; other local paths become file:// links.

        A relative link is tried next to the plan file first, then in the campaign's repo, since
        issue docs often cite repo files (`src/x.rs`, `CONTRIBUTING.md`) relative to the repo root.
        """
        target, _, frag = href.partition("#")
        if target.startswith("/"):
            candidates = [Path(target)]
        else:
            candidates = [env["base"] / target] + ([Path(env["repo"]) / target] if env["repo"] else [])
        path = next((p.resolve() for p in candidates if p.exists()), None)
        if path is None:
            return None
        prefix = "../" * env["depth"]
        if path.is_dir() and (path / "SKILL.md") in self.site_pages:
            path = path / "SKILL.md"
        if path in self.site_pages:
            return prefix + self.site_pages[path] + (f"#{frag}" if frag else "")
        try:
            rel = path.relative_to(self.plans_dir)
        except ValueError:
            return path.as_uri()
        parts = rel.parts
        if len(parts) == 1 and path.is_dir():
            dest = f"{parts[0]}/index.html"
        elif len(parts) == 1 and path.suffix == ".md":
            dest = f"plans/{page_for(parts[0])}"
        elif len(parts) == 2 and path.is_file():
            dest = f"{parts[0]}/{page_for(parts[1])}"
        else:
            return path.as_uri()
        return prefix + dest + (f"#{frag}" if frag else "")

    def render_md(self, text: str | None, base: Path, repo: str | None, depth: int) -> Markup:
        """`base` is the folder relative links start from; `repo` is the fallback for repo-relative links."""
        if not text:
            return Markup("")
        return Markup(self.md.render(text, {"base": base, "repo": repo, "depth": depth}))

    def ago(self, d: date | None) -> str:
        if d is None:
            return "—"
        days = (self.today - d).days
        return "today" if days <= 0 else "yesterday" if days == 1 else f"{days} days ago"

    @staticmethod
    def duration(start: datetime, end: datetime) -> str:
        """Wall-clock span from first to last log line (a resumed session spans the gap too)."""
        mins = int((end - start).total_seconds() // 60)
        if mins < 60:
            return f"{mins} min"
        if mins < 48 * 60:
            return f"{mins // 60} h {mins % 60:02d} min"
        return f"{mins // (24 * 60)} days"

    def plan_links(self, s: Session) -> list[dict[str, str]]:
        """The campaigns and loose plans a session wrote to, as links into the site."""
        out: dict[str, dict[str, str]] = {}
        for rel in sorted({rel for _, rel in s.plan_writes}):
            head = rel.split("/", 1)[0]
            if head in self._campaigns:
                out.setdefault(head, {"href": f"{head}/index.html", "label": head})
            elif head in self._plans:
                title = self._plans[head].title
                out.setdefault(head, {"href": f"plans/{page_for(head)}",
                                      "label": title if len(title) <= 40 else title[:39] + "…"})
        return list(out.values())

    def file_link(self, path: str) -> str:
        """A written file as a link from a page one level down: its rendered page if it is a plan file."""
        return self.rewrite_href(path, {"base": Path("/"), "repo": None, "depth": 1}) or Path(path).as_uri()

    # --- pages ----------------------------------------------------------------------------

    def page(self, rel: str, render: Callable[[], str]) -> None:
        self.pages[rel] = render

    def build(self, out: Path) -> None:
        """The static site: every page, the static files, and each campaign's assets folder."""
        out.mkdir(parents=True, exist_ok=True)
        for rel, render in self.pages.items():
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(render(), encoding="utf-8")
        for name in STATIC:
            shutil.copyfile(static_file(name), out / name)
        for assets in self.plans_dir.glob(f"*/{ASSETS}"):
            if assets.is_dir():
                shutil.copytree(assets, out / assets.relative_to(self.plans_dir), dirs_exist_ok=True)

    def register(self, projects: list[Project], unassigned: Project, skills: list[SkillDoc] = (),
                 archive: Archive | None = None) -> None:
        everyone = [*projects, unassigned]
        project_of = {c.slug: p for p in everyone for c in p.campaigns}
        plan_project = {pl.name: (p if p is not unassigned else None) for p in everyone for pl in p.plans}
        session_project = {s.id: (p if p is not unassigned else None) for p in everyone for s in p.sessions}
        self._campaigns = {c.slug for p in everyone for c in p.campaigns}
        self._plans = {pl.name: pl for p in everyone for pl in p.plans}
        self.env.globals.update(projects=projects, unassigned=unassigned, project_of=project_of,
                                plan_project=plan_project, session_project=session_project, archive=archive)
        campaigns = sorted((c for p in everyone for c in p.campaigns),
                           key=lambda c: c.last_activity or date.min, reverse=True)
        plans = sorted((pl for p in everyone for pl in p.plans), key=lambda pl: pl.modified, reverse=True)
        sessions = sorted((s for p in everyone for s in p.sessions),
                          key=lambda s: s.ended or NEVER, reverse=True)
        overview = self.env.get_template("overview.html")

        tpl = self.env.get_template
        self.page("index.html", lambda: overview.render(
            active="all", root="", depth=0, heading="All projects", project=None, campaigns=campaigns,
            plans=plans, sessions=sessions))
        for p in everyone:
            self.page(f"p/{p.key}.html", lambda p=p: overview.render(
                active=p.key, root="../", depth=1, heading=p.label, project=p, campaigns=p.campaigns,
                plans=p.plans, sessions=p.sessions))
            for c in p.campaigns:
                self.page(f"{c.slug}/index.html", lambda p=p, c=c: tpl("campaign.html").render(
                    c=c, active=p.key, root="../", sessions=[s for s in sessions if s.touched(c.slug)]))
                for fname in c.files:
                    self.page(f"{c.slug}/{page_for(fname)}",
                              lambda p=p, c=c, f=fname: self._doc_page(c.path / f, p, c=c))
            for ss in p.sessions:
                self.page(f"s/{ss.id}.html", lambda p=p, ss=ss: tpl("session.html").render(
                    s=ss, active=p.key, root="../", tool_rows=usage([ss])["tools"],
                    continued_from=[o for o in sessions if o.continued_in == ss.id]))
            for pl in p.plans:
                self.page(f"plans/{page_for(pl.name)}", lambda p=p, pl=pl: self._doc_page(
                    pl.path, p, plan=pl, sessions=[s for s in sessions if s.touched(pl.name)]))

        u = usage(sessions)
        self.page("usage.html", lambda: tpl("usage.html").render(
            active="usage", root="", sessions=sessions, u=u,
            by_project=[(p, usage(p.sessions)) for p in everyone if p.sessions]))
        self.page("archive.html", lambda: tpl("archive.html").render(active="archive", root="", a=archive))
        self._register_skills(list(skills), u)

    def _register_skills(self, skills: list[SkillDoc], u: dict) -> None:
        """skills/index.html, one page per skill or command, and one per file in a skill folder."""
        pages: dict[Path, str] = {}
        for sk in skills:
            pages[sk.path.resolve()] = f"skills/{sk.key}/index.html"
            for f in sk.files:
                pages[f.resolve()] = f"skills/{sk.key}/{page_for(str(f.relative_to(sk.folder)))}"
        self.site_pages.update(pages)
        by_key = {sk.name: sk for sk in skills}
        invoked = {r.name: r for r in u["skills"]}
        typed = {r.name: r for r in u["commands"]}

        def used(sk: SkillDoc) -> dict:
            bare = sk.name.split(":")[-1]
            r = invoked.get(sk.name) or invoked.get(bare)
            t = typed.get(sk.name) or typed.get(bare)
            lasts = [x.last for x in (r, t) if x and x.last]
            return {"invoked": r.count if r else 0, "typed": (r.extra if r else 0) + (t.count if t else 0),
                    "last": max(lasts) if lasts else None}

        usage_of = {sk.name: used(sk) for sk in skills}
        bare_count: dict[str, int] = {}
        for sk in skills:
            bare_count[sk.name.split(":")[-1]] = bare_count.get(sk.name.split(":")[-1], 0) + 1
        dupes = {sk.name for sk in skills if bare_count[sk.name.split(":")[-1]] > 1}
        groups: dict[str, list[SkillDoc]] = {}
        for sk in skills:
            groups.setdefault(sk.source, []).append(sk)
        self.page("skills/index.html", lambda: self.env.get_template("skills.html").render(
            active="skills", root="../", groups=groups, usage_of=usage_of, dupes=dupes, by_key=by_key,
            total=len(skills)))
        referenced_by = {sk.name: [o for o in skills if sk.name in o.refs] for sk in skills}
        tpl = self.env.get_template("skill.html")
        for sk in skills:
            self.page(f"skills/{sk.key}/index.html", lambda sk=sk: tpl.render(
                active="skills", root="../../", sk=sk, file=None, used=usage_of[sk.name], by_key=by_key,
                dupe=sk.name in dupes, referenced_by=referenced_by[sk.name],
                body=self.render_md(sk.body, sk.folder, None, depth=2)))
            for f in sk.files:
                rel = str(f.relative_to(sk.folder))
                self.page(f"skills/{sk.key}/{page_for(rel)}",
                          lambda sk=sk, f=f, rel=rel: self._skill_file_page(tpl, sk, f, rel, usage_of, by_key))

    def _skill_file_page(self, tpl, sk: SkillDoc, f: Path, rel: str, usage_of: dict, by_key: dict) -> str:
        depth = 2 + rel.count("/")
        body = raw = None
        if f.stat().st_size <= MAX_RENDER_BYTES:
            try:
                text = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = None
            if text is not None and f.suffix == ".md":
                body = self.render_md(text, f.parent, None, depth=depth)
            else:
                raw = text
        return tpl.render(
            active="skills", root="../" * depth, sk=sk, file=rel, body=body, raw=raw,
            file_uri=f.resolve().as_uri(), used=usage_of[sk.name], by_key=by_key, dupe=False)

    def _doc_page(self, path: Path, project: Project, c: Campaign | None = None,
                  plan: LoosePlan | None = None, sessions: list[Session] = ()) -> str:
        fname = path.name
        size = path.stat().st_size
        body: Markup | None = None
        raw: str | None = None
        header: dict[str, str] = {}
        issue = next((i for i in c.issues.values() if i.doc == fname), None) if c else None
        repo = c.repo if c else (project.dir or None)
        if size <= MAX_RENDER_BYTES:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = None
            if text is not None and fname.endswith(".md"):
                body = self.render_md(text, path.parent, repo, depth=1)
                if issue:
                    header = parse_issue_header(text)
            else:
                raw = text
        return self.env.get_template("doc.html").render(
            c=c, plan=plan, project=project if project.dir else None, fname=fname, body=body, raw=raw,
            size=size, issue=issue, header=header, file_uri=path.resolve().as_uri(),
            active=project.key, root="../", sessions=sessions,
        )
