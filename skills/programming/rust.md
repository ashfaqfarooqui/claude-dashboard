# Rust guidelines

## Environment and build

- Use `cargo` exclusively; `cargo add` / `cargo remove` for dependencies.
- The project's gate (its campaign `AGENT_PROMPT.md`, CI config, pre-push hook or `justfile`)
  decides which commands count. Without one: `cargo build`, `cargo test`,
  `cargo clippy --all-targets`.
- Fix clippy warnings in code you changed. Leave warnings in code you did not touch alone.
- Format only changed files: `rustfmt --edition <edition from Cargo.toml> <files>`. Run
  `cargo fmt` across the workspace only when formatting is the task.
- With several features, pass each as its own flag (`--features a --features b`); coverage
  tooling has silently dropped code when given a comma list.

## Checking docs before use

- Read docs.rs for the exact crate version in `Cargo.lock`, or the vendored source under
  `~/.cargo/registry/src/`. A generic web search finds whichever version is most popular.

## Reuse

- Check `Cargo.toml` for crates already in the tree before adding a new one.
- Prefer the standard library and the project's existing error types and traits over new ones.
- Path dependencies on sibling crates stay relative (`path = "../openscenario-rs"`), never
  absolute.
