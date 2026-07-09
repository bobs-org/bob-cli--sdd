---
create_time: 2026-06-03 15:50:33
status: done
prompt: sdd/prompts/202606/dataview_table_query.md
---
# Plan: Fix `bob dataview` TABLE Query Behavior

## Context and Root Cause

The reported command uses a `TABLE` DQL query without `--format`, so `bob dataview` uses its documented default:
`--format paths`. In that mode, even a Dataview `TABLE` result is converted into the source note paths for matching
rows. The exact Obsidian engine is able to run the query:

- `--format markdown` renders the expected Markdown table.
- `--format json` returns a structured Dataview result with `type: "table"`, table headers, row values, and extracted
  paths.
- The two returned notes are consistent with current vault metadata: both have `parent: [[memory_ref]]`, and
  `memory_ref -> agent_ref -> ai_ref`.

There is still a real TABLE support gap: the headless `native` engine only parses `LIST` queries. A native run of the
same shape fails before evaluation with `unsupported token ','`, because the lexer/parser do not recognize `TABLE`
queries or comma-separated projections. The docs also say the native engine supports `LIST` only, which makes TABLE
behavior inconsistent across engines and easy to misdiagnose.

## Intended Behavior

- Preserve the existing default `paths` output contract. It is script-friendly and already documented for DQL
  `LIST`/`TABLE` path extraction.
- Make `TABLE` a supported query type for the native headless engine for the same local frontmatter/query subset that
  `LIST` currently supports.
- Keep rendered table output explicit: users who want a visible table should use `--format markdown` with the Obsidian
  engine, while users who want structured rows should use `--format json`.
- Update help/docs so this distinction is obvious from the command page and native-engine section.

## Implementation Plan

1. Add focused regression coverage.
   - Add a CLI integration test using the existing native parent-chain fixture with:
     `TABLE status, parent, source_path FROM "ref" WHERE ...`.
   - Assert default `paths` output matches the equivalent `LIST` row set.
   - Add a native `--format json` test for a simple `TABLE` query, asserting `result.type == "table"`, headers match the
     requested columns, row count is correct, and missing fields become `null`.
   - Keep existing Obsidian TABLE path extraction tests intact; they already cover exact-engine TABLE extraction.

2. Extend the native parser without broadening the full DQL surface.
   - Introduce a small `NativeQueryKind` enum: `List` or `Table { columns }`.
   - Add `TABLE` and comma tokens to the native lexer.
   - Parse `TABLE` as a comma-separated list of field chains before optional `FROM` and `WHERE`.
   - Preserve existing `FROM "folder"` and `WHERE` expression semantics.
   - Keep unsupported DQL features rejected with clear native-engine error messages.

3. Extend native evaluation/output.
   - Keep `paths` output unchanged: native `TABLE` returns the same matching source note paths as native `LIST`.
   - Teach `NativeOutput` to retain query kind and, for table queries, projected row values.
   - For native JSON output:
     - `LIST` keeps the current list-shaped result.
     - `TABLE` emits a table-shaped result with headers and `values`.
     - Scalar frontmatter values map to JSON booleans/strings/null.
     - Obsidian wikilink-looking scalar values map to the same lightweight link object shape already used elsewhere.
   - Continue emitting clean stdout and no warnings for supported native queries.

4. Clarify user-facing docs/help.
   - Update `docs/dataview.md` to show the exact distinction:
     - default/`paths` prints matching note paths for `TABLE`;
     - `--format markdown` renders a Markdown table through Obsidian;
     - `--format json` exposes structured table rows.
   - Update the native-engine section from `LIST`-only to `LIST`/limited `TABLE`.
   - Update the command long help text if needed so the native subset description is no longer misleading.

5. Verify.
   - Run `cargo fmt --check`.
   - Run focused tests: `cargo test dataview_native`.
   - Run broader Dataview coverage: `cargo test dataview`.
   - Run full practical checks: `cargo test` and `cargo clippy --all-targets --all-features`.

## Risks and Tradeoffs

- Changing the default format based on query type would break the existing script contract, so this plan does not do
  that.
- Native `TABLE` will remain a local frontmatter subset, not a full Dataview implementation. It should parse only
  straightforward field projections and continue to fail clearly for unsupported DQL.
- Native JSON table values will be useful for automation but will not try to perfectly clone every Dataview runtime
  type.
