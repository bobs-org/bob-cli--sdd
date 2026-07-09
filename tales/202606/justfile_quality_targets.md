---
create_time: 2026-06-02 08:26:11
status: done
prompt: sdd/prompts/202606/justfile_quality_targets.md
---
# Justfile Quality Targets Plan

## Context

This Rust CLI project already has a lowercase `justfile` with these quality-related targets:

- `fmt`: runs `cargo fmt --check`
- `lint`: runs `cargo clippy --all-targets --all-features`
- `test`: runs `cargo test`
- Supporting release checks such as `check-scripts`, `package-list`, and `install-smoke`

The requested change is to make the everyday quality workflow clearer and easier to run by adding a good `all` target
and printing visible headers before each of the `fmt`, `lint`, and `test` command groups.

## Goals

1. Add an `all` target that runs every requested quality target: `fmt`, `lint`, and `test`.
2. Ensure `just all` output is easy to scan by having each component target print a clear section header before running
   its commands.
3. Preserve the current behavior of the individual targets:
   - Formatting remains a check-only operation via `cargo fmt --check`.
   - Linting remains `cargo clippy --all-targets --all-features`.
   - Tests remain `cargo test`.
4. Keep the Justfile idiomatic and small, without expanding the scope into packaging, install smoke tests, or
   release-only validation unless explicitly requested later.

## Proposed Design

Update `justfile` as follows:

- Add `all: fmt lint test` near the top so it runs the requested targets through Just's dependency mechanism.
- Add simple shell `printf` header lines to the beginning of `fmt`, `lint`, and `test`.
- Use explicit labels such as `==> format`, `==> lint`, and `==> test` or similar so that the repeated sections in
  `just all` output are visually separated.
- Leave existing auxiliary targets unchanged.

The target order should be `fmt`, then `lint`, then `test`. This order catches cheap style problems first, then compile
and lint issues, then full test failures.

## Validation

After editing the Justfile:

1. Run `just --list` or `just --summary` to confirm the target graph is valid and `all` exists.
2. Run `just fmt` to verify the header prints and the format check still passes.
3. Run `just lint` to verify the header prints and Clippy still passes.
4. Run `just test` to verify the header prints and tests still pass.
5. Run `just all` to verify the combined output includes the three separated sections in the expected order.

If any validation command fails because of pre-existing code issues, preserve the Justfile change and report the exact
failure rather than broadening the implementation.
