---
create_time: 2026-07-10 13:42:28
status: done
prompt: .sase/sdd/plans/202607/prompts/tasks_query_parity.md
bead_id: bob-cli-9
tier: epic
---
# Native Obsidian Tasks Query Support for `bob query`

## Objective

Extend `bob query` so it can run Obsidian Tasks plugin queries (```tasks code-block language) against the Bob vault with
full parity to the installed Tasks plugin, without requiring a running Obsidian app.

"Full parity" is defined precisely as: matching the behavior of the installed **obsidian-tasks-plugin v8.0.0** as
configured in `~/bob/.obsidian/plugins/obsidian-tasks-plugin/data.json`, including:

- The complete query language: status, date, text, tag, priority, recurrence, and dependency filters; Boolean
  combinations (`AND`/`OR`/`NOT`/`AND NOT`/`OR NOT`/`XOR` with parentheses); regex filters with flags; comments and line
  continuations.
- `filter by function`, `sort by function`, and `group by function` JavaScript instructions, including the `moment()`
  API that Tasks exposes to them.
- All `sort by`, `group by` (multi-level, `reverse`), `limit`, and `limit groups` instructions, plus Tasks' default sort
  order when no sort is given.
- Layout/display instructions (`short mode`, `full mode`, `hide toolbar`, `hide edit button`, `show tree`, etc.),
  `explain`, and task-count output.
- Settings-driven behavior from the vault's Tasks `data.json`: global filter (`#task`), global query, custom statuses
  (`/` In Progress, `*` Next, `-` Canceled), `taskFormat: dataview`, and presets (`preset <name>`).
- Query File Defaults (`TQ_*` frontmatter properties, e.g. `TQ_extra_instructions`) and query placeholders
  (`{{query.file.path}}`, etc.).
- Task-line parsing in both the vault's configured dataview format (`[due:: ...]`, `[completion:: ...]`, `[id:: ...]`,
  `[dependsOn:: ...]`, `[priority:: ...]`, ...) and the emoji format, with statuses, tags, block IDs, nested child
  tasks, and urgency scoring.

Acceptance is anchored on the real dashboard: the three queries in `~/bob/dash.md` (WIP `status.type is IN_PROGRESS`,
NEXT `status.name includes Next`, READY `status.type is TODO`, each combined with the note's `TQ_extra_instructions`
defaults) must return exactly the tasks Obsidian shows.

Out of scope: task mutation (toggling, postponing, recurrence generation, "on completion" actions), interactive UI
elements (the toolbar, edit/postpone buttons render as nothing in CLI output but their `hide`/`show` instructions must
parse and behave), auto-suggest, and the Tasks editor/modal APIs. This is read-only query parity.

## Current State

- `bob query` (recently renamed from `bob dataview`) runs Dataview source expressions and DQL with two engines: `native`
  (default, headless Rust implementation) and `obsidian` (evaluates JavaScript in the live desktop app via the official
  `obsidian` CLI's `eval` command, protocol-prefixed stdout).
- The native Dataview engine lives in `src/native/dataview.rs` (~6,900 lines) with submodules
  `src/native/dataview/index.rs` (vault scan/index) and `value.rs`. It has an established pattern of fixture-vault
  golden tests (`tests/fixtures/dataview_parity/`, `tests/dataview_parity.rs`) plus an env-gated live parity harness
  (`BOB_DATAVIEW_PARITY_LIVE`).
- There is **no** Tasks-plugin query support anywhere in `bob`. Dataview `TASK` queries exist but are a different
  language with different task semantics (no statuses registry, no urgency, no dependency filters, etc.).
- The vault has ~1,120 `#task` lines across ~125 notes and 17 live
  ```tasks blocks (3 in `dash.md`, 14 in daily notes). Task metadata uses the dataview format. `BOB_NOW` is the repo's
  established env override for "now" in date-sensitive commands.
- The Tasks plugin has no public query-execution API, so the `obsidian` engine cannot call a `tryQuery` equivalent the
  way Dataview does. A live oracle has to go through rendering (e.g. `MarkdownRenderer.render` on a
  ```tasks block and scraping the resulting DOM) — feasible via the existing `obsidian eval` plumbing, but strictly an
  oracle, not the primary engine.

## Design Direction

- **New query-input flags on the existing `bob query` command** (joining the existing mutually-exclusive `query-input`
  group):
  - `-t, --tasks <QUERY>`: inline Tasks query (newline-separated instructions).
  - `-T, --tasks-file <PATH>`: Tasks query from a file, `-` for stdin.
  - `-n, --tasks-note <VAULT_RELATIVE_PATH>`: run **every**
    ```tasks block in a vault note exactly as Obsidian would render that note (Query File Defaults, placeholders, global query/filter all applied), emitting per-block results. This is the primary tool for verifying `dash.md`.
  - `--origin` gains meaning for `--tasks`/`--tasks-file`: it supplies the `query.file.*` context, placeholder values,
    and that note's `TQ_*` Query File Defaults, so `--tasks 'status.type is TODO' --origin dash.md` behaves exactly like
    a block inside `dash.md`.
  - Existing `--format` values map naturally: `paths` (unique note paths containing matched tasks), `json` (structured
    groups/tasks/counts/explanation), `markdown` (Tasks-like rendered text output honoring layout instructions). CLI
    help stays alphabetized, every public long option keeps a short alias, and colored output is preferred where it
    helps (per `memory/cli_rules.md`).
- **A new `tasks` subsystem** under `src/native/dataview/tasks/` (the query command's module), split roughly as:
  `settings` (Tasks `data.json`: statuses, global filter/query, presets), `task` (task model, line parser for both
  formats, status registry, urgency), `index` (vault task scan, hierarchy, dependency graph), `parse` (instruction
  lexer/parser, placeholders, presets, TQ_\* defaults, Boolean algebra), `filter`/`sort`/`group` (semantics), `js`
  (by-function engine), `render` (markdown/json/paths output). Reuse the existing vault-walk and frontmatter helpers
  where practical, but do not force Tasks semantics into Dataview types.
- **Vault scan scope must match Obsidian, not bob's other commands.** Obsidian (and therefore Tasks) indexes
  `_templates/` and `_generated/` — that is exactly why `dash.md` filters `folder does not include _templates` in its
  query. The tasks index must scan all vault markdown except dot-directories (`.obsidian`, `.git`, `.trash`), unlike
  `ALWAYS_EXCLUDED_NOTE_DIRECTORY_NAMES` used elsewhere in the repo.
- **JavaScript `by function` instructions need a real JS engine.** This is unavoidable for full parity — `dash.md`
  itself uses `filter by function` and `sort by function` with `moment()`. Recommended approach:
  - Embed `boa_engine` (pure Rust, no C toolchain) as the sandbox; fall back to `rquickjs` (QuickJS bindings) only if
    boa proves unable to run the required code.
  - Vendor `moment.min.js` into the binary and evaluate it inside the sandbox, so `moment()` and every
    `task.<date>.moment` value is a **real** Moment object rather than a hand-written shim — this is the cheapest route
    to genuine parity for date logic.
  - Build the `task` and `query` expose objects to match Tasks' documented custom-filter API (`task.file.path`,
    `task.lineNumber`, `task.tags`, `task.scheduled.moment`, `task.priorityName`, `query.file.*`, `query.allTasks`,
    ...), driving the sandbox clock from `BOB_NOW`.
- **Determinism**: all "today"-relative behavior (date filters, urgency, `moment()`) flows through the existing
  `BOB_NOW` override so fixtures and tests are stable.
- **Oracle strategy**: primary correctness rails are a deterministic fixture vault with golden tests (mirroring the
  Dataview parity approach), plus an env-gated live harness (`BOB_TASKS_PARITY_LIVE`) that renders
  ```tasks blocks in the running desktop app via `obsidian
  eval`+`MarkdownRenderer.render`DOM scraping. Whether to also expose this as`--engine
  obsidian`for tasks inputs is decided late (Phase 7), once its reliability is known; if it is not exposed, tasks inputs must reject`--engine
  obsidian` with a clear error.
- **Reference implementation**: treat the Tasks v8.0.0 source (GitHub `obsidian-tasks-group/obsidian-tasks`, tag
  matching the installed version) as the specification for exact semantics — default sort order, urgency coefficients,
  unknown-status handling, `is not blocked` semantics, recurrence-rule normalization, group-heading naming — rather than
  re-deriving them from prose docs.

## Phases

Each phase is completed by a distinct agent instance, leaves the repo in a passing-test state (`just all`), and ends
with updated goldens so the next phase starts from green.

### Phase 1: Contract, CLI Surface, and Tasks Parity Fixture Vault

Goal: make Tasks parity measurable before building the engine, and land the CLI plumbing end-to-end.

Scope:

- Add `--tasks`, `--tasks-file`, and `--tasks-note` to `bob query` (query-input group, help text, docs stubs), including
  `--origin` interaction rules and format validation.
- Read Tasks plugin settings from `<vault>/.obsidian/plugins/obsidian-tasks-plugin/data.json` with stable defaults when
  absent (default statuses, empty global filter/query, emoji task format).
- Create `tests/fixtures/tasks_parity/vault/` with a Tasks `data.json` mirroring the real vault's settings (dataview
  task format, `#task` global filter, custom statuses `/`, `*`, `-`, stock presets) and fixture notes covering: every
  status; both metadata formats; all date fields (due/scheduled/start/created/done/cancelled) including invalid dates;
  priorities; recurrence; `id`/`dependsOn` chains (blocked, blocking, done-dependency); nested child tasks; block IDs;
  tags including `#hide`; tasks missing the global filter; `_templates/` and `_generated/` notes; a daily note; a
  dashboard-like note with `TQ_extra_instructions` and all three dash statuses; `-`/`*`/`+` and numbered list markers.
- Implement the minimal end-to-end slice: an empty/filterless tasks query returns every global-filter task in the
  fixture vault (paths + json), proving settings read, vault scan scope (`_templates` included), and output plumbing.
- Add `tests/tasks_parity.rs` with golden tests for the slice plus the `BOB_TASKS_PARITY_LIVE` env-gated live-oracle
  scaffolding (can be a stub that documents the mechanism).

Done when: new flags appear in help/docs, the filterless slice passes golden tests against the fixture vault, and
existing suites still pass.

Estimate: 1-2 days.

### Phase 2: Task Model and Vault Task Index

Goal: parse every task in a vault into a model rich enough for all later filters, sorts, and groups.

Scope:

- Task-line parser for the vault's dataview format and the emoji format: status symbol, description (raw + display
  cleanup honoring `removeGlobalFilter: false`), all date fields, priority, recurrence rule text, `id`, `dependsOn`,
  `onCompletion`, tags, block ID.
- Status registry from settings: core + custom statuses, symbol → name/type/nextSymbol, and Tasks' exact unknown-symbol
  semantics (v8 registers unknowns with TODO type) — match the plugin source.
- File/positional context per task: path, folder, filename, root, preceding heading, line number; parent/child task
  hierarchy (indentation-based, including non-task list-item parents).
- Dependency graph over the indexed vault: `isBlocked`/`isBlocking` with semantics identical to Tasks v8 (done/cancelled
  dependencies don't block, missing ids, self-references, duplicate ids).
- Urgency score matching Tasks' published formula and coefficients exactly, driven by `BOB_NOW`.
- Recurrence: parse/normalize rule text sufficiently for `is recurring`, `recurrence includes`, and
  `group by recurrence` display parity (no occurrence generation needed).
- Unit tests for every parser/model behavior against the fixture vault; expand fixtures where gaps appear.

Done when: index unit tests pass, the Phase 1 filterless slice now reports full task metadata in `json` output, and
urgency/blocked values for fixture tasks match hand-verified expectations from the plugin source.

Estimate: 4-7 days.

### Phase 3: Query Language Parser

Goal: parse the complete Tasks query language into an AST without yet evaluating most of it.

Scope:

- Instruction-line preprocessing: `#` comments, trailing-`\` line continuations, case-insensitivity rules.
- Query composition pipeline exactly as Tasks does it: global query → Query File Defaults (`TQ_*` properties, full set
  supported by v8) → block/inline instructions; `ignore global query`; `preset <name>` expansion including nested
  presets; placeholder templating (`{{query.file.path}}`, `{{query.file.folder}}`, etc.) with Tasks' error behavior for
  unknown placeholders or missing context.
- Filter grammar → AST: all status (`done`, `not done`, `status.type is/is not`,
  `status.name includes/does not include`, `status.symbol`), date (`due/scheduled/starts/created/done/cancelled/happens`
  with on/before/after/on-or-before/on-or-after, ranges, `has`/`no <field> date`, `<field> date is invalid`), text
  (`description`/`heading`/`path`/`folder`/`filename`/`root` includes/does not include,
  `regex matches`/`regex does not match` with flags), tag, priority (`is`/`is above`/`is below`/`is not`), recurrence,
  dependency (`has id`, `id includes`, `has depends on`, `is blocked`, `is not blocked`, `is blocking`,
  `is not blocking`) filters; Boolean combinations with parentheses; `filter by function` capturing raw JS source.
- Sort/group/limit/layout instructions: `sort by <key>` (+ `reverse`), `group by <key>` (+ `reverse`),
  `sort/group by function`, `limit [to] N [tasks]`, `limit groups [to] N`, `short mode`/`full mode`, all `hide`/`show`
  instructions v8 accepts (toolbar, edit button, postpone button, backlinks, tree, urgency, task count, every field
  hide, ...), `explain`.
- Error messages that mirror Tasks' "do not understand" diagnostics closely enough to debug queries; parser tests for
  valid and invalid instructions, including every instruction used anywhere in the real vault's 17 blocks.

Done when: every instruction in the fixture vault, `dash.md`, the daily-note blocks, and the settings presets parses to
the expected AST; unknown instructions produce high-quality errors; no behavior regressions.

Estimate: 4-6 days.

### Phase 4: Filter Engine (non-JavaScript)

Goal: correct evaluation semantics for every non-`by function` filter.

Scope:

- Date semantics engine: relative keywords (`today`, `yesterday`, `tomorrow`, weekday names,
  `this/next/last week|month|quarter|year`, absolute dates, explicit `YYYY-MM-DD YYYY-MM-DD` ranges) resolved against
  `BOB_NOW`, matching Tasks' range expansion rules (e.g. `due before this week` boundaries) exactly.
- `happens` (min of due/scheduled/start) semantics; invalid-date filters; `has`/`no` field filters.
- Status, text (case-insensitive substring), regex (with flag handling), tag, priority ordering, recurrence, and
  dependency filter evaluation; Boolean expression evaluation with Tasks' precedence/parenthesization rules.
- Golden tests per filter family against the fixture vault with `BOB_NOW` pinned, including date-boundary cases (weekend
  week-start, month/quarter/year edges) and the exact filters used in `dash.md` (`is not blocked`,
  `folder does not include _templates`).

Done when: all non-function filters pass goldens; combining filters (implicit AND across lines, explicit Boolean lines)
matches Tasks; the fixture dashboard note's non-function subset returns the hand-verified task set.

Estimate: 1-2 weeks.

### Phase 5: `by function` JavaScript Support

Goal: run `filter by function`, `sort by function`, and `group by function` with real parity.

Scope:

- Add the JS sandbox dependency (recommended `boa_engine`; fall back to `rquickjs` if boa cannot execute vendored
  moment.js — decide with a spike at phase start and record the decision).
- Vendor `moment.min.js` (build-time include, license noted) and initialize the sandbox with it; drive its notion of
  "now" from `BOB_NOW`.
- Construct the `task` expose object per Tasks' custom-filter API: `task.description`, `task.descriptionWithoutTags`,
  `task.status.*`, `task.priorityName`/`priorityNumber`, `task.urgency`, `task.tags`,
  `task.due/scheduled/start/created/done/cancelled` as TasksDate-like objects with working `.moment`,
  `task.file.path/folder/filename/root`, `task.heading`, `task.lineNumber`, `task.isRecurring`, `task.id`,
  `task.dependsOn`, `task.isBlocked(...)`-relevant data as v8 exposes it; and `query.file.*` plus `query.allTasks`.
- Execute the three `by function` instruction kinds with Tasks' semantics for return types, group-key arrays,
  errors-in-function reporting, and sort-comparator behavior.
- Tests: the exact `dash.md` expressions (`task.file.path !== query.file.path`,
  `!task.scheduled.moment || task.scheduled.moment.isSameOrBefore(moment(), "day")`, `!task.tags.includes("#hide")`,
  `sort by function task.file.path` / `task.lineNumber`) against fixtures with pinned `BOB_NOW`, plus error-path tests.

Done when: dash-style function filters/sorts produce hand-verified results on the fixture vault; sandbox failures
surface as clear query errors, not panics; binary still builds without a C toolchain (or the rquickjs fallback is
documented).

Estimate: 1 week.

### Phase 6: Sort, Group, Limit, and Output Rendering

Goal: complete the result pipeline so output matches what Obsidian displays.

Scope:

- Tasks' default sort order (verify against v8 source) and all `sort by` keys with multi-key stacking, `reverse`, and
  interleaving with `sort by function`.
- Grouping: all `group by` keys with Tasks' group-heading naming rules, multi-level nested groups, `reverse`,
  `limit groups`; task counts (total and per-group) matching Tasks' "N tasks" strings.
- `limit N`; `explain` output text closely matching Tasks' explanation format.
- Output formats: `markdown` renders Tasks-like static text (group headings, checkbox lines honoring `short mode`,
  `hide`/`show` field instructions, `show tree` child nesting, counts); `json` carries the full structured result (query
  metadata, groups, ordered tasks with all fields, counts, explanation when requested); `paths` yields unique note paths
  in result order. Layout instructions that are UI-only (toolbar, edit/postpone buttons, backlinks rendering) parse and
  toggle the corresponding text elements or no-op — documented either way.
- Golden tests across formats, including grouped + limited + short-mode combinations and the fixture dashboard note.

Done when: fixture goldens cover every sort/group key and layout instruction; markdown output for the fixture dashboard
note is line-for-line stable and hand-verified against Obsidian's rendering of the same fixtures.

Estimate: 1 week.

### Phase 7: Note-Block Execution, Live Oracle, CLI Polish, and Docs

Goal: run whole notes the way Obsidian renders them, and finish the user-facing surface.

Scope:

- `--tasks-note`: extract every
  ```tasks block from a vault note, apply the full composition pipeline (global query, that note's `TQ_\*` defaults,
  placeholders with the note as query context), execute each, and emit per-block results with block identification
  (heading context) in all three formats.
- Finalize `--origin` behavior for `--tasks`/`--tasks-file` (context + defaults application) and cover interactions
  (`--tasks-note` with `--origin` rejected, etc.).
- Implement the live oracle in the parity harness: `obsidian eval` script that calls `MarkdownRenderer.render` on a
  given
  ```tasks block with a given source path, waits for async render, and scrapes matched tasks (description, status symbol, backlink target, group headings) back over the existing protocol. Gate with `BOB_TASKS_PARITY_LIVE`. Then decide and implement `--engine
  obsidian` for tasks inputs: expose it if the mechanism is reliable (documenting reduced format support), otherwise
  reject tasks+obsidian with a clear error.
- Documentation: update `docs/dataview.md` (or split out a `docs/tasks-queries.md`), `README.md`, command
  `about`/`long_about`/examples so `bob query` presents both query languages; comply with `memory/cli_rules.md`
  (alphabetized options/subcommands, short aliases, colored output where it improves readability).

Done when: `bob query --tasks-note dash.md`-style invocations work end-to-end on the fixture dashboard note, the live
harness runs (or cleanly skips without a desktop app), docs/help are complete, and `just all` passes.

Estimate: 3-5 days.

### Phase 8: Real-Vault Parity Hardening and dash.md Acceptance

Goal: prove the acceptance criterion on the real vault and close every gap found.

Scope:

- Run all three `~/bob/dash.md` queries natively (`--tasks-note dash.md`, plus each block individually with
  `--origin dash.md`) and capture results.
- Build an **independent** ground-truth check: a small script (or test) that derives the expected WIP/NEXT/READY task
  sets from the raw vault (global-filter lines, status symbols, scheduled-date rule, `#hide` exclusion, `_templates`
  exclusion, dash.md self-exclusion, blocked-dependency rule) without going through the new engine, and diff it against
  native output. Investigate and fix every discrepancy; add a regression test for each fix.
- If desktop Obsidian is available, run the live oracle on `dash.md` and on the fixture vault and reconcile; if it is
  not available, record that manual Obsidian-side confirmation is the remaining acceptance step for Bryan.
- Sweep the other 14 daily-note ```tasks blocks: every block must parse and execute without errors; spot-check results.
- Document verified parity boundaries and any intentional differences in the docs; run the full suite and the Dataview
  live harness to confirm no regressions.

Done when: native results for the three dash.md queries exactly match the independent ground truth (and the live oracle
where available), all vault blocks execute cleanly, and remaining differences (if any) are documented as explicit
non-goals rather than silent gaps.

Estimate: 3-5 days.

## Sequencing Notes

- Phases run strictly in order; each leaves `just all` green. Phase 1 builds the acceptance rails; 2-6 build the engine
  inside-out (model → parser → semantics → JS → output); 7 completes the surface; 8 proves the acceptance criterion on
  the real vault.
- The JS engine (Phase 5) is deliberately isolated: it is the largest dependency decision and the most likely place to
  need a pivot (boa → rquickjs). Phases 4 and 6 do not depend on it beyond AST plumbing landed in Phase 3.
- Do not tune output rendering (Phase 6) before filter semantics (Phase 4) are trustworthy, or goldens will churn.
- `dash.md` and the vault's other blocks are the north star throughout: every phase should keep the specific
  instructions they use inside its test set.

## Main Risks

- **JS engine compatibility**: vendored moment.js must run inside boa; if it cannot, switch to rquickjs (adds a C build
  dependency). Mitigated by a spike at the start of Phase 5 and by isolating all JS behind one module.
- **Exact-behavior details**: default sort order, urgency coefficients, unknown-status typing, `is not blocked` edge
  cases, date-range boundaries, and recurrence-text normalization are easy to get subtly wrong from prose docs.
  Mitigation: treat the pinned v8.0.0 plugin source as the spec and encode each behavior in a golden test.
- **Live oracle fragility**: DOM scraping through `obsidian eval` depends on the desktop app being open and on Tasks'
  rendered markup. It is an oracle only; native correctness never depends on it, and the harness must skip cleanly when
  unavailable.
- **Vault scan divergence**: Tasks indexes `_templates`/`_generated` while other bob commands exclude them; the tasks
  index must follow Obsidian. Encoded in fixtures from Phase 1 so it cannot regress silently.
- **Clock/timezone sensitivity**: scheduled-date filters and urgency change at midnight boundaries. All evaluation flows
  through `BOB_NOW` (local-time semantics matching Obsidian's) and tests always pin it.
- **Scope breadth**: the Tasks language is large. The phase gates (parser-complete before semantics, fixtures before
  engine) keep partial progress shippable and measurable, mirroring the successful Dataview-parity epic.

## References

- Local: `src/native/dataview.rs`, `src/native/dataview/index.rs`, `tests/dataview_parity.rs`,
  `tests/fixtures/dataview_parity/`, `docs/dataview.md`, `memory/cli_rules.md`.
- Prior epic (conventions this plan mirrors): `.sase/sdd/epics/202606/dataview_native_parity.md`.
- Prior research: `.sase/sdd/research/202607/dash_tasks_query_dedup_consolidated.md` (dash.md query inventory, Tasks
  v8.0.0 confirmation, Query File Defaults background).
- Vault ground truth: `~/bob/dash.md`, `~/bob/.obsidian/plugins/obsidian-tasks-plugin/data.json` (statuses, global
  filter `#task`, `taskFormat: dataview`, presets).
- Tasks plugin docs: https://publish.obsidian.md/tasks/ (Queries, Filters, Sorting, Grouping, Layout, Custom
  Filters/Sorting/Grouping, Query File Defaults, Presets, Global Filter, Global Query, Urgency, Task Dependencies,
  Statuses, Dataview Format).
- Tasks plugin source (parity spec, pin to installed version): https://github.com/obsidian-tasks-group/obsidian-tasks at
  tag `8.0.0`.
