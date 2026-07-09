---
create_time: 2026-06-19 14:13:50
status: done
prompt: sdd/prompts/202606/reopen_prj_ref_status.md
---
# Plan: Reopen Project and Reference Status from Main Tasks

## Goal

Make `bob projects sync` and `bob highlights scan` treat an opened lifecycle task as an explicit reopen signal:

- Project notes: when a project frontmatter `status` is `done` or `canceled` and its main `^prj` task is open again, set
  frontmatter `status: wip`.
- Reference notes: when a ref's selected synced status is `read` or `abandoned` and its generated `^ref` PDF task is
  open again, set the synced status to `wip`, which updates the ref note frontmatter and, when PDF writes are allowed,
  the corresponding PDF marker note.

No new CLI subcommands or options are needed.

## Current Behavior

`src/native/projects.rs` already treats checked and canceled `^prj` tasks as the lifecycle source of truth:

- `[x]` / `[X]` `^prj` -> `status: done`
- `[-]` `^prj` -> `status: canceled`
- open `^prj` currently does not change frontmatter and instead warns when frontmatter is terminal.

`src/native/highlights_ref/mod.rs` already has a shared planning path for `bob highlights sync` and
`bob highlights scan`:

- checked `^ref` task contributes `status: read`
- canceled `^ref` task contributes `status: abandoned`
- unchecked `^ref` currently contributes no status
- marker write-back remains opt-in through `--write-pdf` / `--write-pdfs`

## Desired Semantics

### Projects

An open `^prj` should reopen only terminal project statuses:

- `done` -> `wip`
- `canceled` / `cancelled` -> `wip`

It should not force `waiting`, missing status, or unknown statuses to `wip`. After the effective status becomes `wip`,
the existing active-project sync logic should still run in the same pass: `#hide`, `[scheduled::...]`, and Sub-projects
line management should behave as if the project were already active.

For parent project ledgers, a child project with terminal frontmatter but an open `^prj` should count as open in the
same sync run. This mirrors the current same-run handling for children whose `^prj` task is checked or canceled before
their frontmatter has been updated.

### References

An open generated `^ref` task should contribute `status: wip` only when the currently selected synced projection is
terminal:

- `read` -> `wip`
- `abandoned` -> `wip`

It should not turn `unread`, existing `wip`, `legacy`, missing tasks, or ordinary newly generated unchecked tasks into
`wip`.

The existing marker/frontmatter conflict model should stay intact. If the user unchecked the `^ref` task while marker or
frontmatter also changed the status to another non-`wip` value since the stored base, the command should report a clear
conflict instead of picking a side silently.

The existing PDF write guard should also stay intact:

- Dry-runs preview the note and marker changes.
- Non-dry-run `scan` without `--write-pdfs` refuses per-PDF when the marker would need a write.
- `scan --write-pdfs` writes both the ref note and PDF marker.

Because checked-task closing intentionally imports pending annotation tasks on the final closing run, reopened refs
should allow annotation-task intake in the same run too. The intake condition should be based on either the status
before the `^ref` task signal or the status after applying it being `wip`.

## Implementation Steps

1. Update project lifecycle planning in `src/native/projects.rs`.
   - Generalize the target project status representation to include `wip` with reason `^prj task opened`.
   - Add a project-aware lifecycle target helper so checked/canceled tasks keep closing projects, while open tasks only
     target `wip` when the parsed frontmatter status is terminal.
   - Remove or bypass the current terminal-frontmatter/open-`^prj` warning for this reopenable case.
   - Use the effective target status when deciding whether to run active project edits.

2. Update project sub-project state calculation.
   - Make child state use the same effective lifecycle target as project sync.
   - A terminal child with an open `^prj` should be treated as an open sub-project for parent marker generation in that
     same sync run.
   - Keep malformed, multiple, or missing `^prj` handling unchanged.

3. Update ref PDF task status signaling in `src/native/highlights_ref/mod.rs`.
   - Add an explicit reopen signal for `PdfTaskLineState::Present` with an unchecked task when the selected projection
     status is `read` or `abandoned`.
   - Reuse the existing conflict helper with target `wip`, so competing marker or frontmatter status edits fail
     consistently.
   - Mark the resolution as frontmatter-contributed when the `^ref` task causes `wip`, preserving the existing marker
     write-back detection.
   - Keep missing `^ref` tasks non-contributing.

4. Preserve same-run annotation task behavior for refs.
   - Capture whether the selected projection was `wip` before the PDF task signal.
   - After applying the signal, allow annotation-task intake if either the pre-signal or post-signal projection is
     `wip`.
   - This preserves the existing final-closing import behavior and avoids a one-run delay after reopening.

5. Update documentation.
   - `docs/projects.md` and the README project section: document that an open `^prj` reopens terminal projects to `wip`.
   - `docs/highlights-ref-sync.md` and the README highlights section: document that unchecking an already read/abandoned
     generated `^ref` task reopens the ref to `wip`, with marker write-back still gated by `--write-pdfs`.

## Test Plan

Add focused unit tests:

- `projects.rs`: a terminal project with open `^prj` plans `status -> wip` and active-project edits run from the
  effective status.
- `projects.rs`: sub-project state treats terminal-frontmatter/open-`^prj` children as open.
- `highlights_ref/mod.rs`: unchecked `^ref` contributes `wip` from `read` and `abandoned`, contributes nothing from
  `unread` or existing `wip`, and missing `^ref` contributes nothing.
- `highlights_ref/mod.rs`: unchecked `^ref` plus a competing marker or frontmatter status edit produces a conflict.

Extend integration tests in `tests/cli.rs`:

- `bob projects sync --dry-run` previews terminal project reopen to `wip`.
- `bob projects sync` writes `status: wip`, manages `#hide` as an active project, and is idempotent on rerun.
- Parent project Sub-projects output updates a reopened child from closed ledger display back to open in the same run.
- `bob highlights scan --dry-run --write-pdfs` previews reopening a read or abandoned ref from an unchecked `^ref` task.
- `bob highlights scan` without `--write-pdfs` refuses when marker write-back is needed, matching existing
  checked/canceled task behavior.
- `bob highlights scan --write-pdfs` writes `status: wip` in the ref note, writes `- status: wip` to the PDF marker,
  leaves the generated `^ref` task unchecked, and settles on rerun.

Run verification:

- `cargo test projects`
- `cargo test highlights_ref`
- targeted `cargo test` names for the changed `tests/cli.rs` cases
- `cargo test`

## Risks and Mitigations

- Reopening should not erase intentional `waiting` or `unread` states. Mitigate by only targeting `wip` from terminal
  statuses.
- Parent project ledgers can lag if child effective state is not shared with sub-project calculation. Mitigate by using
  one project-aware lifecycle helper.
- Ref marker writes are sensitive because they mutate PDFs. Mitigate by keeping the existing `--write-pdf` /
  `--write-pdfs` guard and dry-run behavior.
- Annotation task intake ordering is easy to regress. Mitigate with tests that cover both final closing and reopening
  status transitions.
