---
create_time: 2026-06-03 12:47:34
status: done
prompt: sdd/prompts/202606/dataview_mvp.md
bead_id: bob-cli-3
tier: epic
---
# Plan: Ambitious MVP for `bob dataview`

## Context

The research conclusion is that there is no official standalone Dataview CLI. For exact Dataview behavior,
`bob dataview` should execute inside a running Obsidian desktop process through Obsidian CLI `eval` and Dataview's
plugin API. `ob` / Obsidian Headless remains useful for sync freshness, but it is not a community-plugin runtime.

Relevant repo constraints:

- New CLI subcommands/options need excellent help, alphabetized listings, and useful color only when appropriate.
- `~/bob` is Bryan's Obsidian vault; `BOB_DIR` already overrides it through `src/native/env.rs`.
- `src/runner.rs` owns the sorted top-level command table.
- Native commands are routed through `src/native.rs`; richer native CLI parsing already exists in
  `src/native/highlights_ref/mod.rs`.
- Existing `ob::sync_vault()` writes sync output to stdout, which would corrupt `dataview` machine-readable output if
  reused directly.
- Automated tests must not require a real Obsidian GUI session; use fake `obsidian`, `ob`, and `dynomark` binaries.

## Target MVP

`bob dataview` should let Bryan run Dataview queries from the shell and print matching notes by default:

```bash
bob dataview --source '#project and -"archive"'
bob dataview --query 'LIST FROM #project WHERE status = "active"'
bob dataview --format json --query-file ~/queries/projects.dql
bob dataview --format markdown --query 'TABLE status FROM #project'
bob dataview --sync --query 'LIST FROM #waiting'
```

Initial command contract:

- `--source <SOURCE>`: run a Dataview source expression via `pagePaths()`.
- `--query <DQL>`: run full Dataview DQL.
- `--query-file <PATH>`: read DQL from a file; `-` reads stdin if implemented.
- `--format paths|json|markdown`: default `paths`.
- `--origin <VAULT_RELATIVE_PATH>`: origin note for `this` and relative links.
- `--bob-dir <PATH>`: vault root for sync and diagnostics; defaults to `BOB_DIR` or `~/bob`.
- `--vault <NAME_OR_ID>`: Obsidian vault name/id passed to the `obsidian` CLI; default should be configurable with an
  env var and documented.
- `--engine obsidian|dynomark`: default `obsidian`; `dynomark` is explicitly a partial-compatibility headless fallback.
- `--sync`: run `ob sync --path <bob-dir>` before querying, with sync logs sent to stderr or otherwise kept out of query
  stdout.
- `--strict-paths`: fail when `paths` output cannot be derived cleanly from a DQL result.

Default `paths` output should be one vault-relative markdown path per line, exit 0 for no matches, and never include
status/log chatter on stdout. JSON output should be stable enough for scripts and include warnings separately from the
result data. Markdown output should pass through Dataview-rendered markdown.

## Phase 1: Command Surface and Native Skeleton

Goal: land the `bob dataview` command shape with strong help, argument validation, test coverage, and no operational
dependency on Obsidian yet.

Work:

- Add `NativeCommand::Dataview`, `mod dataview`, and a sorted `dataview` entry in `src/runner.rs` between `cronjob` and
  `highlights-ref`.
- Implement `src/native/dataview.rs` using clap, following the richer `highlights-ref` style rather than hand-rolled
  parsing.
- Define internal types for query input, format, engine, vault config, and strict/sync flags.
- Enforce mutual exclusion:
  - exactly one of `--source`, `--query`, or `--query-file` for query mode;
  - `--format markdown` requires DQL (`--query`/`--query-file`), not `--source`;
  - `--strict-paths` is meaningful only for `paths` output.
- Add a temporary execution path that exits with a clear "engine not implemented yet" message only when an actual query
  is requested. Help and validation must be complete in this phase.
- Add the command to top-level help examples and install smoke coverage.

Acceptance criteria:

- `bob dataview --help` succeeds, has no ANSI when stdout is piped, and lists options alphabetically.
- Top-level `bob --help` includes `dataview` in sorted subcommand order.
- Invalid combinations return clap-style usage errors without running external commands.
- `BOB_CLI_USE_SCRIPT=1 bob dataview --help` stays native-only and does not extract legacy script assets.
- `cargo fmt --check`, `cargo clippy --all-targets --all-features`, and `cargo test` pass.

Files likely touched:

- `src/runner.rs`
- `src/native.rs`
- `src/native/dataview.rs`
- `tests/cli.rs`
- `justfile`

## Phase 2: Obsidian `eval` Engine and Protocol

Goal: make `--engine obsidian` execute through the real Dataview API, while remaining fully testable with a fake
`obsidian` binary.

Work:

- Add an Obsidian command resolver:
  - `BOB_DATAVIEW_OBSIDIAN_COMMAND` for tests/overrides;
  - fallback to `obsidian` on `PATH`.
- Spawn `obsidian` directly with argv, never via shell. Forward `vault=<NAME_OR_ID>` only when configured.
- Generate JavaScript by embedding a serialized JSON request object rather than interpolating shell-quoted query text.
- JavaScript responsibilities:
  - find `app.plugins.plugins.dataview?.api` or `window.DataviewAPI`;
  - wait for Dataview readiness on cold starts where feasible;
  - run `api.pagePaths(source)` for `--source`;
  - run `api.tryQuery(query, origin, { forceId: true })` for structured DQL;
  - run `api.tryQueryMarkdown(query, origin)` for markdown output;
  - serialize Dataview links/dates/tasks into plain JSON;
  - print exactly one sentinel-prefixed JSON line, e.g. `BOB_DATAVIEW_RESULT\t{...}`.
- Parse the sentinel from stdout so unrelated Obsidian/plugin logging does not become command output.
- Map engine failures clearly:
  - missing `obsidian`;
  - Obsidian not running;
  - Dataview disabled/missing;
  - Dataview query parse/runtime error;
  - missing sentinel or malformed protocol response.

Acceptance criteria:

- Integration tests use a fake `obsidian` executable and verify argv shape, vault forwarding, query JSON embedding,
  sentinel parsing, and error handling.
- No automated test requires a real desktop Obsidian session.
- Query execution returns a typed internal response for source paths, structured DQL JSON, and markdown.
- Engine errors print actionable stderr and exit non-zero without leaking large generated JavaScript blobs.

Files likely touched:

- `src/native/dataview.rs`
- `tests/cli.rs`

## Phase 3: Path Extraction, Output Formats, and Strict Semantics

Goal: turn Dataview engine responses into the three user-facing formats with predictable note matching behavior.

Work:

- Implement `paths` output:
  - source queries print `pagePaths()` results directly;
  - DQL `LIST`/`TABLE`/`TASK` results use forced row identity where available;
  - task rows resolve to source note paths;
  - de-duplicate paths by first appearance while preserving result order;
  - normalize to vault-relative slash paths and ensure `.md` note paths.
- Implement `json` output as a stable object, not raw plugin noise. Include at least:
  - `engine`;
  - `query_kind`;
  - `format`;
  - `paths`;
  - `result` or `rows`;
  - `warnings`.
- Implement `markdown` output by printing the Dataview-rendered markdown only.
- Emit best-effort path warnings to stderr in non-strict mode.
- Make `--strict-paths` fail when a DQL result contains rows that cannot be traced back to note paths, such as
  `WITHOUT ID`, heavy transformations, or grouped/aggregate-only rows.
- Add focused unit tests for path extraction from canned JSON shapes, including lists, tables, tasks, links, groups,
  missing identities, duplicate paths, and weird but valid vault paths.

Acceptance criteria:

- `paths` output is clean one-path-per-line stdout with a trailing newline only when at least one path is printed.
- `json` output is valid JSON and deterministic.
- `markdown` output contains only rendered markdown, with engine warnings/errors on stderr.
- Strict and non-strict behavior is covered by tests.
- Existing command tests keep passing.

Files likely touched:

- `src/native/dataview.rs`
- `tests/cli.rs`

## Phase 4: Vault Freshness, Sync-Safe Output, and Operational Polish

Goal: make the command usable in Bryan's real vault workflow without corrupting scriptable stdout.

Work:

- Implement `--bob-dir` and vault path validation using existing `bob_env::bob_dir()` / tilde expansion patterns.
- Implement `--sync` using shared `ob` discovery and child environment, but do not call the current `ob::sync_vault()`
  in a way that writes to stdout before query results.
- Refactor `src/native/ob.rs` narrowly if needed:
  - preserve existing `cronjob`, `bulk-git-commit`, and `move-done-tasks` stdout behavior;
  - add a variant/helper that returns sync output to the caller or routes it to stderr for `dataview`.
- Define behavior for non-fatal sync states:
  - missing `ob`: warn and continue, or fail only behind a future strict sync flag;
  - already-running sync: warn and continue;
  - real sync failure: exit non-zero before querying.
- Add origin validation:
  - accept vault-relative paths;
  - reject absolute paths and `..` traversal for `--origin`;
  - document that relative links and `this` require an origin.
- Add a lightweight manual smoke-test note in docs or SDD describing how to run the command against a live Obsidian
  session.

Acceptance criteria:

- `--sync --format json` and `--sync --format paths` never mix sync logs into stdout.
- Tests prove fake `ob` calls are made with `sync --path <bob-dir>` and `sync-status --path <bob-dir>` when appropriate.
- Existing sync/cronjob tests remain unchanged in behavior.
- Real-vault manual smoke instructions are explicit about requiring a running desktop Obsidian app for the default
  engine.

Files likely touched:

- `src/native/dataview.rs`
- `src/native/ob.rs`
- `tests/cli.rs`
- possibly `README.md` or `docs/dataview.md`

## Phase 5: Headless `dynomark` Fallback

Goal: provide a useful headless mode for server/cron workflows without claiming full Dataview compatibility.

Work:

- Implement `--engine dynomark`.
- Resolve `dynomark` through `BOB_DATAVIEW_DYNOMARK_COMMAND` then `PATH`.
- Run against `--bob-dir` and capture stdout/stderr.
- Translate supported dynomark output to the same `paths`/`json` contract where possible.
- Clearly reject or warn on unsupported combinations, especially markdown rendering if dynomark cannot match
  Dataview-rendered markdown.
- Label JSON metadata with `engine: "dynomark"` and include a compatibility warning.
- Add tests with a fake `dynomark` executable; do not require dynomark to be installed in CI.

Acceptance criteria:

- `bob dataview --engine dynomark --query ... --format paths` can run in a non-GUI shell with only a fake dynomark in
  tests.
- Unsupported formats fail clearly.
- The default engine remains exact Obsidian/Dataview, not dynomark or silent auto-fallback.
- Documentation states that dynomark is partial compatibility.

Files likely touched:

- `src/native/dataview.rs`
- `tests/cli.rs`
- `README.md` or `docs/dataview.md`

## Phase 6: Documentation, End-to-End Checks, and Release Hardening

Goal: finish the MVP as a polished command rather than a hidden internal tool.

Work:

- Add user-facing docs with examples for:
  - source queries;
  - DQL path output;
  - JSON output for scripts;
  - markdown output;
  - query files;
  - sync behavior;
  - live Obsidian requirement;
  - dynomark limitations.
- Update README command lists if present.
- Add an install-smoke check for `bob dataview --help`.
- Run `just all`.
- If a live Obsidian session is available, perform manual smoke tests against `~/bob`:
  - source query;
  - simple `LIST FROM ...`;
  - `TABLE file.path ... --format json`;
  - markdown query;
  - query file;
  - sync path.
- Capture any real-world incompatibility as a short follow-up note rather than expanding the MVP indefinitely.

Acceptance criteria:

- Docs match implemented flags exactly.
- `just all` passes.
- Manual smoke results are recorded in the final agent response, including when a real Obsidian session was not
  available.
- No generated or intermediate plan files are left unintentionally unless SASE keeps the submitted plan artifact by
  design.

## Cross-Phase Guardrails

- Keep every phase buildable and testable on its own.
- Avoid adding large dependencies unless a phase proves the standard library is inadequate.
- Do not make real Obsidian, `ob`, or `dynomark` required for automated tests.
- Keep stdout sacred: query results only. Put diagnostics, warnings, sync logs, and engine stderr on stderr.
- Preserve top-level subcommand sorting and option sorting.
- Keep the default command behavior exact/fidelity-first through Obsidian; any headless fallback must be explicit.
- Prefer small internal helper functions over broad refactors of existing commands.
- Do not modify memory files.
