---
name: audit
description: Investigate a codebase against a question (a bug report, a conformance claim, "is this sound?") and write an evidence catalogue FINDINGS.md into ~/.claude/plans/<slug>/, each finding tagged by how it was verified. Optional first step before campaign:plan; skip it when the work is already concrete.
when_to_use: When the user asks to audit, review in depth, or find out what is actually wrong before planning fixes — "audit X", "is the reporter right?", "what's broken in the solver?". Not for a known task list or a clear bug report; go straight to campaign:plan for those.
argument-hint: "[slug] [question or area]"
---

# campaign:audit

Output: `~/.claude/plans/<slug>/FINDINGS.md`, in the format defined in
`${CLAUDE_SKILL_DIR}/../plan/reference/format.md` (read its *Findings* section first),
from the template `${CLAUDE_SKILL_DIR}/../plan/templates/FINDINGS.md`.

Arguments: `$ARGUMENTS`

## 1. Scope

Agree with the user: repo path, the question being asked, the areas in scope, and the `<slug>`.
If there is an originating report, keep it — the catalogue answers it point by point.

## 2. Baseline

Record commit, branch, clean/dirty tree, and date. Run build / tests / lint once in the
foreground and record each result **with its command**.

## 3. Investigate

- Read the code the question is about **and the code the product actually runs**. The most
  valuable finding in past audits was "the tested path is not the production path": trace from
  the entry point (`main`, the public API) rather than from the tests.
- Check the originating report's claims one by one, including which are already fixed.
- Where a finding can be demonstrated, demonstrate it — a command and its output beats a
  reading. Tag each finding with its verification level honestly.
- Test quality is in scope whenever the question touches correctness: check the tests guarding
  each finding against the *Junk patterns* in `${CLAUDE_PLUGIN_ROOT}/skills/test-audit/SKILL.md` (vacuous
  negatives, expected values produced by the code under test, mocks implementing the asserted
  behaviour, test-only seams). "The test passes for the wrong reason" is a finding. If the
  question is itself "are these tests any good / prune them", follow
  `${CLAUDE_PLUGIN_ROOT}/skills/test-audit/reference/pruning-campaign.md` steps 1–4.
- Enumerate. For a pattern ("fabricated defaults"), find every instance with a command and
  list them all; record the command so the count can be re-run.
- Parallel read-only Explore agents per area are fine **if the user asks for parallel work**.
  Cross-check anything they report against source yourself before it goes in the catalogue.

## 4. Write FINDINGS.md

Write FINDINGS.md in STE: follow `${CLAUDE_PLUGIN_ROOT}/skills/ste/SKILL.md` and run its checker on the
file before the handover. Use a Mermaid diagram when a finding is about a path through the code
(for example "the tested path is not the production path"). Any finding about a third-party tool's behaviour cites
the docs or source for the version in use.

- F-ids in order, grouped by area; F0 section for "what the report got right / already fixed".
- A **through-line** section if the findings share a root cause.
- No "and N others".

## 5. Hand over

Summarise for the user: counts by severity, the through-line, and anything that needs their
decision. Suggest `/campaign:plan <slug>` as the next step; do not write issues from this skill.
