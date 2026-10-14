# Test-pruning campaign

Prunes one subsystem's whole test surface (a crate, a package, one core area). It runs as
an ordinary campaign — `campaign:audit` → `campaign:plan` → `campaign:run` over
`~/.claude/plans/<slug>/`, format in `<plugin root>/skills/plan/reference/format.md` —
with the steps below slotted into those phases. The value bar, retention bar, candidate
evidence, and validation in [../SKILL.md](../SKILL.md) apply to every lane. Each step ends
on its completion criterion; do not start the next early.

## Audit phase (`campaign:audit`)

### 1. Baseline

At a pinned commit, record the subsystem's test and test-support line counts
(`tokei`/`wc -l` with the command) and every test's pass/fail state with the gate command.
Keep baseline failures in their own list in `FINDINGS.md` — in openclaw's first campaign
all three were real product bugs, not stale tests.

Done when every in-scope test has a recorded baseline result.

### 2. Lanes

Split the surface into **lanes** along production-owner boundaries (module, parser vs
model vs serialiser, public API vs internals), not file names. Include the subsystem's
cases in shared integration tests, fixture-driven conformance suites, examples, and
doctests.

Done when every test file, integration test, and fixture suite the subsystem owns belongs
to exactly one lane.

### 3. Read-only ledger per lane

One read-only pass per lane (a parallel Explore agent per lane only if the user asked for
parallel work). Read every assigned test in full, including parameter tables and fixture
files, plus the production owner, its entry points, callers, history, and CI routing.
Each test declaration gets one mark and an evidence line; an `#[rstest]` / `parametrize`
table is one declaration unless its rows need different marks.

- `R` retain — name the contract and the bug it catches; a move to a better home stays `R`;
- `F` fix — keep the contract, repair the assertion (e.g. a vacuous negative);
- `C` consolidate — name the owner that absorbs the assertion first;
- `D` delete — name the proof that remains, or why no contract exists.

Judge a test by its assertions, not its name.

The ledger goes into `FINDINGS.md` as one `F<n>` per lane, verification tag
*Confirmed by reading source*, with the mark table inline. Never "and N others".

Done when every declaration in every lane has a mark and an evidence line.

### 4. Layer plan per lane

The ledger is input, not the edit list. A second pass looks for the redundant **layer**:
whole suites replaying a shared helper through a mock around a stronger real-boundary
suite. Name the **keeper** suite per contract. Prefer the real boundary (parse a real
file, round-trip real XML/JSON) over a mocked collaborator. Correct ledger errors found
here.

Done when each lane names its retired files, its keeper per contract, the assertions to
carry into keepers, and the test-only production seams unlocked.

## Plan phase (`campaign:plan`)

### 5. Issues and waves

One issue per lane (or per lane half, if large). **Files you may touch** = the lane's test
files, its keepers, and the production files holding the seams it unlocks. Shared
harnesses, `tests/common/`, `conftest.py`, and fixture helpers get **one owning issue** in
an early wave; later lanes depend on it. Acceptance criteria per issue:

- `<focused test command>` → keepers pass;
- `rg` command showing the retired seam is gone;
- `git diff --numstat` production vs test LOC recorded;
- ledger marks applied: every `D`/`C` row gone or moved, every `F` row repaired.

Model: `opus` for ledger and layer-plan judgement and preservation review; `sonnet` for
applying a finished lane plan (the compiler catches dangling seams).

Put durable test-ownership rules learned here into the repo's `CLAUDE.md` /
`CONTRIBUTING.md` as a final issue — drawn only from mistakes this campaign found.

## Run phase (`campaign:run`)

### 6. Cutover

Dispatch lane issues wave by wave. With each lane, remove the test-only seams it unlocks
(`pub` widenings, `#[cfg(test)]` accessors, injection parameters, reset functions,
indirection layers). Update CI routing if suites moved.

Done when every lane plan is applied and each lane's keepers pass.

### 7. Preservation review

Before calling the campaign done, add one review issue per boundary group (model `opus`,
read-only): compare deleted coverage against keepers, looking for contracts that lost
their only proof, and for new assertions that cannot fail (a rejection row the code never
reaches). openclaw's first review found nine real gaps and one unreachable assertion.

For each restored contract, make one deliberate **mutation** of the production owner,
confirm the keeper goes red, then restore the source byte for byte (`git diff` empty).
Record the mutation and the red output in the issue's Outcome.

Done when every reported gap is restored or rejected with source evidence, and every
restored contract has a caught mutation.

### 8. Product defects

A baseline failure that survives into a keeper is a bug: a new issue (`**Raised by:**`),
fixed at its owner in its own commit, proven with a **control** run that reverts the fix
and shows the old behaviour. Unrelated discrepancies become follow-up issues, not
campaign fixes.

Done when each repaired defect has a failing control and a passing candidate on the same
harness.

### 9. Reconcile and hand off

Long campaigns outlive many `main` commits. Merge `main` rather than rebasing. When `main`
modified a file the campaign deleted, keep the deletion and port the new contract into the
keeper; confirm every regression `main` added still has a home. Rerun the whole subsystem
gate on the merged head.

Hand off with the SKILL.md report, plus:

- baseline and final test/support line counts, production counted separately;
- lanes, retired layers, and keepers;
- preservation gaps found and their mutations;
- product defects with control and candidate proof.
