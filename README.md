# campaign

Two things in one repo:

- **The `campaign` Claude Code plugin** (`skills/`): `/campaign:brainstorm`, `/campaign:audit`,
  `/campaign:plan` and `/campaign:run`, which turn work into local campaign folders in
  `~/.claude/plans/<slug>/` (a MASTER.md tracker, one file per issue, a log), plus the `ste`,
  `programming` and `test-audit` rules that the campaign agents follow.
- **campaign-dashboard** (`src/`): an HTML view of those folders and of your Claude Code sessions.

## Install

Clone the repo and register the clone as a plugin marketplace. Claude Code then loads the skills
from the clone itself, so `git pull` (and `/reload-plugins` in a running session) updates them.

```sh
git clone https://github.com/<owner>/<repo> ~/playground/claude-dashboard
claude plugin marketplace add ~/playground/claude-dashboard
claude plugin install campaign@ashfaqf
```

Or open Claude Code in the clone and ask it to "install the campaign plugin from this repo".

Keep the clone where you registered it: new campaigns write the absolute path of the skills into
their `AGENT_PROMPT.md`.

## Dashboard

HTML overview of the campaign folders in `~/.claude/plans/<slug>/`
(format: `skills/plan/reference/format.md`), served live or written once as
static files. Read-only: it never writes to the plans or to any repo.

```sh
uv run campaign-dashboard --serve --open  # live on http://127.0.0.1:8765/
uv run campaign-dashboard --open          # writes ~/.cache/campaign-dashboard/ and opens it
uv run campaign-dashboard --no-git        # skip the git queries
uv run campaign-dashboard --check-links   # exit 1 if a generated link is broken
uv run pytest
```

**Live mode.** `--serve` renders each page when it is requested. Every 2 s it checks the size and
mtime of the plans, session logs, skills and each campaign repo's `.git/HEAD`, `index` and
`logs/HEAD`. When one changed it reloads, parsing again only the session logs that changed, and
open pages fetch themselves and swap in the parts that changed. It listens on 127.0.0.1 only. To run
it all the time:

```sh
cp contrib/campaign-dashboard.service ~/.config/systemd/user/
systemctl --user enable --now campaign-dashboard
```

**Diagrams and images.** A ```` ```mermaid ```` block in any plan file is drawn as a diagram (Mermaid
12.1.0, vendored in `static/`, loaded only on pages that have one). Images linked from a plan file
are served from the campaign's `assets/` folder and copied there by the static build.

Tabs: **All**, then one tab per project, then **Unassigned**. A project is a directory: a
campaign belongs to the repo its MASTER.md names, and a loose plan (`~/.claude/plans/*.md`) belongs
to the working directory of the Claude Code session that wrote it (found from Write/Edit calls in
`~/.claude/projects/**/*.jsonl`). A directory inside another project's directory rolls up into it.

Each tab shows the sessions running now, what's waiting on you, one card per campaign, the loose
plans, and the Claude Code sessions whose working directory is in that project (title, first
prompt, `claude -r <id>`, prompts, subagents, cost, lines changed, model, branch, the campaigns and
plans each one wrote to, PR links). Sessions in a directory with no campaign or plan go under
**Unassigned**. Running sessions come from `~/.claude/sessions/<pid>.json` (`--live-dir`).
Campaign and plan pages list the sessions that wrote to them.

Each session has its own page (`s/<id>.html`): every prompt you typed with its time, slash
commands, tool calls with errors / rejections / denials, skills, subagents (type, description, their
tool calls) and the files it wrote. The **Usage** tab tallies the same across all sessions: skills
(invoked by Claude vs typed by you), tools, MCP servers, subagent types, slash commands, and a
per-project breakdown. The **Skills** tab lists every skill and command Claude Code can load here
(your skills and commands, claude.ai-synced skills and plugins, enabled plugins, per-project
`.claude/`), with use counts, which skills each one points to and is referenced by, duplicate
names flagged, and every file in a skill rendered (`--claude-dir`). "Rejected" is you saying no at the prompt; "denied" is a permission rule or
the auto-mode classifier. Each campaign
has a page (START HERE, waves with issue status and outcomes, decisions, findings, log, git state),
and every file — campaign files and loose plans — is rendered as HTML.

A folder with no MASTER.md yet is shown at its stage instead of as an error: **brainstorm**
(only `DESIGN.md`, from `campaign:brainstorm`: status, verdict, which clarity-checklist sections are
filled in, disagreements, and its `D<n>` decisions) or **audit** (`FINDINGS.md` without a plan).
Both are listed under "Waiting on you" with the next command to run; a brainstorm is placed in the
project whose repo `DESIGN.md` names. Once MASTER.md exists, the campaign page still shows the design
summary and links `DESIGN.md`.

Older campaigns that predate the format show gaps ("unknown" status, no log) instead of failing.
A folder that cannot be parsed gets an error badge; the rest of the site still builds.
