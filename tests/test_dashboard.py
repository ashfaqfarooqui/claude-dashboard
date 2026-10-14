"""Contracts: each MASTER.md format variant on disk parses to the right progress numbers, links in
rendered docs lead somewhere real, and one malformed campaign never stops the site being built.

Fixtures are trimmed copies of real campaigns; expected counts were taken with grep over the
fixture's Status table ID column, not from the parser.
"""

import argparse
import json
import shutil
import sys
import threading
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import pytest

from campaign_dashboard.cli import build_site, main, watched
from campaign_dashboard.parse import parse_campaign
from campaign_dashboard.projects import attribute_plans, group, load_loose_plans
from campaign_dashboard.render import Renderer
from campaign_dashboard.server import Site, serve
from campaign_dashboard.sessions import load_sessions, usage
from campaign_dashboard.skills import load_skills

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "slug, expected",
    [
        # current format: Status table, wave tables, "- **D<n> / … Resolved …" decisions
        ("sdb-cli", dict(counts={"☐": 17}, waves=5, done_waves=0, current="Wave 1", open_decisions=[],
                         decisions=4, has_next=True, awaiting="commit the migration")),
        # older format: "☑ done" glyphs, rows split off by blank lines, "## Decisions taken" as a numbered list
        ("scenario-weaver", dict(counts={"☑": 46, "☐": 1}, waves=0, done_waves=0, current=None,
                                 open_decisions=[], decisions=5, has_next=False, awaiting=None)),
        # plan-mode-era: no Status table, so issues come from filenames with unknown status
        ("openscenario-rs", dict(counts={"unknown": 12}, waves=0, done_waves=0, current=None,
                                 open_decisions=[], decisions=0, has_next=False, awaiting=None)),
    ],
)
def test_format_variants_parse_to_progress(slug, expected):
    c = parse_campaign(FIXTURES / slug)

    assert c.errors == []
    assert {k: v for k, v in c.counts().items() if v} == expected["counts"]
    assert len(c.waves) == expected["waves"]
    assert c.waves_done() == expected["done_waves"]
    cw = c.current_wave()
    assert (cw.name.startswith(expected["current"]) if cw else None) == (True if expected["current"] else None)
    assert [d.id for d in c.open_decisions()] == expected["open_decisions"]
    assert len(c.decisions) == expected["decisions"]
    assert ("next" in c.start_here) == expected["has_next"]
    assert c.start_here.get("awaiting", "").startswith(expected["awaiting"] or "") is True
    if expected["awaiting"] is None:
        assert "awaiting" not in c.start_here


def test_rendered_links_point_at_generated_pages_or_real_files(tmp_path):
    plans = tmp_path / "plans"
    shutil.copytree(FIXTURES / "sdb-cli", plans / "sdb-cli")
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "lib.rs").write_text("")
    (plans / "loose-plan.md").write_text("# p")
    (plans / "sdb-cli" / "assets").mkdir()
    (plans / "sdb-cli" / "assets" / "flow.png").write_bytes(b"png")
    r = Renderer(plans, date(2026, 9, 30))
    html = str(r.render_md(
        "[a](SDB-03-search-multibyte-panic.md#why) [b](src/lib.rs) [c](nowhere.md) [d](https://x.org)"
        " [e](../loose-plan.md)",
        plans / "sdb-cli", str(repo), depth=1,
    ))
    # an image is linked from the page's depth, so it also resolves on the overview (depth 0)
    top = str(r.render_md("![flow](assets/flow.png)\n\n```mermaid\ngraph LR; a-->b\n```\n",
                          plans / "sdb-cli", None, depth=0))

    assert 'href="../sdb-cli/SDB-03-search-multibyte-panic.html#why"' in html
    assert f'href="{(repo / "src" / "lib.rs").as_uri()}"' in html
    assert 'href="nowhere.md" class="unresolved"' in html
    assert 'href="https://x.org"' in html
    assert 'href="../plans/loose-plan.html"' in html
    assert 'src="sdb-cli/assets/flow.png"' in top
    assert '<pre class="mermaid">graph LR; a--&gt;b\n</pre>' in top


def test_malformed_campaign_does_not_stop_the_build(tmp_path, monkeypatch):
    plans = tmp_path / "plans"
    shutil.copytree(FIXTURES / "sdb-cli", plans / "sdb-cli")
    (plans / "broken").mkdir()
    (plans / "broken" / "MASTER.md").write_bytes(b"\xff\xfe not utf-8 \x80")
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["campaign-dashboard", "--plans-dir", str(plans), "--out", str(out),
                                      "--sessions-dir", str(tmp_path / "no-sessions"),
                                      "--claude-dir", str(tmp_path / "no-claude"), "--no-git", "--check-links"])

    main()  # --check-links exits non-zero on a broken link; returning means exit 0

    index = (out / "index.html").read_text()
    assert 'href="sdb-cli/index.html"' in index
    assert "broken" in index and "parse error" in index
    assert (out / "sdb-cli" / "SDB-03-search-multibyte-panic.html").exists()


def test_folders_before_planning_show_their_stage_not_an_error(tmp_path, monkeypatch):
    """A brainstorm (DESIGN.md only) or an audit (FINDINGS.md only) has no MASTER.md yet: it gets a stage,
    the brainstorm's unfilled template sections and open decisions come from DESIGN.md, it is placed by the
    repo DESIGN.md names, and it is listed as waiting on you."""
    plans = tmp_path / "plans"
    shutil.copytree(FIXTURES / "sdb-watch", plans / "sdb-watch")
    (plans / "audit-only").mkdir()
    (plans / "audit-only" / "FINDINGS.md").write_text("# f\n\n### F1 (H) — x. *Confirmed by running*\n")

    c = parse_campaign(plans / "sdb-watch")

    assert (c.stage, c.errors, c.repo) == ("brainstorm", [], "/home/ashfaqf/playground/sdb-cli")
    assert (c.design.status, c.design.verdict, c.design.disagreements) == ("in progress", "open", 1)
    assert [k for k, ok in c.design.settled.items() if ok] == ["Problem", "Success"]
    assert [d.id for d in c.open_decisions()] == ["D1"]
    a = parse_campaign(plans / "audit-only")
    assert (a.stage, a.errors) == ("audited", [])

    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["campaign-dashboard", "--plans-dir", str(plans), "--out", str(out),
                                      "--sessions-dir", str(tmp_path / "no-sessions"),
                                      "--claude-dir", str(tmp_path / "no-claude"), "--no-git", "--check-links"])
    main()

    waiting = (out / "index.html").read_text().split('class="waiting"')[1].split("</section>")[0]
    assert "/campaign-brainstorm sdb-watch" in waiting and "/campaign-plan audit-only" in waiting
    assert "parse error" not in (out / "index.html").read_text()
    assert (out / "p" / "sdb-cli.html").read_text().count('href="../sdb-watch/index.html"') >= 1


def test_live_server_shows_file_changes_and_serves_only_campaign_assets(tmp_path):
    """Served pages are rendered from the files as they are now: after an edit, one poll is enough for the
    next request to show it. Plan images are served from a campaign's assets/ folder and nothing else."""
    plans = tmp_path / "plans"
    shutil.copytree(FIXTURES / "sdb-watch", plans / "sdb-watch")
    (plans / "sdb-watch" / "assets").mkdir()
    (plans / "sdb-watch" / "assets" / "flow.png").write_bytes(b"\x89PNG")
    (plans / "secret.png").write_bytes(b"\x89PNG")
    args = argparse.Namespace(plans_dir=plans, sessions_dir=tmp_path / "no", live_dir=tmp_path / "no",
                              claude_dir=tmp_path / "no", no_git=True, serve=True)
    site = Site(lambda cache: build_site(args, cache), watched(args))
    httpd = serve(site, plans, 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}/"

    def get(path):
        try:
            with urllib.request.urlopen(base + path) as r:
                return r.status, r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, ""

    try:
        assert "Cache on disk or in memory?" in get("sdb-watch/index.html")[1]
        assert site.poll() is False  # nothing changed, nothing rebuilt

        design = plans / "sdb-watch" / "DESIGN.md"
        design.write_text(design.read_text().replace("Cache on disk or in memory?", "Cache format?"))
        assert site.poll() is True and site.version == 1
        assert "Cache format?" in get("sdb-watch/index.html")[1]

        assert get("sdb-watch/assets/flow.png")[0] == 200
        assert get("secret.png")[0] == 404
        assert get("sdb-watch/DESIGN.md")[0] == 404
        assert get("sdb-watch/assets/../../secret.png")[0] == 404
    finally:
        httpd.shutdown()


def _tool_line(tool: str, path: Path, cwd: str) -> str:
    return json.dumps({"cwd": cwd, "message": {"content": [
        {"type": "tool_use", "name": tool, "input": {"file_path": str(path)}}]}}, separators=(",", ":"))


def test_loose_plans_are_grouped_by_the_session_that_wrote_them(tmp_path):
    plans = tmp_path / ".claude" / "plans"
    shutil.copytree(FIXTURES / "sdb-cli", plans / "sdb-cli")  # MASTER names /home/ashfaqf/playground/sdb-cli
    for name in ("written.md", "edited-in-subdir.md", "only-mentioned.md", "a-main.md", "b-main.md"):
        (plans / name).write_text(f"# {name}\n")
    sessions = tmp_path / "projects"
    (sessions / "x" / "s1" / "subagents").mkdir(parents=True)
    (sessions / "x" / "s1.jsonl").write_text("\n".join([
        _tool_line("Write", plans / "written.md", "/home/ashfaqf/playground/sdb-cli"),
        # a session that merely lists the folder must not claim the plan
        json.dumps({"cwd": "/elsewhere/a/main", "text": f"{plans}/only-mentioned.md"}),
        _tool_line("Write", plans / "a-main.md", "/elsewhere/a/main"),
        _tool_line("Write", plans / "b-main.md", "/elsewhere/b/main"),
    ]))
    (sessions / "x" / "s1" / "subagents" / "s2.jsonl").write_text(
        _tool_line("Edit", plans / "edited-in-subdir.md", "/home/ashfaqf/playground/sdb-cli/src/web"))

    campaigns = [parse_campaign(plans / "sdb-cli")]
    loose = load_loose_plans(plans)
    attribute_plans(loose, load_sessions(sessions))
    projects, unassigned = group(campaigns, loose)

    by_label = {p.label: p for p in projects}
    assert set(by_label) == {"sdb-cli", "a/main", "b/main"}  # two "main" dirs get told apart
    sdb = by_label["sdb-cli"]
    assert [c.slug for c in sdb.campaigns] == ["sdb-cli"]
    assert sorted(p.name for p in sdb.plans) == ["edited-in-subdir.md", "written.md"]  # subdir rolls up
    assert [p.name for p in by_label["b/main"].plans] == ["b-main.md"]
    assert [p.name for p in unassigned.plans] == ["only-mentioned.md"]


def _line(**d) -> str:
    return json.dumps(d, separators=(",", ":"))


def test_session_summary_and_placement(tmp_path):
    """A session log becomes one row: typed prompts only, final cost, the campaign it wrote to,
    and it lands in the project its cwd is inside; a session elsewhere lands in Unassigned."""
    plans = tmp_path / ".claude" / "plans"
    shutil.copytree(FIXTURES / "sdb-cli", plans / "sdb-cli")
    cwd = "/home/ashfaqf/playground/sdb-cli/src"
    proj = tmp_path / "projects" / "p"
    (proj / "s1" / "subagents").mkdir(parents=True)
    (proj / "s1.jsonl").write_text("\n".join([
        _line(type="user", cwd=cwd, timestamp="2026-09-30T08:00:00Z", message={"content": "fix the panic"}),
        _line(type="user", cwd=cwd, isMeta=True, message={"content": "injected"}),
        _line(type="user", cwd=cwd, message={"content": "<command-name>/clear</command-name>"}),
        _line(type="user", cwd=cwd, message={"content": [{"type": "tool_result", "content": "ok"}]}),
        _line(type="user", cwd=cwd, origin={"kind": "task-notification"}, message={"content": "agent done"}),
        _line(type="assistant", cwd=cwd, timestamp="2026-09-30T08:30:00Z", message={"model": "claude-opus-5-5"}),
        _line(type="user", cwd=cwd, message={"content": [{"type": "text", "text": "now commit"}]}),
        _line(type="ai-title", aiTitle="Fix search panic"),
        _line(type="cost-state", totalCostUSD=1.0, totalLinesAdded=1, totalLinesRemoved=0),
        _line(type="cost-state", totalCostUSD=2.5, totalLinesAdded=10, totalLinesRemoved=3),
    ]))
    (proj / "s1" / "subagents" / "a.jsonl").write_text(
        _tool_line("Edit", plans / "sdb-cli" / "MASTER.md", cwd))
    (proj / "s2.jsonl").write_text(_line(type="user", cwd="/tmp/scratch", message={"content": "hi"}))

    sessions = {s.id: s for s in load_sessions(tmp_path / "projects")}
    s1 = sessions["s1"]
    assert (s1.title, s1.first_prompt, s1.prompts) == ("Fix search panic", "fix the panic", 2)
    assert (s1.cost, s1.lines_added, s1.lines_removed) == (2.5, 10, 3)
    assert s1.models == ["claude-opus-5-5"] and s1.subagents == 1
    assert (s1.ended - s1.started).total_seconds() == 1800
    assert s1.touched("sdb-cli") and not s1.touched("sdb")

    projects, unassigned = group([parse_campaign(plans / "sdb-cli")], [], list(sessions.values()))
    assert [s.id for s in projects[0].sessions] == ["s1"]
    assert [s.id for s in unassigned.sessions] == ["s2"]


def test_tool_calls_are_tallied_with_their_outcomes(tmp_path):
    """Calls from the session and its subagents add up; a failed result is charged to the tool that
    made the call and sorted into error / rejected by you / denied by a rule; skills Claude invoked and
    commands you typed stay apart."""
    def use(i, name, **inp):
        return _line(type="assistant", message={"content": [{"type": "tool_use", "id": i, "name": name, "input": inp}]})

    def fail(i, text):
        return _line(type="user", message={"content": [{"type": "tool_result", "tool_use_id": i, "is_error": True,
                                                        "content": text}]})

    proj = tmp_path / "projects" / "p"
    (proj / "s1" / "subagents").mkdir(parents=True)
    (proj / "s1.jsonl").write_text("\n".join([
        _line(type="user", message={"content": "<command-name>/clear</command-name>"}),
        _line(type="user", message={"content": "<command-name>/campaign-run</command-name>"}),
        use("a", "Bash", command="ls"), fail("a", "Exit code 1"),
        use("b", "Bash", command="rm"), fail("b", "The user doesn't want to proceed with this tool use."),
        use("c", "Bash", command="push"), fail("c", "Permission for this action was denied by the classifier."),
        use("d", "Skill", skill="campaign-run"),
        use("e", "Write", file_path="/r/x.py"),
    ]))
    (proj / "s1" / "subagents" / "agent-q.jsonl").write_text(use("f", "Edit", file_path="/r/x.py"))
    (proj / "s1" / "subagents" / "agent-q.meta.json").write_text('{"agentType": "Explore", "description": "look"}')

    [s] = load_sessions(tmp_path / "projects")
    assert s.tools.calls == {"Bash": 3, "Skill": 1, "Write": 1, "Edit": 1}
    assert (s.tools.errors, s.tools.rejected, s.tools.denied) == ({"Bash": 1}, {"Bash": 1}, {"Bash": 1})
    assert s.tools.files == {"/r/x.py": 2}
    assert [(a.type, a.description) for a in s.agents] == [("Explore", "look")]

    u = usage([s])
    assert [(r.name, r.count, r.extra) for r in u["skills"]] == [("campaign-run", 1, 1)]
    assert [r.name for r in u["commands"]] == ["clear"]


def test_available_skills_are_found_and_cross_referenced(tmp_path):
    """Your skills, commands, claude.ai-synced skills and enabled plugins are listed under the name
    they are invoked by; a disabled plugin is not; a mention counts as a reference only when it reads
    as a skill, not as an ordinary word."""
    home = tmp_path / ".claude"

    def skill(folder, name, body, extra=""):
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: >\n  Does {name}\n  well.\n{extra}---\n{body}")

    skill(home / "skills" / "campaign-run", "campaign-run", "Uses the `test-audit` skill. Then commit.")
    (home / "skills" / "campaign-run" / "reference").mkdir()
    (home / "skills" / "campaign-run" / "reference" / "modes.md").write_text("Invoke /herdr here.")
    skill(home / "skills" / "test-audit", "test-audit", "Nothing.", 'when_to_use: "When testing"\n')
    skill(home / "skills" / "herdr", "herdr", "Nothing.")
    (home / "commands").mkdir()
    (home / "commands" / "commit.md").write_text("# Commit\n\nStage and commit changes.\n")
    skill(home / "skills" / "synced" / "org" / "pdf", "pdf", "Nothing.")
    for plugin, on in (("on", True), ("off", False)):
        skill(tmp_path / plugin / "skills" / "debug", "debug", "Nothing.")
    (home / "plugins").mkdir()
    (home / "plugins" / "installed_plugins.json").write_text(json.dumps({"plugins": {
        f"{p}@mk": [{"installPath": str(tmp_path / p)}] for p in ("on", "off")}}))
    (home / "settings.json").write_text(json.dumps({"enabledPlugins": {"on@mk": True, "off@mk": False}}))

    docs = {d.name: d for d in load_skills(home)}

    assert set(docs) == {"campaign-run", "test-audit", "herdr", "commit", "anthropic-skills:pdf", "on:debug"}
    run = docs["campaign-run"]
    assert run.description == "Does campaign-run well."
    assert docs["test-audit"].meta["when_to_use"] == "When testing"
    assert run.refs == ["herdr", "test-audit"]  # "commit" in plain prose is not a reference
    assert [f.name for f in run.files] == ["modes.md"]
    assert (docs["commit"].kind, docs["commit"].description) == ("command", "Stage and commit changes.")
