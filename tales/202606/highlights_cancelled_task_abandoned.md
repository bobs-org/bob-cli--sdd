---
status: planned
create_time: 2026-06-06 09:21:09
prompt: sdd/prompts/202606/highlights_cancelled_task_abandoned.md
---

# Plan: Sync Cancelled Highlights PDF Tasks to Abandoned Status

## Context

`bob highlights` already has special sync behavior for the generated PDF task line inside reference notes:

```md
- [ ] #task [[lib/books/example.pdf]] [p::2] ^task
```

The current native implementation lives in `src/native/highlights_ref/mod.rs`. It parses the generated task line before
resolving marker/frontmatter sync state, then applies a checked-task contribution after the normal marker/frontmatter
resolution:

- `[x]` or `[X]` is treated as checked and contributes `status: read`.
- `[ ]` is treated as unchecked and contributes no status.
- `[-]` is currently accepted by the parser but represented as unchecked, so it is tolerated without becoming a status
  signal.

The command already supports `STATUS_ABANDONED = "abandoned"` in the canonical status vocabulary and in
marker/frontmatter validation. The requested behavior is to make a cancelled generated task line an explicit abandonment
signal:

- the PDF marker note should become `- status: abandoned`;
- the reference note `status` frontmatter should become `abandoned`;
- the existing PDF write safety contract should remain intact.

This is not a CLI surface change. No new subcommands, flags, or options are being added, so the CLI rules long memory is
not required. I did use the required audited Obsidian memory read because this changes Bob vault reference note,
frontmatter, and task workflow semantics.

## Product Semantics

1. Treat generated task markers as a three-state status affordance.
   - `[x]` or `[X]` means `status: read`.
   - `[-]` means `status: abandoned`.
   - `[ ]` means no inferred replacement status.

2. Scope the signal to the generated PDF task line only.
   - The line must still contain the stable `^task` block ID, `#task`, and a PDF wikilink.
   - Arbitrary Obsidian Tasks markers such as `[>]`, `[/]`, or `[?]` should remain unsupported for this generated line.
   - Inline metadata such as `[cancelled:: 2026-06-04]`, `[completion:: ...]`, and `[p::2]` should be preserved by
     checkbox-only rewrites.

3. Preserve existing write safety.
   - `sync --dry-run` previews note and PDF marker updates without writing.
   - Plain targeted `sync` refuses before writes when a cancelled task would require a PDF marker update and
     `--write-pdf` was not supplied.
   - Targeted `sync --write-pdf` updates the PDF marker first, recomputes the PDF SHA-256, then writes the reference
     note.
   - `scan --dry-run` previews cancelled-task marker work.
   - Writing `scan` continues to refuse per PDF unless `--write-pdfs` opts in to marker writes.

4. Keep the unchecked behavior unchanged.
   - An unchecked generated task should not downgrade `read` or `abandoned` back to `wip`/`unread`.
   - If status comes from marker/frontmatter rather than the task line, the note body should still render consistently
     with the selected projection.

## Implementation Design

### Task Status Model

Replace the boolean-only `PdfTaskCompletion` model with a neutral generated task status signal. The current struct
tracks `found`, `checked`, and `status_contributed`; that forces cancelled tasks into the unchecked bucket.

Add a small enum for parsed/generated task state, for example:

```rust
enum PdfTaskStatus {
    Missing,
    Unchecked,
    Read,
    Abandoned,
}
```

Alternatively, keep `PdfTaskLineState::Present(PdfTaskLine)` as the parser output and derive a separate status signal
during planning. The important contract is that the raw checkbox mark is retained for narrow body rewrites, and the
planner can distinguish unchecked from cancelled.

### Projection Contribution

Rename and generalize `apply_pdf_task_completion_signal()` into a status-signal helper. The helper should:

1. Return no contribution for missing or unchecked tasks.
2. Contribute `status: read` for checked tasks.
3. Contribute `status: abandoned` for cancelled tasks.
4. Leave the projection alone if it already has the target status.
5. Mark `decision.frontmatter_contributed = true` when the task signal changes the selected projection, so existing
   marker write planning continues to know the note-side user signal must be reflected back into the PDF marker.
6. Append a clear sync reason such as:
   - `checked PDF task set status read`
   - `cancelled PDF task set status abandoned`

The marker/frontmatter/base projections should continue to be normalized for deprecated `done -> read` before task
signals are applied. Cancelled-task handling should not introduce a deprecated alias for abandonment.

### Conflict Behavior

Generalize `checked_task_status_conflicts()` so it validates any task-derived target status, not just `read`.

Desired conflict behavior:

- If the base status is `wip`, marker/frontmatter are unchanged, and the task is `[-]`, select `status: abandoned`.
- If marker/frontmatter contain compatible non-status edits and the task is `[-]`, auto-merge those edits with
  `status: abandoned`.
- If the task is `[-]` but marker or frontmatter changed status to another value, such as `read`, fail before writes and
  tell the user to uncancel the task or set marker/frontmatter status to `abandoned`.
- If the task is `[x]` but marker or frontmatter changed status to `abandoned`, preserve the current conflict behavior,
  updated through the generalized helper.
- `--prefer marker` and `--prefer frontmatter` should continue to resolve marker/frontmatter disagreements, but should
  not silently discard a task-line status signal.

This keeps task-line status as an explicit user signal while preserving the existing three-way merge model.

### Body Rendering

The current rendering path uses `projection_status_is_read()` to decide whether to render or rewrite the generated task
checkbox as `[x]`; otherwise it writes `[ ]`. That should be extended to map selected status back to task marker:

- `status: read` renders/rewrites to `[x]`.
- `status: abandoned` renders/rewrites to `[-]`.
- any other supported status renders/rewrites to `[ ]`.

Replace `rewrite_pdf_task_checkbox(body, checked: bool)` with a marker-oriented helper, for example
`rewrite_pdf_task_checkbox_mark_for_status(body, projection)`, or a lower-level `projection_pdf_task_mark()` returning
`'x'`, `'-'`, or `' '`.

Keep the rewrite narrow:

- only replace the one checkbox character on the recognized generated `^task` line;
- preserve all other inline task metadata and body text;
- keep duplicate/malformed generated task lines as planning errors before writes.

### Dirty Worktree Allowance

The existing dirty-note allowance permits a tracked reference note modified only by the generated task checkbox,
optionally combined with frontmatter-only changes. It currently compares boolean checked state, which makes `[-]` and
`[ ]` look equivalent.

Update `bodies_differ_only_by_pdf_task_checkbox()` to compare the raw task marker instead of only `checked`:

- HEAD `[ ]` -> current `[-]` should be allowed as a narrow generated-task edit.
- HEAD `[x]` -> current `[-]` should be allowed as a narrow generated-task edit.
- HEAD `[-]` -> current `[ ]` should be allowed as a narrow generated-task edit.
- arbitrary body edits, managed-region edits, duplicate `^task` lines, and non-generated task changes should remain
  refused.

The frontmatter guard should stay as it is: if the dirty change includes frontmatter, the plan must have
`decision.frontmatter_contributed`.

### Reporting

Update command output labels to distinguish checked and cancelled task signals:

- keep `pdf_task: missing`, `pdf_task: unchecked`, and `pdf_task: checked`;
- add `pdf_task: cancelled` for `[-]`;
- keep `pdf_task_contribution: status=read` for checked tasks;
- add `pdf_task_contribution: status=abandoned` for cancelled tasks.

The status normalization line for deprecated `done -> read` should remain unchanged and independent of the
cancelled-task path.

### Documentation

Update `docs/highlights-ref-sync.md` and the relevant README highlights section so the generated task line is documented
as:

- checked means `status: read`;
- cancelled means `status: abandoned`;
- unchecked means no inferred replacement status;
- PDF marker write-back still requires `--write-pdf` or `scan --write-pdfs`.

Remove the older documentation statement that `[-]` behaves like unchecked.

## Implementation Steps

1. Introduce a task-status signal abstraction in `src/native/highlights_ref/mod.rs`.
   - Preserve raw checkbox mark parsing.
   - Derive missing, unchecked, read, and abandoned status states.
   - Keep parser validation narrow around `^task`, `#task`, and PDF wikilinks.

2. Generalize task contribution and conflict handling.
   - Replace checked-only helper names with status-neutral names.
   - Insert `STATUS_READ` for checked tasks and `STATUS_ABANDONED` for cancelled tasks.
   - Generalize conflict messages so they name the target status and suggested resolution.

3. Update marker write planning through the existing contribution path.
   - Ensure cancelled-task contribution sets `decision.frontmatter_contributed` when it changes the selected projection.
   - Preserve the existing `--write-pdf` and `--write-pdfs` guards.

4. Update task checkbox rendering and dirty-note allowance.
   - Render new notes with `[-]` when the selected projection is abandoned.
   - Rewrite existing generated task lines to `[x]`, `[-]`, or `[ ]` based on selected status.
   - Allow tracked dirty notes whose only body edit is changing the generated checkbox mark among accepted states.

5. Update focused unit tests in `src/native/highlights_ref/mod.rs`.
   - Parser distinguishes cancelled from unchecked.
   - Status-signal helper contributes `abandoned`.
   - Rewrite helper maps abandoned status to `[-]` and preserves inline metadata.
   - Dirty allowance accepts `[ ]`/`[x]`/`[-]` generated checkbox-only transitions and rejects unrelated body edits.

6. Update integration tests in `tests/cli.rs`.
   - Replace or rewrite the current `highlights_ref_scan_tolerates_cancelled_generated_pdf_task` expectation: dry-run
     should now report `pdf_task: cancelled`, `pdf_task_contribution: status=abandoned`, `notes_update: 1`, and
     `pdf_marker_action: would-update`.
   - Add targeted `sync --dry-run` cancelled-task coverage proving no files are modified.
   - Add plain `sync` refusal coverage when `--write-pdf` is omitted.
   - Add `sync --write-pdf` or `scan --write-pdfs` coverage proving the PDF marker contains `- status: abandoned`, the
     reference frontmatter contains `status: abandoned`, the generated task remains `[-]`, the refreshed
     `source_pdf_sha256` is recorded, and a repeat sync settles.
   - Add conflict coverage for cancelled task plus competing marker/frontmatter `status: read`.
   - Add status-source coverage where marker/frontmatter `status: abandoned` rewrites an existing generated task line to
     `[-]`.

7. Update docs.
   - Change the generated task section in `docs/highlights-ref-sync.md`.
   - Update README highlights summary if it mentions task-derived status.
   - Keep supported status vocabulary unchanged: `unread`, `wip`, `read`, `abandoned`, `legacy`.

8. Verify.
   - `cargo fmt --check` after formatting if needed.
   - `cargo test highlights_ref_task`
   - `cargo test --test cli highlights_ref_task`
   - `cargo test --test cli highlights_ref_scan_tolerates_cancelled_generated_pdf_task` or the renamed replacement test.
   - If focused tests pass quickly, run `cargo test highlights_ref` and the broader `cargo test`.
   - `git diff --check`

## Risks and Mitigations

- Risk: `[-]` lines with old inline metadata get rewritten too aggressively. Mitigation: keep rewrites to the single
  checkbox character and add metadata preservation tests.
- Risk: unchecked and cancelled remain conflated in dirty-file safety because the old helper uses a boolean checked
  field. Mitigation: compare raw checkbox marks in the narrow body-diff helper.
- Risk: task status conflicts become confusing once both `read` and `abandoned` are possible. Mitigation: use one
  generalized conflict message that names the task-derived target status.
- Risk: `scan` starts writing PDFs unexpectedly. Mitigation: preserve the existing `--write-pdfs` opt-in and update
  dry-run expectations before writing behavior.
- Risk: documentation still says cancelled tasks behave like unchecked. Mitigation: update docs and tests in the same
  change, and run a focused `rg` for `cancelled`, `canceled`, and `pdf_task`.

## Acceptance Criteria

- A generated `[-] #task [[...pdf]] ... ^task` line is reported as `pdf_task: cancelled`.
- Dry-run output shows `pdf_task_contribution: status=abandoned` when the cancelled task changes the selected
  projection.
- Targeted `sync --write-pdf` and `scan --write-pdfs` write `status: abandoned` to both the PDF marker note and
  reference-note frontmatter.
- The generated reference-note task line is `[-]` whenever the selected projection has `status: abandoned`.
- Plain `sync` and writing `scan` still refuse before writes when a PDF marker update is needed and PDF writes were not
  explicitly enabled.
- Checked-task `status: read`, unchecked no-inference behavior, deprecated `done -> read` normalization, and
  marker/frontmatter conflict handling still pass their existing tests.
