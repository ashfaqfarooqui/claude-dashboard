# <slug> — design brief

**Status:** in progress · **Repo:** `/home/ashfaqf/playground/sdb-cli`
at commit `abc1234` (branch `main`) · **Verdict:** open

## Summary

<One paragraph: the problem, the chosen approach, and the expected result.>

## Problem

Searching a 2 GB dump re-reads it from disk every time; a search took 40 s on 2026-10-01.

## Who and why now

<Who has it, how often, what they do about it today, and why it is worth solving now.>

## Success

- `sdb search foo dump.sdb` returns in under 2 s on the 2 GB dump.

**Failure looks like:** <what would make this not worth having built.>

## Constraints

- <Time, cost, tools and versions, compatibility, things that must not change.>

## Scope

**In:** <…>

**Out (non-goals):** <…>

**Later:** <pieces split off to brainstorm separately, or delete this line.>

## Approach

<The chosen design: the parts, how they connect, what happens when something fails, how it is
tested. Third-party behaviour relied on cites the docs for the version in use.>

## Alternatives considered

| Alternative | Why not |
|---|---|
| Do nothing / use what exists: <…> | <…> |
| <…> | <…> |

## Risks

| Risk (from the pre-mortem) | Mitigation, or "accepted" |
|---|---|
| <…> | <…> |

## Verification

- <How each part of the design is shown to work. Seeds campaign-plan's acceptance criteria.>

## Decisions

- **D1 — Cache on disk or in memory?** Options: disk / memory. Recommendation: disk, because the dump outlives the process. Open.
- **D2 — Watch the file for changes?** Resolved 2026-10-04: no, re-index on demand.

## Disagreements

<!-- Where the brainstorm objected and the user chose otherwise. One line each side. -->

- **Index format.** Objection: a custom format is a second parser to maintain. Chosen: custom, because SQLite is too slow to build.

## Assumptions

- <Things taken as true without checking. Each is a candidate risk.>
