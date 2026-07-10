---
create_time: 2026-07-10 13:34:20
status: done
prompt: .sase/sdd/prompts/202607/future_scheduled_subproject_icon.md
---
# Future-Scheduled Sub-project Calendar Marker

## Goal

Make future-scheduled child projects immediately recognizable in the machine-owned `Sub-projects:` line beneath a parent
project's `^prj` task, matching the future-only visual treatment already used by the Obsidian child-note picker without
changing project lifecycle, ledger retention, or ordering behavior.

## Current gap

The scheduled-project implementation carries schedule metadata into project frontmatter, reconciles task visibility, and
shows a `calendar-clock` chip in the `<ctrl+=>` picker. The CLI's generated parent ledger does not carry schedule
metadata into its sub-project model, however, so it still renders scheduled open children as ordinary bare wikilinks,
for example `- 🧩 **Sub-projects:** [[roadmap]]`.

## Product decisions

- Use `🗓️` as the compact Markdown-native equivalent of the picker's `calendar-clock` indicator. Render it directly
  before each qualifying child, for example `🗓️ [[roadmap]]`.
- A child qualifies only while its valid `scheduled` frontmatter date is strictly later than the machine's local current
  date. Today, past, absent, and invalid schedules do not receive the marker. This preserves the same date boundary and
  `BOB_NOW` override used by task visibility and the picker.
- Keep the existing `🧩 **Sub-projects:**` heading, open-before-closed/name ordering, separators, wikilinks, and closed
  lifecycle decorations. If a retained closed-ledger child has a future schedule, render the calendar before its struck
  link, such as `🗓️ ~~[[roadmap]]~~ ✅`; lifecycle state and schedule remain independent pieces of metadata.
- Treat the calendar marker as part of the fully machine-owned canonical line. `bob projects sync` adds it when a child
  becomes future-scheduled and removes it on the scheduled date, after a schedule is cleared, or after a schedule moves
  to today or the past. Repeated syncs remain idempotent.
- Report marker additions and removals as meaningful `^prj` ledger actions in normal and dry-run output rather than
  describing a date-boundary update only as generic canonical-format normalization. Existing summary accounting remains
  project-line based.
- Keep the change in `bob-cli`; no `bob-navigation-hotkeys` source or CSS change is needed because the picker already
  presents future scheduling with its richer date chip.

## Implementation plan

1. **Carry future-schedule presentation state into parent-ledger entries.** Extend the sub-project entry assembled from
   each cleanly parsed child project with whether its validated schedule is later than the shared local `today` value.
   Thread that same date through child aggregation and parent planning so task visibility and ledger decoration cannot
   disagree at midnight boundaries or under `BOB_NOW`. Preserve the existing effective lifecycle-state calculation,
   parent-link matching, and closed-entry retention rules.

2. **Reconcile schedule decoration as semantic ledger state.** Compare the desired future-scheduled flag with the
   machine-owned marker line for each existing child link, alongside the current open/done/canceled comparison. Plan
   explicit marker-add and marker-remove actions when the flag changes, while retaining canonical normalization for
   indentation, ordering, duplicates, separators, and other malformed line text. Ensure the emoji parser recognizes only
   the marker belonging to the relevant entry and does not interfere with strikethrough or done/canceled markers.

3. **Render the canonical calendar-decorated entry form.** Update sub-project entry rendering to prefix qualifying open
   and retained closed children with `🗓️`, leaving all non-qualifying entries byte-for-byte in their current canonical
   form. Keep edits confined to the generated marker line and preserve line endings, surrounding user-owned sub-bullets,
   and the existing one-line rewrite/idempotence guarantees.

4. **Lock down behavior with unit and end-to-end coverage.** Add focused tests for tomorrow versus today/past/absent
   schedules, mixed scheduled and ordinary siblings, open and retained closed children, stable sorting, parsing beside
   strikethrough/status markers, dry-run output, first-run reconciliation, and second-run idempotence. Add a fixed
   `BOB_NOW` integration case that creates the marker before the boundary and removes it on the scheduled date without
   changing the link or lifecycle marker. Retain existing invalid-date and partial-scan expectations.

5. **Document the generated ledger contract.** Update project documentation and representative output examples with the
   `🗓️ [[child]]` form, the future-only/local-date rule, automatic boundary cleanup, its relationship to closed ledger
   entries, and the distinction between this compact parent-note marker and the picker's labeled calendar chip.

## Verification

- Run the focused `projects` unit and CLI integration tests with deterministic `BOB_NOW` values on both sides of a
  scheduled-date boundary.
- Run `cargo fmt --check` using the repository-supported formatter when available, then run the full Rust test suite.
- Exercise a temporary vault containing an unscheduled child, a today-scheduled child, a future-scheduled open child,
  and a retained future-scheduled closed child; preview and apply sync, advance the date, and confirm only the generated
  parent ledger line changes and a second sync is a no-op.

## Expected files

- `src/native/projects.rs`
- `tests/cli.rs`
- `docs/projects.md`
