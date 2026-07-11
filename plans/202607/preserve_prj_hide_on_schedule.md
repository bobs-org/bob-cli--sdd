---
create_time: 2026-07-11 07:50:18
status: done
prompt: .sase/sdd/plans/202607/prompts/preserve_prj_hide_on_schedule.md
tier: tale
---
# Preserve `^prj` Visibility During Scheduled Project Sync

## Goal

Correct `bob projects sync` so reaching a project's `scheduled` date reveals the project's ordinary Obsidian tasks
without prematurely revealing its definition-of-done task. The `^prj` task should have `#hide` removed by the
scheduled-visibility rule only when it is the sole real Obsidian task in the project note.

For this rule, a "real Obsidian task" should retain the command's existing meaning: any parsed Markdown checkbox task
outside frontmatter and fenced code, including open, in-progress, completed, canceled, nested, quoted, and ordered
tasks. Checkbox-like prose and fenced examples do not count.

## Behavioral Design

- Preserve the future-schedule behavior: every real task, including `^prj`, receives exactly one whole-token `#hide`
  while the schedule is in the future.
- On the scheduled date and afterward, remove whole-token `#hide` tags from all ordinary real tasks.
- When the note has more than one real task, exclude `^prj` from due/past removal and leave its existing `#hide` state
  untouched.
- When `^prj` is the only real task in the note, allow due/past removal to show it, preserving the current useful
  behavior for projects with no separate work tasks.
- Keep scheduled frontmatter as the override for the ordinary `^prj` surfacing calculation; this fix narrows scheduled
  tag removal rather than re-enabling the unrelated open-task/sub-project surfacing rules.
- Report only task lines that are actually changed, so per-project action text, summary totals, dry runs, and
  repeated-sync no-op behavior remain accurate.

## Implementation Plan

1. In `src/native/projects.rs`, enrich the task metadata gathered during project parsing so scheduled visibility can
   distinguish the valid `^prj` task from every other real task while continuing to use the existing total task
   population for the sole-task decision.
2. Centralize the eligibility decision used by scheduled visibility planning: all tasks are eligible when hiding for a
   future date; when showing a due/past project, `^prj` is eligible only if the note contains no other real task. Use
   this decision when calculating the change count and carry the same policy into change application so the reported
   plan cannot diverge from the text edits.
3. Update the scheduled task-visibility editor to skip `#hide` removal on `^prj` when the policy says to preserve it,
   while retaining all current token-boundary, duplicate-tag normalization, formatting, line-ending, fenced-code, and
   block-ID guarantees for eligible tasks.
4. Extend the unit tests in `src/native/projects.rs` to cover both sides of the exception: a due/past note with
   additional tasks preserves `#hide` on `^prj` and counts/edits only the other hidden tasks, while a note whose only
   task is `^prj` removes its `#hide`. Retain assertions that future scheduling still hides `^prj` and all other real
   task forms.
5. Update the CLI regression coverage in `tests/cli.rs` across dry-run, applied future sync, the scheduled-date
   boundary, and a repeated no-op sync. Assert exact file contents and visibility totals after the due sync, and add
   end-to-end coverage for the sole-`^prj` exception if it is not fully covered by the existing boundary fixture.
6. Revise the `bob projects sync` long help and `docs/projects.md` contract so they no longer promise removal from every
   task on/after the scheduled date and explicitly document the protected `^prj` behavior and sole-task exception.

## Verification

- Run `cargo fmt --check` after implementation formatting.
- Run the focused scheduled-visibility unit and CLI tests while iterating.
- Run the full `cargo test` suite to catch interactions with project lifecycle, sub-project ledgers, status
  reconciliation, task parsing, reporting, and idempotence.
- Review the final diff to confirm only the project sync implementation, relevant tests, and user-facing documentation
  changed.
