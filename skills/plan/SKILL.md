---
name: plan
description: Turn a body of work (audit findings, a plan-mode plan, a bug report, a PR review, a task list) into a campaign plans folder at ~/.claude/plans/<slug>/ — MASTER.md tracker, AGENT_PROMPT.md rules, and one issue file per task, grouped into waves of disjoint files — so the work can be dispatched to agents with campaign:run.
when_to_use: When the user wants to plan multi-issue work for agents to execute, "make a campaign", "split this into issues", "write the master plan and agent prompt", "turn this plan into a campaign" (a plan from Claude Code plan mode in ~/.claude/plans/), or add issues to an existing campaign.
argument-hint: "[slug] [source: plan-mode plan | findings file | issue URL | description]"
---

# campaign:plan

Produce the plans folder described in
[reference/format.md](reference/format.md). **Read that file first** — it is the contract
`campaign:run` and `campaign:audit` rely on. Templates live in `${CLAUDE_SKILL_DIR}/templates/`.
Reference and template files write the folder of this plugin as `<plugin root>`. It is `${CLAUDE_PLUGIN_ROOT}`. When you write
AGENT_PROMPT.md into a campaign, replace `<plugin root>` with that absolute path.

Arguments: `$ARGUMENTS`

## 0. Identify the input and decide whether an audit is needed

- Input is a **plan-mode plan** (a single `~/.claude/plans/<name>.md`, or "the plan we just
  made") → read [reference/from-plan-mode.md](reference/from-plan-mode.md) and follow it
  through steps 1–7. It says how the plan's sections map onto the campaign files and which gaps
  to fill.
- Input is concrete (a clear bug report, a review with line refs, a known task list, an
  existing `FINDINGS.md`) → skip the audit and plan from it.
- Input is a `DESIGN.md` from `campaign:brainstorm` → plan from it. Its *Approach* becomes the
  issues, *Verification* the acceptance criteria, *Scope → Out* the things issues must not do,
  and its open `D<n>` move into MASTER's Decisions with the same numbers. If its status is not
  *agreed* or its verdict is *don't build*, stop and ask the user first.
- Input is "prune / clean up the tests of X" → this is a test-pruning campaign: read
  `${CLAUDE_PLUGIN_ROOT}/skills/test-audit/reference/pruning-campaign.md`; it says which steps belong to
  the audit, plan and run phases.
- Input is an idea that has not been shaped yet ("I want a tool that…", no clear scope or
  success criteria) → suggest `/campaign:brainstorm` first and stop until the user decides.
- Input is a symptom or a vague worry ("this feels broken", "is X conformant?") and nobody knows
  the shape yet → suggest `/campaign:audit` first and stop until the user decides.

## 1. Set up

- Agree the `<slug>` and the ID prefix `<PFX>` with the user.
- `~/.claude/plans/<slug>/` — if it exists, this is an **extension**: read `MASTER.md`, continue
  numbering from the highest existing ID, and do not rewrite existing issues.
- Record the repo's absolute path, branch and commit.

## 2. Environment pre-check

Run every check in the *Environment pre-check* table in `format.md`. Ask the user about
attribution policy and protected paths if the repo does not answer it. The results go into
MASTER's **Dispatch hazards** and decide which run modes `campaign:run` may offer.

## 3. Measure the baseline

Run the gate (fmt / lint / build / tests, whatever the project has) once, in the foreground,
and record each number **with the command that produced it**. Different commands give different
counts for the same tree (`cargo test` vs `cargo nextest run`), and an unlabeled count sends
agents chasing phantom regressions.

## 4. Write the issues

Write every campaign file (issues, MASTER.md, AGENT_PROMPT.md) in STE: follow
`${CLAUDE_PLUGIN_ROOT}/skills/ste/SKILL.md` and run its checker on each file you wrote before the handover.

One file per issue from `templates/ISSUE.md`. For each:
- State the defect, not the task, in the title.
- **Files you may touch** — explicit. This is what makes waves possible.
- **Acceptance criteria** — literal commands with expected results. A criterion that cannot be
  run is a wish.
- Pick the model with the heuristic in `format.md`, and the **Skills:** with its *Skill
  routing* table. Every issue that writes code or config gets `programming`; every issue that
  writes prose (docs, README, PR body, FINDINGS) gets `ste`.
- An issue that touches a third-party tool's config or API names the docs source (URL, or the
  version to look up) in **What to build**, so the agent starts from the docs, not from memory.
- When a criterion needs a new test, run the test-audit authoring gate
  (`${CLAUDE_PLUGIN_ROOT}/skills/test-audit/SKILL.md`) on it now: name the owner boundary and the existing
  test or table it should extend. Do not plan a test at every layer a bug crosses.
- Never "and N others" — enumerate, or give the command.
- Prefer fewer, well-bounded issues. Group mechanical work by file; separate anything with a
  judgement call so it can get opus.

## 5. Waves and decisions

- Group issues so each wave's file sets are disjoint. Ordering constraints go in the wave plan.
- Anything that needs the user's judgement becomes a `D<n>` decision in MASTER, not a guess
  inside an issue.

## 6. Write AGENT_PROMPT.md and MASTER.md

- `AGENT_PROMPT.md` from the template: fill **every** `<placeholder>` (project, gate, baselines,
  spec source, commit/attribution policy, protected paths, conventions, helpers to reuse). Delete
  the options that do not apply. Keep the *Tests you write must pass the test-audit gate* and *Language* rules
  and the *Tests added or changed*, *Docs relied on* and *STE check* report sections. Check for
  leftovers with `command grep -nE '<[^>]+>' AGENT_PROMPT.md | command grep -v '<ISSUE-ID>' || echo clean`
  — only the reporting template's own slots may remain.
- `MASTER.md` from the template: START HERE, wave plan, status table (one line per issue),
  decisions, model policy, dispatch hazards, log.

## 7. Hand over

Show the user: the issue list with model and wave, the open decisions (ask them with
AskUserQuestion), and the safe run modes. Point to `/campaign:run <slug>` as the next step. Do
not dispatch anything from this skill.
