---
create_time: 2026-07-11 08:47:51
status: done
prompt: .sase/sdd/prompts/202607/project_note_properties.md
---
# Plan: Project-note properties in the Obsidian bullet-property picker

## Goal

Extend Bob Navigation Hotkeys' `Set bullet property` command (bound to `Ctrl+Shift+P`) so that choosing `scheduled`
while the cursor is on the valid project lifecycle task anchored by `^prj` writes the project note's `scheduled` YAML
property instead of adding `[scheduled:: ...]` to the task. The same operation must immediately reconcile task `#hide`
tags according to the `bob projects sync` scheduling contract.

Only `scheduled` is a project-note property in this change. Other configured properties, including `dependsOn`, retain
their current inline Dataview behavior even when invoked from `^prj`. The existing chezmoi configuration already
declares `scheduled` as a date property, so no configuration schema or chezmoi change is needed.

## Current behavior and contracts

- `bob-navigation-hotkeys` loads the property list from `~/.config/bob/config.yml`, derives each property's current
  state from inline Dataview fields on the cursor line, and routes set/delete actions through the inline-field helpers.
- The project task is a real Markdown task with an exact trailing `^prj` block ID. The project CLI also requires the
  task to contain the whole-token `#task` tag; legacy omission of `#prj` remains valid.
- `bob projects sync` treats frontmatter `scheduled: YYYY-MM-DD` as the sole scheduling source and removes stale inline
  `[scheduled:: ...]` fields from active open `^prj` tasks.
- For a future scheduled date, every real Markdown task in the note has exactly one whole-token `#hide`. For today or a
  past date, all whole-token `#hide` tags are removed from ordinary tasks. The `^prj` task keeps its current `#hide`
  state when any other task exists, but loses all `#hide` tags when it is the note's only task.
- Visibility reconciliation covers open, in-progress, completed, canceled, nested, ordered-list, blockquoted, and
  lifecycle tasks. It ignores YAML, fenced code, and checkbox-like prose, and preserves indentation, markers, inline
  fields, trailing block IDs, unrelated tags such as `#hidden`, and the document's line endings.

## Implementation plan

1. **Introduce explicit property-target resolution in Bob Navigation Hotkeys.** Add a small allowlist/descriptor for
   project-note properties (initially only `scheduled`) and a context classifier that recognizes a valid, unfenced
   `#task` line with the exact trailing block ID `^prj`. Resolve each picker property to either the existing inline
   Dataview target or the project-note frontmatter target. Keep this resolution centralized so future file properties
   can be added without scattering `scheduled` checks through the modal.

2. **Make the picker display the effective value from the resolved target.** When the cursor is on `^prj`, read
   `scheduled` from the active editor's YAML frontmatter and use it for the property's defined/current state, sorting,
   current-value badge, date selection, and `Ctrl+D` eligibility. Continue reading every other property from the cursor
   line. Validate the active file, cursor task, frontmatter shape, and existing schedule before opening or committing;
   malformed or stale context should produce a focused notice and no write.

3. **Add a pure project-schedule visibility planner matching the CLI.** Given note content, a valid schedule date, and
   an injected local “today,” identify real Markdown task lines outside frontmatter and fences and plan the same
   whole-token `#hide` edits as `bob projects sync`: normalize all tasks to one `#hide` for a future date; for
   today/past remove `#hide` from ordinary tasks and apply the special sole-`^prj` rule. Reuse the plugin's existing
   task, tag-boundary, block-ID, date-validation, and line-edit conventions where possible, and keep the helper
   deterministic for tests.

4. **Route project `scheduled` set operations through a coordinated note update.** Upsert `scheduled` in YAML using the
   canonical `YYYY-MM-DD` value selected by the picker, remove any inline `[scheduled:: ...]` field from the `^prj` task
   so frontmatter remains the sole source, and apply the visibility plan only after all guards and transformations
   succeed. Commit the planned frontmatter/body changes through the active Obsidian file/editor APIs as one coordinated
   operation, preserve cursor position as safely as the current inline path does, await completion before closing the
   modal, and issue one success or failure notice.

5. **Route project `scheduled` deletion to YAML without guessing an unscheduled visibility state.** `Ctrl+D` on a
   frontmatter-backed `scheduled` item should delete that YAML property and remove any stale inline scheduled field,
   while leaving existing `#hide` tags untouched. This follows the CLI boundary: the schedule-wide visibility policy
   applies only while a valid schedule exists, whereas unscheduled `^prj` surfacing depends on open tasks and
   sub-project relationships owned by `bob projects sync`. Inline-property deletion remains unchanged everywhere else.

6. **Keep asynchronous modal state and stale-write guards correct.** Update the modal's set/delete callbacks to support
   awaited project-note writes while retaining the current synchronous inline path. Re-read the active file, cursor
   task, and note content before committing so a file switch or edit made while the picker is open cannot update the
   wrong note. Refresh or close the modal only after the operation's final result is known.

7. **Document and version the feature.** Bump the Bob Navigation Hotkeys manifest with a semver-minor version and update
   the bob-plugins README's version/feature and test-coverage descriptions. Add a concise section to
   `bob-cli/docs/projects.md` explaining that `Ctrl+Shift+P` on `^prj` writes frontmatter scheduling and applies the
   same immediate visibility policy as `bob projects sync`; identify deletion's intentionally narrower behavior.

## Test plan

Add focused pure-helper coverage in `bob-plugins/scripts/test-navigation-hotkeys.cjs` for:

- Project-task classification: valid legacy/current `#task ... ^prj` lines, and rejection of ordinary tasks, non-task
  bullets, non-trailing/mismatched block IDs, frontmatter, and fenced examples.
- Property-target/current-value resolution: `scheduled` comes from YAML only on `^prj`; ordinary bullets and
  non-scheduled properties continue using inline fields; missing and malformed schedule states fail safely.
- Frontmatter upsert/delete and removal of stale inline `[scheduled:: ...]` without disturbing other inline fields or
  the trailing block ID.
- Future scheduling across open, in-progress, completed, canceled, nested, ordered, and blockquoted tasks;
  zero/one/multiple existing `#hide` tags are normalized to exactly one.
- Today/past scheduling removes all whole-token `#hide` tags from ordinary tasks, preserves `^prj` when other tasks
  exist, and removes it when `^prj` is the only task.
- Preservation of `#hidden`, task formatting, code fences, checkbox prose, frontmatter, trailing whitespace/block IDs,
  LF and CRLF input, date-boundary behavior, idempotence, and the no-visibility-change deletion contract.

Run the repository checks:

```bash
npm test
npm run validate
```

After implementation changes in `bob-plugins`, deploy the source-of-truth plugin to the vault as required by that
repository:

```bash
bob plugins sync -p bob-navigation-hotkeys
```

Finally, manually smoke-test `Ctrl+Shift+P` in Obsidian on an ordinary task and on `^prj` with future, today, changed,
and deleted schedules, confirming both the YAML/inline destination and task visibility behavior.

## Expected files

- `bob-plugins/plugins/bob-navigation-hotkeys/main.js`
- `bob-plugins/scripts/test-navigation-hotkeys.cjs`
- `bob-plugins/plugins/bob-navigation-hotkeys/manifest.json`
- `bob-plugins/README.md`
- `bob-cli/docs/projects.md`

No production changes are expected in `bob-cli`, and no changes are expected in the chezmoi property configuration.
