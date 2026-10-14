---
name: test-audit
description: Value bar for tests. Authoring gate every new or changed test must pass, plus an audit workflow for low-value, implementation-coupled, or duplicative tests and the test-only production seams they keep alive. Rust and Python.
when_to_use: Whenever writing, changing, reviewing, or sweeping tests — including tests written by campaign agents and regression tests named in acceptance criteria. "audit the tests", "are these tests any good?", "prune the test suite", "write a regression test for X".
argument-hint: "[author | audit <path> | campaign <slug> <subsystem>]"
---

# Test Audit

Adapted from openclaw's `.agents/skills/test-audit` (Rust/Python, campaign-folder workflow).

Three modes, one value bar.

Reference and template files write the folder of this plugin as `<plugin root>`. It is `${CLAUDE_PLUGIN_ROOT}`.

- **Authoring** gates every new or changed test at write time. It applies to all
  programming work, and every campaign agent follows it (`AGENT_PROMPT.md` points here).
- **Audit** runs a focused sweep for tests that re-assert source, duplicate stronger
  proof, couple to implementation, or keep test-only production seams alive. Prefer a few
  high-confidence candidates over a large speculative inventory; optimise for confidence,
  not deletion count.
- **Campaign** prunes one subsystem's whole test surface as a campaign
  (`~/.claude/plans/<slug>/`). Read [reference/pruning-campaign.md](reference/pruning-campaign.md)
  first.

Arguments: `$ARGUMENTS`

## Authoring gate

Before adding or changing a test, answer four questions. A missing answer means do not add
it yet.

1. What observable behaviour, invariant, or independent contract does it protect?
2. What credible regression makes it fail?
3. Why does existing coverage not already catch that failure? Each contract has **one
   primary test owner** at the strongest boundary; another layer needs its own distinct
   risk (e.g. a parse/serialise round-trip the unit owner cannot reach). Prefer adding a
   row to an existing table-driven test (`#[rstest]` case, `pytest.mark.parametrize`, a
   fixture-directory loop) over a near-duplicate test. Consolidate duplicated setup in the
   same change.
4. Does it need a production seam — a `pub` / `pub(crate)` that exists only for tests, a
   feature flag, a `#[cfg(test)]` accessor on a production type, an injection parameter,
   a module-level global to monkeypatch — that no production caller needs? If yes, move the
   test to the real boundary instead.

Then check it against every [junk pattern](#junk-patterns). A match fails the gate unless
the [retention bar](#retention-bar) names the contract it independently guards. A test
that would break under a behaviour-preserving refactor asserts implementation, not
behaviour; rewrite it at the owning boundary before landing it.

**Regression tests must fail on the pre-fix code for the intended reason** and pass after
the repair at the owner boundary. Prove it: run the test against the unfixed code (write
the test first, or temporarily revert the fix with a WIP commit — never `git stash` /
`git checkout --` in a shared checkout) and record the failing output. A regression test
that never demonstrably failed proves the mock, not the fix. One regression at the owner
boundary covers the bug; do not replay the same scenario at every layer it crosses.

When reporting (a campaign report, a PR description, the final message), give the four
answers in one line per new test, plus the pre-fix failure for regression tests.

## Junk patterns

The shared checklist: the authoring gate rejects a new test that matches one, and audits
hunt for existing tests that do.

- assertion-free coverage probes (a test that only calls the function; `let _ = f();`,
  `assert!(true)`, `is_ok()` on something that cannot fail);
- self-comparisons and identity copiers (`assert_eq!(x.clone(), x)`, round-tripping a
  value through a function that is the identity);
- copied fixtures, inventories, manifests, or export lists (a test that restates the
  variant list, the schema's element list, or `__all__`);
- exact source, import, or string greps over the codebase;
- private-helper or call-shape tests duplicated by a test at the real boundary;
- duplicate invocations of the same contract;
- per-module replays of a shared helper's tests;
- tests whose only purpose is keeping a test-only export, global, or wrapper alive;
- dead production code whose only callers are tests;
- expected values produced by the function or serialiser under test (snapshot or golden
  files regenerated from the code and never reviewed against the spec count here);
- mocks that implement the asserted behaviour, or one mock standing in for different APIs;
- fixtures that supply the ordering, IDs, or resolved references the code under test
  should produce, or persistence asserted against a store the path never writes;
- capability tests that restate declared flags or trait impls instead of exercising the
  behaviour they promise;
- negative controls that pass for an unrelated reason: an error from a different
  validator, a parse failure before the branch under test, a `should_panic` with no
  `expected =` message, `pytest.raises(Exception)` with no `match=`;
- names or fixtures that promise more than the input exercises (a "rejects invalid
  ranges" test whose only input is valid).

## Value bar

Tests justify their maintenance cost by protecting behaviour, a credible regression, or an
independently meaningful contract. In an audit, an existing test that must change for a
behaviour-preserving reorganisation is suspect, not automatically deletable; the authoring
gate still rejects new ones.

Before judging a candidate, read the complete test and its production owner, the entry
point, callers, callees, sibling implementations, overlapping tests, which CI job runs it,
and relevant history (`git log -L` / `git log -S`). Read root and scoped `CLAUDE.md` /
`CONTRIBUTING.md` first. When the test claims dependency-backed behaviour, read the
dependency's source or docs for the pinned version (docs.rs, the pinned wheel).

## Retention bar

Keep a test when it independently enforces a public API, spec/schema conformance, file
format or wire compatibility, config, migration, error message a user sees, security,
platform, default value, cross-language binding, packaging, release, or architecture
contract. Also keep:

- call ordering when order is observable behaviour;
- regressions with a credible failure mode;
- source inspection when it is the cheapest independent guard: it fails when the contract
  changes (the user-facing key, byte, or path) and survives an identifier-only refactor;
- a retained test that fails on the baseline: treat it as a possible product bug,
  reproduce it, and repair the owner rather than deleting it.

Static or slow is not a deletion reason. A test that resembles implementation may still be
the independent contract; prove otherwise before removing it.

## Discovery (audit mode)

Keep discovery read-only and report evidence before editing. For broad scope, split by
production owner (crate / package / module), plus one cross-cutting pattern sweep. Record
the command behind every pattern count so it can be re-run, e.g.:

```
rg -n 'should_panic\]$' --type rust            # panics with no expected message
rg -n 'pytest.raises\((Exception|BaseException)\)' --type py
rg -n '#\[cfg\(test\)\]' --type rust -g '!**/tests/**'   # test-only seams in src
```

Parallel read-only agents per owner are fine **if the user asks for parallel work**;
cross-check their candidates against source yourself.

## Candidate evidence

Record every field before editing. A missing field means the candidate is not ready for
deletion:

- exact test name and `file:line`;
- what failure it can actually detect;
- non-test callers of the covered production or support seam;
- stronger remaining owner-boundary proof, or why no proof is needed;
- relevant history and the reason the test or seam exists;
- production or test-support deletion it unlocks;
- risk and the focused validation command.

## Edit shape

One coherent owner-boundary batch per commit. Delete obsolete test-only exports, `pub`
widenings, `#[cfg(test)]` accessors, globals, wrappers, and dead production paths instead
of keeping aliases. Move retained regressions to their canonical owner. Consolidate
repeated assertions into one table-driven contract.

Prefer net-negative production LOC. Do not add replacement tests that restate the same
implementation, and do not convert uncertain candidates into deletions to raise the count.

## Validation

Run in the foreground; do not edit while a test run is in progress.

1. Smallest owner and sibling tests: `cargo test -p <crate> <filter>` (or
   `cargo nextest run -p <crate> -E 'test(<filter>)'` if the project uses nextest);
   `uv run pytest <path>::<name>`.
2. For a removed grep or manifest assertion, run the script or build step that owns the
   real contract.
3. `cargo fmt --check` / `cargo clippy --all-targets` or `uv run ruff check`, then
   `git diff --check`.
4. The project's full gate as `CLAUDE.md` / `CONTRIBUTING.md` / the campaign's
   `AGENT_PROMPT.md` defines it. Record test counts **with the command** — `cargo test`
   and `cargo nextest run` count differently.
5. `git diff --numstat`; report production/tooling LOC separately from tests and support.
6. Run `/code-review` on the diff before handing off.

## Landing

Commit, push, or open a PR only when authorised. In a campaign, follow `AGENT_PROMPT.md`'s
commit rules. Land one coherent batch at a time, then rerun read-only discovery for the
next one.

## Handoff

Report:

- root cause and the low-value categories removed;
- production simplifications (seams deleted);
- retained false positives and why they remain valuable;
- focused and full proof actually run, with commands;
- production versus test LOC;
- named follow-ups (in a campaign: *Out of scope, found anyway*).
