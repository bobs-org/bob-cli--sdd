---
create_time: 2026-06-08 07:55:03
status: done
prompt: sdd/prompts/202606/no_highlight_task_property.md
---
# Plan: Remove New highlight_task Task Properties Without Losing Processed Tracking

## Feasibility Conclusion

Yes, but not by removing durable provenance entirely.

The current `[highlight_task:: ...]` field is not just cosmetic metadata. It is the durable marker that lets
`bob highlights` recognize an annotation-created task after the task has been completed, cancelled, moved to another
note, or archived by `bob move-done-tasks`, without writing processed state back into the PDF or sidecar.

To remove the task property while preserving the same behavior, the created task still needs a durable identifier that
moves with the task line. The best replacement is to make the existing source backlink carry a task-specific source
anchor. That keeps the user-facing task free of the `highlight_task` Dataview property while preserving processed-task
tracking through ordinary Obsidian link syntax.

## Goals

- Stop rendering `[highlight_task:: ...]` on newly-created annotation tasks.
- Preserve the existing behavior:
  - only `wip` PDFs create annotation tasks;
  - `@name` route suffixes append to existing root-level `~/bob/name.md` notes;
  - reruns do not duplicate active, completed, cancelled, routed, or archived tasks;
  - task text, checkbox state, and user-added task properties remain user-owned after creation;
  - no processed marker is written back to the PDF or sidecar;
  - the recent skip-the-vault-scan optimization remains intact when there are no candidates.
- Keep old tasks that already contain `[highlight_task:: ...]` recognized without rewriting them.

## Non-Goals

- Do not add a new CLI option or subcommand.
- Do not auto-create routed notes.
- Do not bulk-edit existing user task lines just to remove old `[highlight_task:: ...]` fields.
- Do not weaken duplicate detection to source text alone.

## Recommended Design

### 1. Replace the rendered property with a task-specific source anchor

Today, created tasks link to the annotation block:

```md
- [ ] #task Follow up [[ref/books/example#^h-abc123|source]] [highlight_task:: ...] [created::2026-06-08]
```

Change new task rendering to omit the property and point at a task-specific source block instead:

```md
- [ ] #task Follow up [[ref/books/example#^ht-abc123|source]] [created::2026-06-08]
```

The `ht-...` block id is deterministic and represents the exact source task occurrence. It should be derived from the
same stable inputs the property uses today:

- vault-relative reference note path;
- source annotation block id;
- normalized task identity.

Use a prefix distinct from normal annotation blocks, such as `ht-`, so scanners can tell source-task anchors apart from
annotation-level `h-...` blocks.

Use vault-relative source links for both routed tasks and same-note reference tasks. The alias keeps the rendered
Obsidian view compact, and the vault-relative target keeps the source note recoverable if the task later moves to
`done/` or another note.

### 2. Render resolvable source-task anchors in the managed Highlights region

Keep the existing annotation block id (`^h-...`) exactly as it is. Additionally, when a rendered highlight comment or
standalone note contains a `#task` source line, attach the corresponding task-specific block id to that rendered source
line in the managed `<!-- highlights:begin -->` region.

For example:

```md
> [comment] #task Follow up ^ht-abc123

^h-def456
```

This makes the created task backlink both durable and resolvable. The source anchor lives in generated reference-note
content, not in the PDF or sidecar.

Render these source-task anchors independently of current PDF status. A PDF may move from `wip` to `read` after tasks
are created; existing source links should remain resolvable even though non-`wip` PDFs no longer create new tasks.

For duplicate identical task bullets within the same annotation, preserve current duplicate behavior: only one task is
accepted. Render the shared source-task anchor on the first matching source line to avoid duplicate block ids in the
generated region.

### 3. Change the processed index to read source-task links first

Extend the vault-wide processed-task scanner to collect three kinds of processed evidence:

- `source_task_anchors`: task lines containing a source backlink to `#^ht-...`;
- `legacy_highlight_task_ids`: existing `[highlight_task:: ...]` values, for backwards compatibility only;
- `legacy_identities`: normalized task text after stripping source backlinks, route suffixes, and Obsidian task
  properties, preserving the current fallback for pre-marker tasks.

Candidate acceptance should check in this order:

1. source-task anchor key already seen;
2. old `highlight_task` property id already seen;
3. legacy normalized identity already seen.

When accepting a new task during a run, insert its source-task anchor key and legacy identity into the in-memory index
so parallel or multi-PDF scans keep their current deterministic no-duplicate behavior.

Keep the old processed-id generator internally, but rename its role to make it clear that it is now only a legacy
property id used to recognize tasks written by earlier versions.

### 4. Keep the source-link stripper and identity behavior

`annotation_task_identity()` should continue to strip block backlinks and Obsidian task properties before computing
legacy identity. This keeps old link-bearing tasks, new task-specific-link tasks, and property-bearing legacy tasks all
comparable by text when the fallback is needed.

The primary processed marker for new tasks should be the `ht-...` source anchor, not the normalized task text. This is
the piece that preserves current robustness when a user edits the task prose after creation but leaves the source link
in place.

### 5. Update docs and examples

Update `README.md` and `docs/highlights-ref-sync.md` to say:

- new annotation-created tasks no longer carry `[highlight_task:: ...]`;
- the source backlink points to a task-specific generated source anchor;
- old `[highlight_task:: ...]` fields are still recognized but are no longer written;
- removing the source backlink from a moved or heavily edited task removes the only durable no-property marker.

Do not document a migration step that rewrites existing tasks. Existing user lines should remain stable unless the user
asks for a cleanup command later.

## Rejected Alternatives

### Pure normalized-text matching

This is not equivalent. It fails when the created task text is edited after creation, and it is the reason the durable
property was introduced in the first place.

### Annotation-level source links only

The existing `h-...` annotation block is not enough. Multiple `#task` bullets can come from one annotation, and a
same-note `[[#^h-...]]` link loses the reference-note path if the task is moved to `done/`.

### External processed ledger

A separate JSON or cache file avoids task-line metadata, but it no longer moves with the task. It also changes deletion
semantics: deleting a task would not allow recreation unless the ledger was manually edited.

### Created-task block ids as the primary marker

Rendering something like `^ht-...` directly on the created task would work and is still better than a Dataview property,
but it adds another visible token to the task line. Use it only as a fallback if task-specific source anchors inside
rendered highlight/comment blocks prove unreliable in Obsidian.

## Implementation Steps

1. Add a task-specific source-anchor model.
   - Add `source_task_block_id` or equivalent to `AnnotationTaskCandidate`.
   - Compute it deterministically from the reference note path, source annotation block id, and normalized identity.
   - Keep the existing property-id computation internally for legacy matching only.

2. Thread source-task anchors through rendering.
   - Teach the sidecar highlight renderer to identify rendered source task lines using the same parsing rules as
     candidate extraction.
   - Append the matching `^ht-...` block id to those generated source lines.
   - Keep the existing annotation-level `^h-...` blocks.

3. Stop writing the property on new tasks.
   - Update `render_annotation_task_line()` and the test-only insertion helper to omit `[highlight_task:: ...]`.
   - Render source links as vault-relative `[[ref/...#^ht-...|alias]]` for both reference-note and routed targets.

4. Update processed-index parsing.
   - Add source-link extraction for task backlinks targeting `#^ht-...`.
   - Continue parsing existing `[highlight_task:: ...]` fields.
   - Keep legacy identity fallback.
   - Update `ProcessedTaskIndex::accept()` around source-anchor keys first, legacy property ids second, and identities
     last.

5. Preserve the no-candidate optimization.
   - The vault-wide processed index should still be built only when annotation-task candidates exist.
   - Source-task anchors in the managed highlights region do not require the processed index.

6. Update tests.
   - Unit: task candidate computes a source-task block id and legacy property id.
   - Unit: rendered annotation blocks include `^ht-...` for task source lines and keep `^h-...`.
   - Unit: rendered created task lines omit `[highlight_task:: ...]` and link to `#^ht-...`.
   - Unit: processed index recognizes new source-task links, old properties, completed tasks, cancelled tasks, indented
     tasks, and `done/` archive notes.
   - CLI: regular same-note task creation no longer writes `[highlight_task:: ...]`, and its source link resolves.
   - CLI: routed task creation no longer writes `[highlight_task:: ...]`.
   - CLI: completed, cancelled, archived, and edited-prose tasks are not recreated as long as the source-task backlink
     remains.
   - CLI: legacy tasks with existing `[highlight_task:: ...]` are not recreated.
   - CLI: no-candidate sync still skips the vault-wide processed scan.

7. Update docs.
   - Remove examples that show `[highlight_task:: ...]` on new tasks.
   - Add a compatibility note for older tasks that already have the property.
   - Explain that the source backlink is now the durable processed marker.

8. Verify.
   - `cargo fmt --check`
   - `cargo test annotation_task`
   - `cargo test --test cli highlights_ref_sync_creates_tasks_from_pdf_note_task_bullets`
   - `cargo test --test cli highlights_ref_sync_routes_annotation_tasks_to_existing_root_note`
   - `cargo test --test cli highlights_ref_sync_skips_vault_scan_when_no_annotation_candidates`
   - `cargo test --test cli highlights_ref`
   - `cargo test`
   - `cargo clippy --all-targets`

## Risks and Mitigations

- Source-task block ids in rendered blockquotes need practical validation in Obsidian. If they do not resolve reliably,
  fall back to a created-task `^ht-...` block id marker instead of reintroducing a Dataview task property.
- The first run after this change may update generated Highlights regions to add source-task anchors. This is managed
  content and should be visible in dry-run output.
- If a user deletes the source backlink from a moved or edited task, no no-property design can prove that the original
  source was processed. The legacy identity fallback still covers unchanged text, but exact robustness requires some
  durable marker to remain on the moved task line.
