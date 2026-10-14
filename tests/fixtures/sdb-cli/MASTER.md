# sdb-cli — master tracker

Examined: `/home/ashfaqf/playground/sdb-cli` at commit `434853e` (branch `main`, dirty tree).

**Origin.** A broad audit on 2026-09-30 asked what is actually wrong with the repository before
planning fixes. It produced 26 findings (1 Critical, 5 High, 10 Medium, 10 Low), 11 of them
confirmed by running code. This campaign turns them into 17 issues.

Read `FINDINGS.md` for the evidence. Read `AGENT_PROMPT.md` before starting any issue.

> **Path note.** `AGENT_PROMPT.md` lives in this plans directory —
> `/home/ashfaqf/.claude/plans/sdb-cli/AGENT_PROMPT.md` — **not** in the repo. Always give agents absolute paths.

---

## ▶ START HERE

**Status 2026-09-30:** 0 of 17 issues done. Planned, nothing dispatched. Branch `main`, not pushed.

**Before the first dispatch (user action):** the working tree holds 53 files of uncommitted,
non-whitespace changes: the `openscenario-rs` 0.3.2 → 0.5.0 migration and the new
`tests/upload_fetch_roundtrip.rs`. Commit them first, ideally after `cargo fmt`
(`cargo fmt --check` currently fails on `src/operations/download.rs`,
`src/operations/scenario_analyzer/catalogs.rs` and `src/operations/xosc_parser.rs`). Then record
the new commit here as the campaign start and re-run the baselines in `AGENT_PROMPT.md`.

**Next, in order:**
1. Wave 1: SDB-01 first if running serially (it is the Critical and sets up the router test
   harness that SDB-10 reuses), then SDB-03, SDB-04, SDB-05, and the rest of the wave.
2. Wave 2 once SDB-01, SDB-02 and SDB-06 have landed.

**Live hazards:** dirty tree (above). Commit signing is on; a locked key stalls agents.

**Awaiting the user:** commit the migration. D1–D4 are resolved.

---

## The through-line

The security and correctness guarantees live in the docs and in unit tests of helpers, not in the
wiring the server runs. The router attaches authentication only when an API key is set, the
limiter never sees a client address, and the headers layer misses the pages. No test sends a
request through the router. SDB-01 fixes the worst instance and adds the router test harness that
later issues extend.

---

## Wave plan

Issues inside a wave touch disjoint files and may run in parallel. Waves run in order.

### Wave 1 — independent fixes (parallel)
| ID | Title | Sev | Files held |
|---|---|---|---|
| [SDB-01](SDB-01-router-unauthenticated-without-api-key.md) | Routes unauthenticated without an API key | C | `src/web/api/mod.rs`, `src/web/middleware.rs`, `src/web/mod.rs`, `Cargo.toml`, `Cargo.lock` |
| [SDB-02](SDB-02-inline-scripts-block-csp.md) | Inline scripts block the CSP | M | `templates/**` |
| [SDB-03](SDB-03-search-multibyte-panic.md) | Multibyte search qualifier panics | H | `src/search/query.rs` |
| [SDB-04](SDB-04-config-env-ignored.md) | Env vars (incl. `SDB_API_KEY`) ignored | H | `src/config/loading.rs`, `src/config/mod.rs` |
| [SDB-05](SDB-05-web-initialize-clobbers-config.md) | Web initialize clobbers config; file 0644 | H | `src/web/api/config.rs`, `src/cli/init.rs`, `src/util/config.rs` |
| [SDB-06](SDB-06-zip-extraction-unbounded.md) | ZIP extraction unbounded; D3 folder layout | M | `src/operations/upload/zip_handler.rs`, `validation.rs`, `dependencies.rs` |
| [SDB-07](SDB-07-login-enumeration-and-lockout.md) | Login enumeration and permanent lockout | M | `src/web/api/auth_api.rs` |
| [SDB-08](SDB-08-esmini-pipe-deadlock.md) | esmini pipe deadlock | M | `src/operations/video_jobs/generator.rs` |
| [SDB-09](SDB-09-video-job-claiming.md) | Video job claiming, stuck and lost jobs | M | `src/operations/video_jobs/db.rs`, `types.rs`, `src/bin/video_worker.rs` |

### Wave 2 — builds on wave 1 (parallel)
| ID | Title | Sev | Files held |
|---|---|---|---|
| [SDB-10](SDB-10-router-hardening.md) | Rate limiter, page headers, panic layer | H | `src/web/api/mod.rs`, `src/web/mod.rs`, `Cargo.toml`, `Cargo.lock` |
| [SDB-11](SDB-11-duplicate-upload-overwrites-scenario.md) | Duplicate upload overwrites a scenario; one ingest path | H | `src/operations/upload/{mod,content,types,metadata}.rs`, `src/cli/upload.rs`, `src/web/api/upload.rs`, `src/cli/index/{mod,folder_processor}.rs`, `tests/upload_fetch_roundtrip.rs`, `tests/document_building.rs` |
| [SDB-12](SDB-12-unbounded-queries.md) | Search/metrics without time limits; user counts to Viewers | M | `src/web/api/search.rs`, `src/web/api/metrics_api.rs` |

Order constraints: SDB-10 needs SDB-01 and SDB-02; SDB-11 needs SDB-06; SDB-12 needs SDB-01.

### Wave 3 — auth depth and cleanup (parallel)
| ID | Title | Sev | Files held |
|---|---|---|---|
| [SDB-13](SDB-13-jwt-not-revocable.md) | JWTs not revocable; last admin can demote self | M | `src/web/middleware.rs`, `src/web/auth.rs`, `src/web/api/users_api.rs`, `src/web/api/auth_api.rs` (call sites only) |
| [SDB-14](SDB-14-index-clear-deletes-video-dir.md) | `index --clear` deletes the video directory | L | `src/cli/index/mod.rs` |
| [SDB-15](SDB-15-library-prints-to-stdout.md) | Library prints to stdout | L | `src/operations/upload/{mod,validation,dependencies,zip_handler,content}.rs`, `src/operations/download.rs` |

Order constraints: SDB-13 needs SDB-01 and SDB-07; SDB-14 and SDB-15 need SDB-11 (and SDB-15 needs SDB-06).

### Wave 4 — serial
| ID | Title | Sev | Files held |
|---|---|---|---|
| [SDB-16](SDB-16-admin-credentials-and-videos.md) | Admin password in /tmp; `/videos` unauthenticated | M | `src/web/mod.rs`, `src/web/middleware.rs`, `src/web/templates.rs`, `templates/pages/scenario_view.html`, `templates/assets/scripts.js` |

### Wave 5 — serial
| ID | Title | Sev | Files held |
|---|---|---|---|
| [SDB-17](SDB-17-security-docs-out-of-date.md) | Security and deployment docs out of date | M | `docs/security.md`, `docs/api/README.md`, `docs/deployment/*.md`, `docs/guides/user-guide.md` |

---

## Status

| ID | Status | Model | Commit | Outcome |
|---|---|---|---|---|
| SDB-01 | ☐ | opus | | · [doc](SDB-01-router-unauthenticated-without-api-key.md) |
| SDB-02 | ☐ | sonnet | | · [doc](SDB-02-inline-scripts-block-csp.md) |
| SDB-03 | ☐ | sonnet | | · [doc](SDB-03-search-multibyte-panic.md) |
| SDB-04 | ☐ | opus | | · [doc](SDB-04-config-env-ignored.md) |
| SDB-05 | ☐ | opus | | · [doc](SDB-05-web-initialize-clobbers-config.md) |
| SDB-06 | ☐ | opus | | · [doc](SDB-06-zip-extraction-unbounded.md) |
| SDB-07 | ☐ | opus | | · [doc](SDB-07-login-enumeration-and-lockout.md) |
| SDB-08 | ☐ | sonnet | | · [doc](SDB-08-esmini-pipe-deadlock.md) |
| SDB-09 | ☐ | sonnet | | · [doc](SDB-09-video-job-claiming.md) |
| SDB-10 | ☐ | sonnet | | · [doc](SDB-10-router-hardening.md) |
| SDB-11 | ☐ | opus | | · [doc](SDB-11-duplicate-upload-overwrites-scenario.md) |
| SDB-12 | ☐ | sonnet | | · [doc](SDB-12-unbounded-queries.md) |
| SDB-13 | ☐ | opus | | · [doc](SDB-13-jwt-not-revocable.md) |
| SDB-14 | ☐ | sonnet | | · [doc](SDB-14-index-clear-deletes-video-dir.md) |
| SDB-15 | ☐ | sonnet | | · [doc](SDB-15-library-prints-to-stdout.md) |
| SDB-16 | ☐ | opus | | · [doc](SDB-16-admin-credentials-and-videos.md) |
| SDB-17 | ☐ | opus | | · [doc](SDB-17-security-docs-out-of-date.md) |

Legend: ☐ ready · ◐ in progress · ☑ done · ⊘ blocked · ✗ won't fix

---

## Decisions

- **D1 / SDB-01 — Authentication without an API key.** Resolved 2026-09-30: JWT role checks are
  always on; the API key is an optional extra credential; refuse to start on a non-loopback bind
  without `SDB_JWT_SECRET`.
- **D2 / SDB-11 — Scenario identity.** Resolved 2026-09-30: identity is a hash over the whole
  archive content; changed companion files make a new scenario; nothing on disk is overwritten.
- **D3 / SDB-06 — Re-uploading a downloaded ZIP.** Resolved 2026-09-30: upload accepts a ZIP
  whose only top-level entry is one folder; the download layout is unchanged.
- **D4 / SDB-16 — Video access.** Resolved 2026-09-30: `/videos` requires the Viewer role.

---

## Standing constraints

- The campaign start commit is the commit of the pending migration, not `434853e`. Update the
  header and `AGENT_PROMPT.md` baselines once it exists.

---

## Model policy

| Issue | Model | Why |
|---|---|---|
| SDB-01 | opus | Security wiring; a wrong answer is silent |
| SDB-02 | sonnet | Mechanical move; breakage shows in the browser |
| SDB-03 | sonnet | Bounded; regression test fails loudly |
| SDB-04 | opus | Precedence rules; a wrong merge silently drops a secret |
| SDB-05 | opus | Merge semantics across CLI and web |
| SDB-06 | opus | Security limits and D3 |
| SDB-07 | opus | Security behaviour; old tests passed for the wrong reason |
| SDB-08 | sonnet | Bounded; testable with a fake child process |
| SDB-09 | sonnet | Clear target; documented driver semantics |
| SDB-10 | sonnet | Bounded router changes, covered by SDB-01's tests |
| SDB-11 | opus | Identity semantics (D2), cross-cutting refactor |
| SDB-12 | sonnet | Bounded; documented driver options |
| SDB-13 | opus | Auth design |
| SDB-14 | sonnet | Small, bounded |
| SDB-15 | sonnet | Mechanical |
| SDB-16 | opus | Needs a design for authenticating `<video>` requests |
| SDB-17 | opus | Prose in the author's voice, checked against landed code |

---

## Dispatch hazards

Environment pre-check, 2026-09-30:

| Check | Result | Consequence |
|---|---|---|
| Relative path deps | none (`path =` in `Cargo.toml` only names bin sources) | Worktrees can build |
| Other worktrees / sessions | one worktree (`main`) | No bare `stash`; parallel agents in one checkout must not commit concurrently |
| Commit signing | `commit.gpgsign=true` | A locked key stalls agents; they stop and report, never `--no-gpg-sign` |
| Attribution policy | no AI-attribution trailers (session instruction); commit bodies written with `write-technical-like-me` | Encoded in `AGENT_PROMPT.md` |
| Hooks | none in `.git/hooks`, no `.pre-commit-config.yaml` | Nothing to bypass |
| Gate runtime | build 0.4 s warm, tests 3.9 s wall | Run in the foreground |
| Protected paths | `~/.config/sdb-cli/sdb-config.toml` (real config with API key), `target/` | Tests isolate `HOME`; no `cargo clean` |
| Uncommitted work | 53 files of the openscenario-rs migration | **Blocks worktree mode** until committed (worktrees would branch from a tree without it) |
| fmt baseline | `cargo fmt --check` fails in 3 files | Agents check fmt only on files they changed |
| Herdr available | `HERDR_ENV=1` | Herdr mode may be offered |

**Safe run modes:** after the migration is committed: subagent serial, git worktrees (one per
issue within a wave; merge in wave order), or Herdr panes. Before it is committed: none.

---

## Log

- 2026-09-30 — audit written (`FINDINGS.md`, 26 findings).
- 2026-09-30 — D1–D4 resolved by the user.
- 2026-09-30 — campaign planned: 17 issues in 5 waves.
