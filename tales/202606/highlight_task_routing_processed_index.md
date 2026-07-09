---
create_time: 2026-06-08 07:08:32
status: done
prompt: sdd/prompts/202606/highlight_task_routing_processed_index.md
---
# Plan: Highlight Task Routing and Processed-Task Tracking

## Context

`bob highlights` currently turns `#task` bullets from PDF sidecar highlight comments or standalone notes into unchecked
top-level Obsidian tasks in the generated reference note. The task is inserted immediately after the generated PDF
reading-status task (`^task`), carries `[created::YYYY-MM-DD]`, and links back to the rendered highlight block with the
`🔖` source backlink.

Duplicate prevention is currently local to the generated reference note body: the planner normalizes existing top-level
tasks in that note and avoids inserting matching candidate text. That works while tasks stay in the reference note, but
it cannot recognize tasks that have been moved elsewhere, archived by `bob move-done-tasks`, or intentionally routed to
a different note.

The new behavior should:

- Route a task whose final whitespace-delimited token is a strict `@<name>` token to `~/bob/<name>.md`.
- Only extract/create annotation tasks for PDFs whose resolved synced status is `wip`.
- Recognize tasks as already processed after they are completed, canceled, or moved, without writing any processed
  marker back into the PDF or PDF note annotation.

## Design Decisions

1. Treat `@<name>` as a routing suffix, not task text.
   - Recognize only a final token matching `@([A-Za-z0-9][A-Za-z0-9_-]*)`.
   - Strip the routing suffix before rendering the Obsidian task and before computing identity.
   - Tokens with punctuation, slashes, dots, empty names, or path traversal content are not route tokens and remain
     ordinary task text. This keeps target resolution root-only and avoids surprising paths.

2. Route only to existing root-level vault notes in the first implementation.
   - `@alice` targets `config.bob_dir.join("alice.md")`.
   - If the target path is missing or is a directory, planning that PDF fails with a clear message asking the user to
     create the note first.
   - This follows the Obsidian memory requirement that newly-created notes under `~/bob` need `parent` frontmatter; the
     command should not guess a parent for arbitrary `@name` notes.

3. Gate annotation task extraction on resolved status.
   - Resolve marker/frontmatter/PDF-task status exactly as today.
   - After `apply_pdf_task_status_signal`, only build annotation task candidates if the synced projection has
     `status: wip`.
   - Continue rendering reference notes and highlights for non-`wip` PDFs; just skip annotation task creation.

4. Add an Obsidian-side processed marker to newly-created tasks.
   - Add a stable inline field such as `[highlight_task:: <id>]` to every newly-created annotation task.
   - Compute `<id>` from stable source/task inputs, for example:
     `sha256("v1\0" + vault-relative reference-note path + "\0" + source block id + "\0" + normalized task identity)`,
     shortened only if the collision risk remains negligible.
   - Keep `annotation_task_identity` stripping all Obsidian inline fields, so this field never changes duplicate
     matching by task text.
   - This marker moves with the task when `bob move-done-tasks` archives it, and does not require modifying the PDF.

5. Build a vault-wide processed-task index.
   - Scan all Markdown files under `config.bob_dir`, including `done/`, excluding hidden directories such as `.git`.
   - Parse every Markdown task line, regardless of indentation and checkbox state.
   - Record all `[highlight_task:: <id>]` values as authoritative processed ids.
   - Also record normalized legacy identities from existing `#task` task lines after stripping source backlinks, task
     properties, and route suffixes. This preserves idempotency for tasks created before the new marker existed.
   - During one run, insert accepted new ids/identities into the in-memory index immediately so duplicate candidates in
     the same `scan` run cannot create duplicate tasks.

6. Preserve source backlinks.
   - Reference-note tasks can keep the existing same-file `[[#^h-...|🔖]]` source link.
   - Routed tasks need a full vault-relative source link, e.g. `[[ref/books/task-notes#^h-...|🔖]]`, because their
     source highlight block lives in the generated reference note.
   - The new `[highlight_task:: ...]` field is the durable processed marker; source links remain for navigation.

7. Finalize annotation task writes after per-PDF planning.
   - Refactor `plan_pdf_sync` so it resolves/render highlights as today but returns annotation task creation requests
     instead of directly mutating the note body.
   - Add a finalization pass that receives the successful plans in deterministic PDF order, builds the vault-wide
     processed index once, filters new requests, groups accepted task lines by target note path, and applies writes.
   - For the reference note target, insert accepted tasks after the generated `^task` line using the existing insertion
     behavior.
   - For routed target notes, append accepted tasks as top-level task lines at EOF, preserving the existing note content
     and line ending style as much as practical.
   - This avoids scan-time write races when multiple PDFs route tasks to the same `@name` note.

## Implementation Steps

1. Introduce task routing and provenance types.
   - Extend `AnnotationTaskCandidate` with `target: AnnotationTaskTarget`, `source_ref_note_path`, and `processed_id`.
   - Add route parsing helpers:
     - `split_annotation_task_route_suffix(task_text) -> (task_text_without_route, Option<RouteName>)`
     - `route_name_to_note_path(config, route_name) -> Result<PathBuf>`
   - Update candidate extraction to strip route suffix before `#task` identity checks and rendering.

2. Gate candidate extraction by status.
   - Add `projection_status_is(&synced_projection, STATUS_WIP)` check in `plan_pdf_sync`.
   - Return no annotation task requests for non-`wip` PDFs.
   - Keep validation/status conflict behavior unchanged.

3. Add processed id generation and parsing.
   - Add constants for the inline field key, e.g. `HIGHLIGHT_TASK_FIELD: &str = "highlight_task"`.
   - Generate a deterministic id from reference note path, source block id, and normalized identity.
   - Add helper(s) to extract inline property values by key from task text.

4. Add the vault-wide processed index.
   - Implement a Markdown scanner local to `highlights_ref` or share a small internal helper if appropriate.
   - Include `done/` and nested notes; skip hidden directories.
   - Parse all Markdown task lines, not just top-level unchecked tasks.
   - Store:
     - `processed_ids: BTreeSet<String>`
     - `legacy_identities: BTreeSet<String>`
   - Seed the index from current vault contents before accepting new task requests, then update it as requests are
     accepted during finalization.

5. Refactor planning/finalization.
   - Split current `insert_missing_annotation_tasks` usage out of `plan_pdf_sync`.
   - Add `finalize_annotation_task_plans(config, plans)` used by both `sync_pdf` and `scan_library` after successful
     per-PDF planning and before report/write safety checks.
   - Recompute each affected reference note's `rendered_body`, `stable_rendered_note`, and `stable_note_action` after
     task insertion.
   - Add a structure for extra routed note writes with path, original contents, rendered contents, and action.
   - Make `execute_pdf_sync` write both the generated reference note and any routed task note writes attached to that
     plan, using unchanged-content checks for every touched note.

6. Update collision and dirty-write safety.
   - Keep existing reference-note output collision validation.
   - Add grouped routed writes so multiple plans can target the same note without competing renders.
   - Extend `ensure_safe_to_write` to include routed task note paths.
   - Keep the existing dirty-file allowance scoped to generated reference notes under `ref/`; routed user notes should
     be refused when dirty unless the implementation can prove the planned preimage is exactly current and no unrelated
     git changes would be swept in.

7. Update reporting.
   - Add concise plan/write counts for annotation tasks created/skipped and routed task note writes.
   - Make scan summary note counts include routed task-note creates/updates if any are allowed; with the existing
     "target note must exist" decision, routed note actions should usually be `update`.
   - Preserve existing report lines where tests and scripts likely depend on them.

8. Update tests.
   - Unit tests:
     - Route suffix parsing accepts `@alice`, strips it from rendered task text/identity, and rejects unsafe tokens.
     - Candidate extraction computes target path and processed id.
     - Processed index recognizes active, completed, canceled, indented, and archived `done/` tasks.
     - Legacy identity fallback prevents recreation of pre-marker tasks.
     - Non-`wip` projections return no annotation task requests.
   - CLI tests:
     - `sync` routes `- #task Follow up @alice` to existing `alice.md`, strips `@alice`, writes a full source backlink,
       and does not insert the task into the reference note.
     - Re-running after checking/canceling the routed task does not duplicate it.
     - Re-running after moving that task to `done/alice_done.md` does not duplicate it.
     - A PDF with `status: unread`, `read`, or `abandoned` does not create annotation tasks even if sidecar bullets
       contain `#task`.
     - `scan -j >1` with multiple PDFs routing to the same existing note produces one merged deterministic append and no
       lost writes.
     - Missing routed target note fails with a clear per-PDF planning error and no partial writes for that PDF.

9. Update documentation.
   - Update `README.md` and `docs/highlights-ref-sync.md` to document:
     - `@name` route suffix syntax and strict filename rules.
     - Routed target notes must already exist and live at vault root.
     - Route suffix is stripped from created task text.
     - Tasks are only created for PDFs whose resolved status is `wip`.
     - Created tasks carry `[highlight_task:: ...]` for Obsidian-side processed tracking.
     - Completed, canceled, and `move-done-tasks` archived tasks remain recognized without PDF edits.

10. Verify.
    - Run `cargo fmt --check`.
    - Run focused unit/CLI tests around highlights annotation tasks.
    - Run `cargo test`.
    - Run `cargo clippy --all-targets`.

## Risks and Tradeoffs

- Requiring target notes to exist avoids bad frontmatter guesses, but it means `@name` routing is not auto-creating
  notes. This is a deliberate first version because the project memory requires `parent` frontmatter for new notes.
- Legacy tasks without `[highlight_task:: ...]` can only be recognized by normalized text identity. That preserves
  current behavior but cannot survive arbitrary user edits to old task text. New tasks are robust because the processed
  id moves with the task.
- A vault-wide legacy identity fallback may suppress a genuinely distinct task with identical normalized text. The
  processed id avoids this for new tasks; the fallback exists only to prevent duplicate recreation of pre-marker tasks.
- Scan finalization is a larger refactor than adding route parsing alone, but it is necessary to handle multiple PDFs
  targeting the same routed note without races or overwrite hazards.
