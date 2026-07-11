---
create_time: 2026-07-10 13:10:16
status: done
prompt: .sase/sdd/plans/202607/prompts/scheduled_projects.md
tier: tale
---
# Scheduled Project Visibility

## Goal

Make a project note's optional `scheduled` frontmatter date control the visibility of every Obsidian task in that note,
carry a source task's schedule into newly-created project frontmatter, and make future-scheduled child projects
instantly recognizable in the `<ctrl+=>` picker without disturbing the existing project lifecycle and sub-project
workflows.

## Product decisions

- `scheduled` is optional project frontmatter. When present, its scalar value must be an actual calendar date written as
  `YYYY-MM-DD`; quoted and unquoted YAML scalars are accepted, but empty, malformed, and impossible dates are errors.
- "Future" means strictly later than the machine's local current date. Today and all past dates are due. The CLI will
  use its existing overridable clock so `BOB_NOW` can make this boundary deterministic in tests.
- A valid `scheduled` property is an explicit task-visibility override for that project:
  - tomorrow or later: ensure every genuine Markdown/Obsidian task line has one whole-token `#hide` tag;
  - today or earlier: remove whole-token `#hide` tags from every genuine task line;
  - no `scheduled` property: retain the current `^prj` dashboard-surfacing rules unchanged.
- The override applies to open, completed, canceled, nested, and lifecycle tasks, while ignoring frontmatter, fenced
  examples, and ordinary checkbox-like prose. Edits preserve indentation, list markers, inline fields, block IDs, line
  endings, and all unrelated text, and repeated syncs are idempotent.
- Invalid project scheduling is reported as a per-file scan error by both `list` and `sync`; `sync` leaves that file
  untouched while continuing to process other projects. Existing cleanup of legacy inline `[scheduled::...]` fields on
  `^prj` remains in place.
- In the child-note picker, a future-scheduled project gets a compact theme-native `calendar-clock` chip immediately
  before its existing status pill. The chip reads `Tomorrow`, `Jul 16`, or `Jul 16, 2027` as appropriate, while its
  tooltip and accessible label expose the full date. A cool blue/violet tint, restrained selected-row emphasis, and
  responsive wrapping will make it prominent without competing with lifecycle status.

## Implementation plan

1. **Model and validate project schedules in `bob projects`.** Extend the project scan in `src/native/projects.rs` to
   locate `scheduled`, validate its exact date shape and calendar value, retain the parsed date on the project model,
   and compare it with the local date from the shared environment clock. Preserve useful frontmatter line information so
   bad values produce precise errors, and make schedule validation part of the common scan used by both subcommands.

2. **Add a file-wide task visibility reconciliation pass.** Generalize task discovery/editing so the sync planner can
   calculate all missing or stale `#hide` tags in a scheduled project and apply non-overlapping text edits safely
   alongside status, legacy-inline-schedule, and generated Sub-projects edits. Give the schedule override precedence
   over the normal open-`^prj` surfacing decision, but continue status transitions and Sub-project ledger maintenance.
   Add aggregated, readable dry-run/action output (including date, direction, and affected-task count) and a
   task-visibility count in the summary rather than emitting a noisy line per task.

3. **Lock down CLI behavior with tests and documentation.** Extend unit coverage in `src/native/projects.rs` and
   end-to-end coverage in `tests/cli.rs` for tomorrow, today, past, absent, quoted, invalid, and impossible dates; mixed
   task statuses; nested tasks; exact tag boundaries; CRLF; dry-run; partial-file errors; interaction with `^prj`
   surfacing and sub-projects; and second-run idempotence. Use `BOB_NOW` in boundary tests. Update `docs/projects.md`
   and CLI help text to describe the frontmatter contract, precedence, error handling, output, and legacy inline-field
   cleanup.

4. **Transfer source-task scheduling during project creation.** In the `bob-plugins` source-of-truth repository, extend
   `plugins/bob-navigation-hotkeys/main.js` source-task parsing to capture and remove `[scheduled:: ...]` from the
   completion criteria while retaining the existing priority, block-ID, and child-task behavior. Validate the same exact
   date contract before creating anything (and show a focused Notice for invalid or ambiguous values), then pass a valid
   value through project creation and write it as `scheduled` frontmatter in the same metadata update that sets
   `parent`, `type`, and `status`. Tasks without the field continue to create unscheduled projects.

5. **Add the future-schedule indicator to the `<ctrl+=>` child picker.** Extend the pure project-note presentation
   metadata to recognize valid future schedule dates using local date-only comparisons. Include `scheduled`, the raw
   date, and the human label in picker search text and add a future-scheduled count to the modal subtitle. Render the
   `calendar-clock` chip and existing status pill inside a small badge cluster, with exact-date title/ARIA text. Add
   namespaced CSS in `plugins/bob-navigation-hotkeys/styles.css` for theme-safe light/dark colors, selected rows,
   reduced motion, truncation, and narrow layouts; today/past/absent/invalid values receive no future chip.

6. **Test, validate, deploy, and document the plugin change.** Add lightweight Node tests around the exported pure
   helpers for task-property extraction/removal, strict date validation, frontmatter handoff, future-boundary labeling,
   search text, and picker presentation metadata, while retaining syntax/manifest validation. Refresh the plugin README
   description if needed. Run the repository validation, then deploy only `bob-navigation-hotkeys` with
   `bob plugins sync` using the linked repository checkout as the source, as required by that repository's instructions,
   and verify the deployed files match.

## Verification

- Run `cargo fmt --check`, the focused project unit/integration tests, and the full Rust test suite.
- Run the plugin's Node helper tests and `npm run validate`.
- Exercise a temporary vault at a fixed `BOB_NOW`: preview and apply a future project, advance to its scheduled day,
  verify all task tags flip correctly, confirm malformed scheduling does not write, and confirm a second sync is a
  no-op.
- In Obsidian, create a project from a scheduled task and confirm the inline property disappears from `^prj`, the new
  frontmatter owns the date, all other task metadata survives, and the source is removed only after successful creation.
- Open a parent with a mix of ordinary, due, and future-scheduled children via `<ctrl+=>`; verify the calendar chips,
  status pills, search terms, subtitle count, keyboard/mouse selection, tooltip/accessibility text, dark/light themes,
  and narrow-window layout.

## Expected files

- `src/native/projects.rs`
- `tests/cli.rs`
- `docs/projects.md`
- `plugins/bob-navigation-hotkeys/main.js` in the linked `bob-plugins` repository
- `plugins/bob-navigation-hotkeys/styles.css` in the linked `bob-plugins` repository
- plugin test/tooling or README files only as needed for the focused helper coverage and documentation above
