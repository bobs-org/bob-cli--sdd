---
create_time: 2026-07-10 12:57:42
status: done
prompt: .sase/sdd/prompts/202607/rename_dataview_to_query.md
---
# Rename `bob dataview` to `bob query`

## Goal

Make `bob query` the public CLI entry point for the existing Dataview source-expression and DQL functionality. Preserve
the command's options, output formats, exit behavior, native/Obsidian engines, and query semantics while updating every
command-facing help, test, smoke-check, and documentation surface.

This is a hard top-level command rename, consistent with the repository's previous command migrations: `bob dataview`
will no longer be registered as an alias, and a regression test will establish that callers receive the normal
unknown-subcommand error and exit code. The README migration notes will direct existing callers to `bob query`.

## Scope boundaries

- Keep Dataview terminology where it names the underlying query language, Obsidian plugin, engine behavior, or data
  model.
- Keep the implementation module and types under `src/native/dataview.rs` and `src/native/dataview/`; this is still a
  Dataview query implementation even though its CLI entry point is `query`.
- Keep `BOB_DATAVIEW_OBSIDIAN_COMMAND`, `BOB_DATAVIEW_VAULT`, the `BOB_DATAVIEW_RESULT` protocol sentinel, Dataview
  error/type names, parity fixture paths, and Dataview-oriented test/module names stable. They describe the
  engine/protocol rather than the top-level command, and renaming them would unnecessarily expand the compatibility
  surface.
- Keep `docs/dataview.md` as the feature-document filename, while changing its title and command examples to
  `bob query`; this avoids unrelated link churn and follows the precedent of retaining implementation/domain-oriented
  filenames during a command rename.
- Do not modify or rename the external `/bob_dataview` skill. No plugin or linked-repository work is needed.
- Do not change query behavior, option names/aliases, output schemas, dependencies, or vault data.

## Implementation plan

1. **Rename and reorder the command registration and native dispatch identity.**
   - In `src/runner.rs`, replace the `dataview` entry in `SUBCOMMANDS` with `query`, preserve its description, map it to
     a command-facing `NativeCommand::Query` variant, and move the entry after `projects` so top-level help remains
     alphabetically sorted as required by the CLI rules.
   - Update the top-level help example from `bob dataview` to `bob query`, ensuring the examples and generated command
     list expose only the new spelling.
   - In `src/native.rs`, rename the dispatch enum variant from `Dataview` to `Query` while continuing to route it to
     `dataview::run`; leave the Dataview implementation module name intact.

2. **Make the delegated command own the new public invocation name.**
   - In `src/native/dataview.rs`, change `COMMAND_NAME` to `bob query`, which updates Clap usage, validation errors,
     warnings, and runtime diagnostics consistently.
   - Update the command's `after_help` examples to invoke `bob query` while retaining accurate Dataview/DQL terminology
     in descriptions and option help.
   - Audit the file for literal old command examples rather than replacing generic `Dataview` identifiers or messages.

3. **Move integration and parity coverage to the new entry point and lock down the migration behavior.**
   - In `tests/cli.rs`, invoke `query` throughout command help, option alias/order, argument validation, native-engine,
     Obsidian-engine, protocol, and error-path tests; update assertions and failure messages that explicitly name the
     public command.
   - Update the all-command help matrix and top-level alphabetical ordering expectation so `query` appears after
     `projects`, and assert that the top-level examples use `bob query` without advertising `bob dataview`.
   - Extend the existing renamed-command regression test so `query --help` succeeds and `dataview --help` is rejected
     with Clap's unknown-subcommand exit behavior. This makes the deliberate absence of a compatibility alias explicit.
   - In `tests/dataview_parity.rs`, change the shared Bob process helpers to invoke `query` and update command-facing
     diagnostics. Retain Dataview parity test/helper names, fixture paths, temp-directory labels, and engine environment
     variables because those identify the feature being tested rather than the CLI spelling.

4. **Update user documentation and packaged smoke surfaces.**
   - Replace executable examples and narrative references to the old command in `README.md` with `bob query`, including
     installation checks, runtime-dependency notes, environment-variable descriptions, the command overview, release
     smoke guidance, and links/context around live Obsidian testing.
   - Add `bob dataview` -> `bob query` to the README migration notes alongside the earlier hard renames, making clear
     that the old top-level name is no longer registered.
   - Update the heading, examples, operational notes, and manual smoke commands in `docs/dataview.md` to present
     `bob query` as the interface while continuing to call the underlying language/plugin Dataview.
   - Update `tests/fixtures/dataview_parity/README.md` so its command-facing description names `bob query` without
     renaming the Dataview parity fixture itself.
   - Update `justfile`'s installed-binary smoke test to exercise `bob query --help`.

5. **Audit the rename boundary and verify the complete CLI contract.**
   - Search tracked files for exact command spellings and registration literals. Any remaining
     `bob dataview`/`"dataview"` command references should be limited to the migration note and the intentional
     unknown-command regression; Dataview engine/domain identifiers should remain unchanged.
   - Run `cargo fmt --check`, `cargo clippy --all-targets --all-features`, `cargo test`, `just check-scripts`, and
     `cargo package --list`.
   - Run `just install-smoke` to verify the packaged binary exposes `bob query --help` after installation.
   - Confirm directly that `bob query --help` renders the complete alphabetized option list with the new usage/examples
     and that `bob dataview --help` exits with code 2 as an unrecognized subcommand.

## Expected files

- `src/runner.rs`
- `src/native.rs`
- `src/native/dataview.rs`
- `tests/cli.rs`
- `tests/dataview_parity.rs`
- `README.md`
- `docs/dataview.md`
- `tests/fixtures/dataview_parity/README.md`
- `justfile`

No Cargo metadata, vault data, linked repository, memory file, or skill file should change.
