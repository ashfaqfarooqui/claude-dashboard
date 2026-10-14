---
name: run
description: Orchestrate a campaign plans folder at ~/.claude/plans/<slug>/ — resume from MASTER.md, pick the next issues, let the user choose how to run them (in-session subagents, git worktrees, or Herdr panes), dispatch with AGENT_PROMPT.md, verify each result independently, and record outcomes back into the plan files.
when_to_use: When the user wants to continue or execute a planned campaign, or asks about one — "continue openscenario-rs", "run the next wave", "dispatch SW-57", "where were we on <project>?", "what's left, give me a table", "explain OSR-12 in plain terms".
argument-hint: "[slug] [issue IDs | 'next' | 'status' | 'explain <ID>'] [max-usage=<5h %>]"
---

# campaign:run

The plan files follow `${CLAUDE_SKILL_DIR}/../plan/reference/format.md` — read it
if the folder is unfamiliar. Run modes: [reference/run-modes.md](reference/run-modes.md).
Dispatch prompt: [reference/dispatch-prompt.md](reference/dispatch-prompt.md). Report formats:
[reference/reports.md](reference/reports.md).
Reference and template files write the folder of this plugin as `<plugin root>`. It is `${CLAUDE_PLUGIN_ROOT}`.

Arguments: `$ARGUMENTS`
- `status` → step 1, then the *status* report from reports.md. No dispatch.
- `explain <ID>` → the *explain* report from reports.md. No dispatch.
- `max-usage=<n>` → the 5-hour usage at which the usage gate stops dispatching (default 80, or
  the value recorded under MASTER's Dispatch hazards). "Stop at 70%" in plain words means the same.

## Usage gate

Subagents draw on the same 5-hour and 7-day limits as this session. Before proposing work and
before **every** dispatch, run:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/usage.py --max <max-usage>
```

| Exit | Meaning | Do |
|---|---|---|
| 0 `go` | headroom | Dispatch as planned. |
| 1 `caution` | within 20 points of the limit | Dispatch only haiku/sonnet issues; hold opus issues and say so. |
| 2 `stop` | at the limit (5-hour) or 7-day ≥ 95% | Dispatch nothing new. Let running agents finish, verify and record them, overwrite START HERE with what is next and when the window resets, and stop. |
| 3 `unknown` | no or stale snapshot | Tell the user the reading is unavailable and ask before dispatching. |

The snapshot comes from the status line (`~/.claude/statusline-command.sh` writes
`~/.cache/claude-usage.json`). Put the printed line in each dispatch's Log entry. Never switch
an issue to a cheaper model than its header names to save usage; hold it instead, and offer the
user the choice.

## 1. Resume

- Read `~/.claude/plans/<slug>/MASTER.md`: START HERE, Status, Decisions, Dispatch hazards.
- Check the record against reality: `git -C <repo> log --oneline` for the commits the status
  table claims, `git status` for uncommitted work. Report any disagreement before acting on it.
- If `AGENT_PROMPT.md` still has `<placeholders>`, stop and fix that first.
- Campaigns planned before the template grew a section are migrated, not worked around. If
  `AGENT_PROMPT.md` lacks any of these, copy it in from
  `${CLAUDE_SKILL_DIR}/../plan/templates/AGENT_PROMPT.md`, tell the user, and log it:
  the *Skills*, *Language* and *Third-party tools: docs first* rules, the *Tests you write
  must pass the test-audit gate* rule, and the *Tests added or changed*, *Docs relied on* and
  *STE check* report sections. Campaigns that still route prose to `write-technical-like-me`,
  `write-like-me` or `voice-rubric` change to `ste`: in the *Skills* table of `AGENT_PROMPT.md`,
  in the *Voice check* report section (it becomes *STE check*), and in the **Skills:** line of
  each issue that is not done.
- Issues without a **Skills:** line get one from the *Skill routing* table in `format.md`
  before they are dispatched.

## 2. Pick the work

Run the usage gate. Propose the next issue(s) as the *status* report's table, limited to the
eligible ones: ready (`☐`), dependencies done, no open decision blocking them, allowed by the
gate, and — for more than one — in the same wave with disjoint file sets. Read each chosen issue
**to the bottom**. Confirm the set with the user.

## 3. Choose the run mode — the user decides

Re-run the pre-checks from run-modes.md (they may have changed since planning), then ask with
AskUserQuestion. Offer each mode with its pre-check result in the description; mark a mode
unsafe rather than hiding it, and say why. Recommend **subagent (serial)** unless the user asked
for parallelism and the checks allow it.

## 4. Dispatch

Build each prompt from dispatch-prompt.md: absolute paths, the model from the issue header,
and any decision (`D<n>`) that overrides the doc. If you notice you are about to write "ignore
X in AGENT_PROMPT.md", edit `AGENT_PROMPT.md` instead and dispatch without the override.

Run the usage gate again immediately before each dispatch; earlier agents may have used the
headroom. Mark the issue `◐` in the status table before dispatching. Then follow the mode's
recipe.

## 5. Verify independently

An agent's report is a claim. For each finished issue:
- `git show --stat <commit>` — changes stayed inside **Files you may touch** (or the deviation
  was reported and is justified).
- Re-run the acceptance commands yourself, **in the foreground** (all of them if cheap, a
  targeted subset otherwise, and say which).
- Every test the commit adds or changes (`git show <commit> -- '*test*' 'tests/'`, plus
  `#[cfg(test)]` / `#[test]` hunks in `src/`) passes the test-audit authoring gate
  (`${CLAUDE_PLUGIN_ROOT}/skills/test-audit/SKILL.md`): the report gives the four answers, it matches no
  junk pattern, and it adds no test-only production seam. For a regression test, confirm the
  fails-before evidence yourself when cheap — check out the parent's version of the fixed
  source in a scratch worktree (`git worktree add <scratchpad>/verify <commit>~1`, copy the new
  test in, run it, then `git worktree remove`) or mutate the fix, see red, restore byte for
  byte. A test that cannot go red is a failed criterion.
- Prose the issue wrote (docs, README, PR body) has an STE check result in the report; run
  `python3 ${CLAUDE_PLUGIN_ROOT}/skills/ste/scripts/ste_check.py` on it yourself. Third-party options the change
  relies on are cited under *Docs relied on*.
- Commit message matches the policy (prefix, attribution rule, signed if required).
- If anything fails, do not record it as done: send it back to the agent (SendMessage / Herdr
  prompt) or report to the user.

## 6. Record

- Status row → `☑`, commit hash, one-line outcome.
- Append `## Outcome (<date>, <commit>)` to the **issue file** with the report's substance —
  changed files, before/after numbers, questions decided, notes for the next agent. MASTER gets
  no narrative.
- Every *Out of scope, found anyway* item → a new issue file (next free ID, `**Raised by:**`),
  a status row, and a mention to the user. Findings worth keeping → append to `FINDINGS.md`.
- A lesson every future agent needs → a rule in `AGENT_PROMPT.md`, not a note in the dispatch.
- Baselines moved → update them in `AGENT_PROMPT.md` with the command.
- One dated line in MASTER's Log, ending with the usage gate's line.
- **Overwrite** START HERE: state, next steps, live hazards, what awaits the user.
- If `MASTER.md` > ~30 KB, move old material to `ARCHIVE.md`.

## 7. Continue or stop

Continue with the next issues only if the user asked for more than one round, and only while
the usage gate allows it. Never push,
merge to a shared branch, or unlock signing on the user's behalf — list those under
"Awaiting the user" in START HERE.
