# SDB-03 — A simple search qualifier that starts with a multibyte character panics the handler

**Severity:** High · **Model:** sonnet (bounded; the regression test fails loudly) ·
**Depends on:** none · **Findings:** F12

## Why this exists

`format_simple_search` (`src/search/query.rs:28-29`) slices with byte indices
`&sub_token[0..1]` / `&sub_token[1..]`. The token `"speed é5"` panics at `query.rs:28:34`
(confirmed by running). Any Viewer can trigger this through `POST /api/search`.

## What to build

Split the first character with `chars()` / `char_indices()` (or `split_at(c.len_utf8())`). A
qualifier whose first character is not `=`, `<` or `>` must return the existing
"Unable to parse" error, not panic. Keep the existing error texts.

Add the regression case to the existing tests of `format_simple_search`, if any; otherwise add
one table-driven test in `src/search/query.rs` covering `"speed é5"` → `Err`, `"speed >5"` → `Ok`.

Do not add a catch-all `catch_unwind`; the router-level panic layer is SDB-10.

## Files you may touch

- `src/search/query.rs`

If a fix needs a file outside this list, stop and report why.

## Acceptance criteria

- [ ] The new test fails on the pre-fix code with `byte index 1 is not a char boundary` (capture it).
- [ ] `cargo test --lib search::query` → passes.
- [ ] Gate green.
