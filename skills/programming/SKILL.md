---
name: programming
description: Engineering rules for writing, editing or reviewing code and tool configuration — Python, Rust, shell, and config for third-party tools (Nix, Hyprland, Zola, systemd, CI). Covers reading the official docs for the pinned version before relying on an API or option, keeping changes to the requested scope, reusing existing code, proving a change with a real check, and tests that pass the test-audit gate. Use for any code or config change, including changes made by campaign agents.
---

# Programming

Language specifics: [python.md](python.md), [rust.md](rust.md). Tests:
`${CLAUDE_PLUGIN_ROOT}/skills/test-audit/SKILL.md`.

## Before writing

1. **Read before you claim.** Never describe or change code you have not opened. Read the
   function, its callers and its tests before editing it.
2. **Docs first for anything third-party** — a library, CLI, config format, or system option.
   Fetch the official docs or source for the version actually in use (lockfile, `Cargo.lock`,
   `flake.lock`, `--version`) and cite the option or API you rely on, with its URL or
   `file:line`, in your report. Never infer an option name from memory or from other config in
   the repo; versions drift. If the docs and the observed behaviour disagree, run the tool and
   trust the output.
3. **Look for what exists.** Search the codebase for a helper, type or dependency that already
   does the job before writing a new one, and extend it instead of duplicating it.

## While writing

4. **Deliver the requested scope, no more.** A bug fix does not need the surrounding code tidied.
   No features, refactors, docs, comments or config knobs nobody asked for; if one would help,
   say so at the end instead of doing it.
5. **Minimum complexity.** No abstractions for one call site, no parameters nothing passes, no
   error handling for states that cannot happen. Validate at system boundaries (user input,
   files, network, external tools) and trust internal guarantees.
6. **Solve the problem, not the test.** Implement logic that is right for every valid input.
   Never special-case test inputs or hard-code expected values. If a test looks wrong, say so;
   do not weaken it.
7. **Format only what you touched.** Run the formatter on changed files (`rustfmt <files>`,
   `ruff format <files>`), never across the whole workspace — unrelated reformatting buries the
   real diff.

## Before reporting done

8. **Prove it with a real check.** Run something that exercises the change: the project's tests,
   type-checker or build, or the changed command itself. A syntax check, or a check that failed
   to start, does not count. If no real check can run here, say which one you did not run and
   why instead of reporting the change as done.
9. **Tests pass the test-audit gate.** Every new or changed test answers the four authoring
   questions and matches none of the junk patterns in `${CLAUDE_PLUGIN_ROOT}/skills/test-audit/SKILL.md`.
   A regression test is shown failing on the pre-fix code; a mutation used as that proof
   changes **production** code, and `git diff --stat` confirms it applied.
10. **Leave no litter.** Delete scratch scripts and temporary files you created, unless the user
    asked to keep them.

## Shell habits

- Interactive aliases exist on this machine (`ls` → eza, `grep` → ugrep, `tr` → trash-restore).
  In scripts, counts and pipelines use `command ls`, `command grep`, `command tr`.
- Run long builds and test suites in the foreground and wait. Never poll with `sleep`; a
  background job notifies when it finishes.
- A command whose "no match" exit code is 1 (`grep`) is not a failure: write
  `grep … || echo none` when no output is the good outcome.
