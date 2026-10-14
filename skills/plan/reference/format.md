# Campaign format — the shared contract

`campaign:brainstorm`, `campaign:audit`, `campaign:plan` and `campaign:run` talk to each other
only through the files described here. Any of them can be used alone, so this file is the whole interface.

Worked examples (real, large, read them when in doubt):
- `~/.claude/plans/openscenario-rs/` — prefix `OSR`, spec-conformance campaign
- `~/.claude/plans/scenario-weaver/` — prefix `SW`, soundness campaign. Its `MASTER.md` (165k) is
  the example of what the size rules below exist to prevent.

---

## Language

Every campaign file is written in Simplified Technical English (ASD-STE100), about 80 % of the
way: DESIGN.md, FINDINGS.md, MASTER.md, AGENT_PROMPT.md, issues, Outcome appendices and agent
reports. So are the docs, READMEs, PR bodies and commit messages that campaign agents write.
The rules and the checker are in `<plugin root>/skills/ste/SKILL.md`. Campaigns do not use the
`write-like-me`, `write-technical-like-me` or `voice-rubric` skills.

## Layout

```
~/.claude/plans/<slug>/
  MASTER.md          tracker — the entry point for every session
  AGENT_PROMPT.md    rules every task agent follows; single source of truth
  DESIGN.md          design brief (optional — only if there was a brainstorm)
  FINDINGS.md        evidence catalogue (optional — only if there was an audit)
  assets/            images the plan files link to (optional)
  <PFX>-NN-<slug>.md one issue per file
  ARCHIVE.md         old MASTER sections moved out (created when needed)
```

- `<slug>`: kebab-case project name (`openscenario-rs`).
- `<PFX>`: 2–4 uppercase letters (`OSR`, `SW`). IDs are `<PFX>-NN`, zero-padded, never reused.
  A file covering several IDs is named `<PFX>-43-44-<slug>.md`.
- The folder lives **outside the repo**. Every reference handed to an agent is an **absolute
  path** — agents told "read AGENT_PROMPT.md" have gone looking in the repo root and reported the
  paperwork missing.

## Design brief — `DESIGN.md`

Written by `campaign:brainstorm`. Template: `templates/DESIGN.md`.

- Header states status (in progress / agreed + date), repo path and commit if there is a repo,
  and the verdict (build / build smaller / don't build / open).
- One section per clarity-checklist item: Problem, Who and why now, Success, Constraints, Scope,
  Approach, Risks, Verification. Plus *Alternatives considered*, *Decisions*, *Disagreements*
  and *Assumptions*.
- Nothing open is left as "TBD" in prose: it is a `D<n>` with options and a recommendation.
  `campaign:plan` carries open `D<n>` into MASTER with the same numbers.
- *Disagreements* records where the brainstorm objected and the user chose otherwise. It stays
  in the file even when empty.
- *Verification* seeds the issues' acceptance criteria; *Alternatives considered* stops a later
  agent from re-proposing a rejected design.
- Diagrams are Mermaid blocks; images live in `assets/` and are linked relatively. Each one has
  one or two sentences under it that say what it shows. The dashboard renders both.

## Findings — `FINDINGS.md`

- ID `F<n>`, never renumbered. Heading:
  `### F<n> (<C|H|M|L>) — <title>. *<verification>*`
  where verification is one of **Confirmed by running**, **Confirmed by reading source**,
  **Inspection-only / unverified**.
- Header of the file states the commit, branch, clean/dirty tree, and date the line refs were
  verified at.
- Evidence is `file:line` plus a quoted excerpt or the command and its output.
- **Never write "and N others" / "~8 more".** List every instance, or give the command that
  lists them. That phrasing caused two coverage gaps and three agents of rework in OSR.
- Findings raised later are appended with a date and the issue that raised them.

## Issue — `<PFX>-NN-<slug>.md`

Template: `templates/ISSUE.md`. Required parts, in order:

1. Title: `# <PFX>-NN — <what is wrong, stated as the defect>`
2. Header line: `**Severity:** · **Model:** · **Skills:** · **Depends on:** · **Findings:**` (plus
   `**Raised by:**` for issues found during the campaign, and `**Status:**` only if it is not
   plain "ready").
3. `## Why this exists` — the problem and the evidence, short.
4. `## What to build` — the target state, numbered steps if order matters. Say what **not** to
   do where a tempting wrong fix exists.
5. `## Files you may touch` — explicit list, or an explicitly stated rule
   ("whatever the compiler points you at, except X").
6. `## Acceptance criteria` — checkboxes, each a **literal command with the expected result**.
   Baselines name the command that produced them. A criterion that demands a new test names
   the owner boundary it belongs at and requires the fails-before evidence; it must pass the
   authoring gate in `<plugin root>/skills/test-audit/SKILL.md`.
7. `## Notes` (optional).
8. `## Outcome (<date>, <commit>)` — appended by `campaign:run` when it lands. Dated appendices
   are part of the issue; agents must read the issue **to the bottom**.

## Model heuristic

| Model | Use when |
|---|---|
| haiku | Mechanical, fully specified, no judgement. The acceptance criteria are the whole spec. |
| sonnet | Bounded change with a clear target, where a mistake is loud (compiler, failing test). |
| opus | A judgement call against a spec, a cross-cutting design, or anywhere a wrong answer is **silent**. |

Rules of thumb: *"read the spec and decide"* → opus. *"If `build` would catch the mistake,
sonnet is enough."* If the safety net is a test the agent must write first, it is not enough.

## Skill routing

A task agent loads no skill on its own: it follows a skill only if its issue names it. Every
issue header lists the skills the work needs under **Skills:**, by short name; `AGENT_PROMPT.md`
maps each name to its absolute path and tells the agent to read those files first.

| Kind of work | Skills |
|---|---|
| Code or tool config (Rust, Python, shell, Nix, CI, dotfiles) | `programming` (pulls in `test-audit` for tests) |
| Any prose: docs, READMEs, PR bodies, FINDINGS, decks, notes | `ste` |
| Anything written into the Obsidian vault | `vault` (plus the voice skill for the prose) |
| Pruning or auditing tests | `test-audit` |

An issue that changes code and docs lists both rows. `none` is a valid value for purely
mechanical issues (renames, moves).

## Waves

Issues in the same wave touch **disjoint files** and may run in parallel. Issues in different
waves must not. Every wave table lists the files each issue holds, so collisions are visible.

## Decisions — `D<n>`

Open questions the user must settle, recorded in `MASTER.md`. **A decision beats the issue doc
it contradicts**, and that issue doc gets a one-line pointer to the decision at the top so an
agent handed only the issue still sees it.

## `MASTER.md` sections and size rules

Template: `templates/MASTER.md`. Sections, in order:

| Section | Rule |
|---|---|
| Title + audit line | Repo path, commit, branch, one-paragraph origin. |
| Path note | Absolute path of `AGENT_PROMPT.md`. |
| **▶ START HERE** | **≤ ~40 lines. Overwritten each session, never appended.** State, next steps, live hazards. |
| The through-line | The common root cause, if there is one. Short. |
| Wave plan | Tables: ID, title, severity, files held. |
| Status | **One line per issue.** `ID \| status \| model \| commit \| one-line outcome · [doc](file)` |
| Decisions | D1… with the resolution and date. |
| Standing constraints | Things every agent must obey that are not yet in `AGENT_PROMPT.md`. Should trend to empty — move them into `AGENT_PROMPT.md`. |
| Model policy | Per-issue model table. |
| Dispatch hazards | Result of the environment pre-check; which run modes are safe and why. |
| Log | **One dated line per event.** Narrative belongs in the issue's Outcome appendix. |

Status legend: `☐` ready · `◐` in progress · `☑` done · `⊘` blocked · `✗` won't fix.

When `MASTER.md` exceeds ~30 KB, move the oldest Log lines and any stray narrative sections to
`ARCHIVE.md`, leaving a one-line pointer.

## `AGENT_PROMPT.md`

Template: `templates/AGENT_PROMPT.md`. It is the **single source of truth** for how a task
agent behaves. If a dispatch would need to say "ignore rule X in AGENT_PROMPT.md", fix
`AGENT_PROMPT.md` first instead. In SW, a stale attribution rule had to be countermanded in
every dispatch, and one forgotten countermand is a wrong commit.

## Environment pre-check

Run by `campaign:plan`, re-checked by `campaign:run`, recorded under *Dispatch hazards*:

| Check | How | Why it matters |
|---|---|---|
| Relative path deps | `grep -nE 'path *=' Cargo.toml`, `file:`/`link:` in `package.json`, `-e ../` in requirements, `replace ../` in `go.mod` | A worktree elsewhere cannot resolve them → worktree mode unsafe |
| Other live worktrees / sessions | `git worktree list` | Shared index → no bare `stash`, no parallel commits in one checkout |
| Commit signing | `git config --get commit.gpgsign` | A locked key stalls agents; they must stop, not pass `--no-gpg-sign` |
| Attribution policy | Ask the user; check existing `git log` | Differs per repo |
| Hooks | `ls .git/hooks`, `.pre-commit-config.yaml` | Agents must not `--no-verify` |
| Gate runtime | Time the gate once | Long gates get backgrounded and polled forever — say "run in the foreground" |
| Protected paths | Ask; look for irreplaceable files in ignored dirs | e.g. OSR's only copy of a ledger lived under `target/` → no `cargo clean` |
| Herdr available | `test "${HERDR_ENV:-}" = 1` | Herdr mode only offered inside Herdr |
| Usage limit | Ask the user; default 80 | `campaign:run` reads `scripts/usage.py` before each dispatch and stops at this 5-hour % |
