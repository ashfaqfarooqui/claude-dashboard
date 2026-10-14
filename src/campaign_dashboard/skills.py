"""Skills and slash commands available to Claude Code on this machine.

Sources, in the order they are listed:
- ~/.claude/skills/<name>/SKILL.md              your skills
- ~/.claude/commands/<name>.md                 your commands
- ~/.claude/skills/synced/<org>/<name>/        skills synced from claude.ai   (anthropic-skills:)
- ~/.claude/plugins/synced/<org>/<plugin>~*/   plugins synced from claude.ai  (<plugin>:)
- installed_plugins.json entries enabled in settings.json                      (<plugin>:)
  read from their source folder when the marketplace was added from a local directory, since
  Claude Code loads those in place and the cached copy goes stale
- <project>/.claude/skills and /commands for each dashboard project

Plugins that are only in a marketplace checkout, and anything under plugins/.trash, are not
available and are not listed.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_FILES = 200  # per skill; a skill folder is instructions plus a few scripts, not a repo


@dataclass
class SkillDoc:
    name: str  # as invoked: `campaign-run`, `engineering:debug`
    kind: str  # "skill" | "command"
    source: str  # group heading on the page
    path: Path  # SKILL.md or the command .md
    meta: dict[str, str] = field(default_factory=dict)
    body: str = ""
    files: list[Path] = field(default_factory=list)  # other files in the skill folder
    refs: list[str] = field(default_factory=list)  # other skills this one mentions

    @property
    def key(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")

    @property
    def folder(self) -> Path:
        return self.path.parent

    @property
    def description(self) -> str:
        if d := self.meta.get("description"):
            return d
        # a command without frontmatter: its first prose line is its description
        line = next((ln for ln in self.body.splitlines() if ln.strip() and not ln.startswith("#")), "")
        return line.strip()


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """`key: value` pairs from a leading `---` block (one level, folded continuation lines)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    meta: dict[str, str] = {}
    key = None
    for line in text[3:end].splitlines():
        if m := re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line):
            key, val = m.group(1), m.group(2).strip()
            meta[key] = "" if val in (">", "|", ">-", "|-") else val
        elif key and line.startswith((" ", "\t")):
            meta[key] = (meta[key] + " " + line.strip()).strip()
    for k, v in meta.items():
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            meta[k] = v[1:-1].replace('\\"', '"')
    return meta, text[end + 4:].lstrip("\n")


def _skill(folder: Path, name: str, source: str) -> SkillDoc | None:
    md = folder / "SKILL.md"
    try:
        meta, body = parse_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p != md
                   and "__pycache__" not in p.parts and not p.name.startswith("."))[:MAX_FILES]
    return SkillDoc(name=name if ":" in name else meta.get("name", name), kind="skill",
                    source=source, path=md, meta=meta, body=body, files=files)


def _command(md: Path, name: str, source: str) -> SkillDoc | None:
    try:
        meta, body = parse_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    return SkillDoc(name=name, kind="command", source=source, path=md, meta=meta, body=body)


def _from_root(root: Path, prefix: str, source: str) -> list[SkillDoc]:
    """skills/<name>/SKILL.md and commands/<name>.md under a plugin or .claude root."""
    out = [_skill(d, prefix + d.name, source) for d in sorted((root / "skills").glob("*/"))
           if (d / "SKILL.md").is_file()]
    out += [_command(f, prefix + f.stem, source) for f in sorted((root / "commands").glob("*.md"))]
    return [s for s in out if s]


def load_skills(claude_dir: Path, project_dirs: list[str] = ()) -> list[SkillDoc]:
    out: list[SkillDoc] = []
    for d in sorted((claude_dir / "skills").glob("*/")):
        if (d / "SKILL.md").is_file() and (s := _skill(d, d.name, "Your skills")):
            out.append(s)
    out += [c for f in sorted((claude_dir / "commands").glob("*.md"))
            if (c := _command(f, f.stem, "Your commands"))]
    for d in sorted((claude_dir / "skills" / "synced").glob("*/*/")):
        if (d / "SKILL.md").is_file() and (s := _skill(d, f"anthropic-skills:{d.name}", "Synced from claude.ai")):
            out.append(s)
    for root in sorted((claude_dir / "plugins" / "synced").glob("*/*/")):
        name = root.name.split("~")[0]
        out += _from_root(root, f"{name}:", f"Plugin: {name} (synced from claude.ai)")
    out += _installed_plugins(claude_dir)
    for proj in project_dirs:
        out += _from_root(Path(proj) / ".claude", "", f"Project: {proj}")
    _link_refs(out)
    return out


def _installed_plugins(claude_dir: Path) -> list[SkillDoc]:
    try:
        installed = json.loads((claude_dir / "plugins" / "installed_plugins.json").read_text())["plugins"]
        enabled = json.loads((claude_dir / "settings.json").read_text()).get("enabledPlugins") or {}
    except (OSError, ValueError, KeyError):
        return []
    in_place = in_place_roots(claude_dir)
    out = []
    for plugin_id, installs in sorted(installed.items()):
        if not enabled.get(plugin_id) or not installs:
            continue
        name = plugin_id.split("@")[0]
        root = in_place.get(plugin_id, Path(installs[-1]["installPath"]))
        out += _from_root(root, f"{name}:", f"Plugin: {plugin_id}")
    return out


def in_place_roots(claude_dir: Path) -> dict[str, Path]:
    """`plugin@marketplace` → source folder, for relative-path plugins in a marketplace added from a
    local directory (settings.json `extraKnownMarketplaces`, source `directory`)."""
    try:
        markets = json.loads((claude_dir / "settings.json").read_text()).get("extraKnownMarketplaces") or {}
    except (OSError, ValueError):
        return {}
    out = {}
    for market, entry in markets.items():
        src = (entry or {}).get("source") or {}
        if src.get("source") != "directory" or not src.get("path"):
            continue
        mdir = Path(src["path"])
        try:
            plugins = json.loads((mdir / ".claude-plugin" / "marketplace.json").read_text())["plugins"]
        except (OSError, ValueError, KeyError):
            continue
        for p in plugins:
            if isinstance(p.get("source"), str):
                out[f"{p['name']}@{market}"] = (mdir / p["source"]).resolve()
    return out


def _link_refs(docs: list[SkillDoc]) -> None:
    """Record which other skills each one points at. A bare word is not enough ("commit", "debug"
    are ordinary words): the name must read as a skill — `/name`, `` `name` ``, `skills/name/`,
    "name skill", or a qualified `plugin:name`."""
    names: dict[str, str] = {}
    for d in docs:
        names.setdefault(d.name, d.name)
        names.setdefault(d.name.split(":")[-1], d.name)
    alt = "|".join(sorted(map(re.escape, names), key=len, reverse=True))
    pattern = re.compile(
        rf"(?:(?<=[/`])|(?<=skills/))({alt})(?=[`/\s.,)]|$)"  # /name, `name`, skills/name/
        rf"|(?<![\w-])({alt})(?= skill)"  # "name skill"
        rf"|(?<![\w-])([a-z][\w-]*:[a-z][\w-]*)(?![\w-])",  # plugin:name
        re.M,
    )
    for d in docs:
        texts = [d.body] + [f.read_text(encoding="utf-8", errors="replace") for f in d.files
                            if f.suffix == ".md" and f.stat().st_size < 200_000]
        found = {names[n] for t in texts for groups in pattern.findall(t) for n in groups if n in names}
        found.discard(d.name)
        d.refs = sorted(found)
