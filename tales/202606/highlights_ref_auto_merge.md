---
create_time: 2026-06-03 19:27:10
status: done
---
# Plan: Safe Auto-Merge for `bob highlights-ref`

## Context Reviewed

- Project memory says this is an ephemeral `bob-cli_<N>` workspace and work should stay inside this clone.
- Long-term CLI rules were read with `sase memory read long/cli_rules.md`; any CLI surface changes need excellent help,
  alphabetically sorted options, and clear output.
- `docs/highlights-ref-sync.md` documents the current contract:
  - `sync <pdf>` compares the PDF marker note with `~/bob/ref/...md` frontmatter.
  - Frontmatter edits require `bob highlights-ref sync --write-pdf <PDF>` before they are reflected back into the PDF
    marker.
  - If marker and frontmatter both changed differently, the command currently fails unless `--prefer marker` or
    `--prefer frontmatter` is supplied.
  - Writing scans currently do not pass `--write-pdf`; scheduled scan automation stays note-only.
- `src/native/highlights_ref/mod.rs` currently stores only `highlights_marker_hash`, not the previous projection itself.
  That hash is enough to detect that both sides changed, but not enough to know whether their changes touched the same
  fields.
- `ensure_safe_to_write()` rejects dirty Git paths for any existing note or PDF that would be modified. In the real
  frontmatter-edit workflow, the ref note is intentionally dirty before `sync --write-pdf`, so this guard can block the
  exact reconciliation the command requires.
- Existing tests already cover one-sided marker changes, frontmatter-to-PDF write-back, dirty target refusal, and manual
  conflict resolution with `--prefer`.

## Problem

There are two related conflict surfaces:

1. Semantic marker/frontmatter conflicts. If both current projections differ from `highlights_marker_hash`, the command
   cannot distinguish a real same-field conflict from a safe non-overlapping edit. Example: the PDF marker changed
   `status`, while note frontmatter added `title`.
2. Git dirty-file conflicts. A user editing frontmatter in `~/bob/ref/...md` makes the note dirty. The follow-up
   `sync --write-pdf` needs to update the PDF marker and refresh pipeline frontmatter such as `highlights_marker_hash`,
   but the dirty-target guard can refuse to touch the note.

The command should merge automatically only when it can prove the result. Ambiguous cases should still fail without
modifying either side.

## Goals

- Auto-merge non-overlapping marker/frontmatter edits using a real three-way base.
- Let the intended frontmatter-edit workflow complete without requiring a commit between editing the note and running
  `sync --write-pdf`.
- Preserve the current hard-failure behavior for same-field conflicts, missing required fields, unrelated dirty files,
  staged changes, untracked target notes, and races where files change after planning.
- Keep dry-run read-only and make dry-run output show when a merge would happen.
- Keep existing notes backward compatible; notes that only have `highlights_marker_hash` should continue using the
  current conflict behavior until a successful sync writes the new merge base.
- Avoid adding a new CLI option for the first version. A safe, provable merge can be the default behavior; `--prefer`
  remains the explicit escape hatch for true conflicts.

## Design

### 1. Store a merge base projection

Add a new pipeline-owned frontmatter field, for example:

```yaml
highlights_marker_base: '{"parent":"[[obsidian]]","status":"wip","title":"Example"}'
```

The exact field name can be refined during implementation, but the contract should be:

- It stores the canonical synced user-property projection from the last successful sync.
- It is excluded from marker sync with the other pipeline fields.
- It is rendered deterministically, using compact JSON in a frontmatter string so the existing line-oriented frontmatter
  parser does not need multi-line map support.
- It is parsed back into the same `Projection` shape used by marker and frontmatter sync.
- `highlights_marker_hash` remains for compatibility and quick unchanged checks.

On old notes without this field:

- Preserve current behavior for conflict cases.
- On any successful sync, write the new base field so future conflicts can be merged field-by-field.

### 2. Replace conflict-only decision logic with a three-way resolver

Introduce a resolver that works from:

- `base_projection`: the last successful projection, from `highlights_marker_base` when available.
- `marker_projection`: current canonical projection parsed from the PDF marker.
- `frontmatter_projection`: current canonical projection parsed from the note frontmatter.

For each key in the union of base, marker, and frontmatter:

- If neither side changed from base, keep the base/current value.
- If only the marker changed, take the marker value.
- If only frontmatter changed, take the frontmatter value.
- If both changed to the same value, take that value.
- If both deleted the key, omit it.
- If one side deleted a key and the other side kept the base value, delete it.
- If one side deleted a key and the other side changed it, treat that as a conflict.
- If both sides changed the same key to different values, treat that as a conflict.

After merging:

- Validate required `status` and `parent` on the merged projection.
- Recompute `highlights_marker_hash` from the merged projection.
- Recompute `highlights_marker_fields` from the merged projection so unknown fields keep round-tripping correctly.
- Render the note and rendered marker from the merged projection.

The resolver should return a richer result than the current `SyncDecision`, such as:

- selected projection
- reason string
- whether marker contributed changes
- whether frontmatter contributed changes
- field-level conflict details

This lets reports say `sync_source: auto-merge` or similar, while still preserving current one-sided reasons for simple
cases.

### 3. Keep PDF writes explicit

Any result that requires changing the PDF marker still requires `--write-pdf` unless it is a dry-run. This includes:

- frontmatter-only edits
- merged edits where frontmatter contributed at least one field
- `--prefer frontmatter`

If a merge only pulls marker-side changes into the note, no PDF write is needed.

`scan` remains note-only because it does not pass `write_pdf`. If scan discovers that a frontmatter contribution would
need a PDF marker write, it should fail or dry-run-report exactly as `sync` does today rather than silently skipping the
PDF update.

### 4. Make dirty safety content-aware for the intended frontmatter workflow

Keep the existing dirty-target refusal as the default, but add a narrow allow path for tracked ref notes that are dirty
because of frontmatter edits the command is intentionally reconciling.

Allow a dirty note write only when all of these are true:

- The note path is under the configured ref directory and is the plan's target note.
- Git status shows an unstaged modification only, not staged, untracked, deleted, renamed, or conflicted status.
- The plan's current note contents match the bytes on disk immediately before writing.
- Comparing Git `HEAD` for the note to the current worktree version shows changes confined to frontmatter. Body changes,
  including edits inside the managed highlights region, still cause refusal.
- The sync result uses frontmatter as a source, either frontmatter-only or an auto-merge where frontmatter contributed
  fields.

For PDFs:

- Do not relax dirty PDF handling in the first implementation unless it is necessary for a focused test case.
- If a future relaxation is needed, use an optimistic content check: the current PDF SHA-256 must still equal the hash
  read during planning, and `--write-pdf` must be present.

This keeps the common workflow unblocked while preserving the guard against accidentally rewriting unrelated local
changes.

### 5. Add race checks before writes

Before `execute_pdf_sync()` writes either file:

- Re-read the note if it will be written and verify it still matches the note contents used during planning.
- Rehash the PDF if it will be written and verify it still matches the PDF hash used during planning.
- If either check fails, abort with a clear "changed during sync; rerun" style error.

These checks are useful even when Git is clean because Obsidian, Highlights, cron, or another command can change files
between planning and writing.

### 6. Report merge decisions clearly

Update reports without adding noise:

- For dry-run and write reports, show the merge reason when an auto-merge happens.
- For conflicts, include field names and a compact side-by-side summary, for example:

```text
marker/frontmatter conflict:
  status: marker="done", frontmatter="paused", base="wip"
rerun with --prefer marker or --prefer frontmatter after reviewing both sides
```

Avoid dumping large values. Truncate long strings and lists in diagnostics.

## Implementation Steps

1. Add projection snapshot support.
   - Add the new pipeline field constant and include it in `PIPELINE_FIELDS`.
   - Add deterministic projection-to-JSON and JSON-to-projection helpers.
   - Add `ParsedNote::marker_base_projection()`.
   - Render the base projection on every successful note render.

2. Implement the three-way merge resolver.
   - Keep the existing hash-only path for notes without a base snapshot.
   - Add field-level merge logic and conflict reporting.
   - Update `plan_pdf_sync()` to use the resolver's selected projection.
   - Treat `marker_write_needed` as "rendered merged marker differs from current marker".

3. Tighten write safety.
   - Extend the write preflight so dirty entries can be classified by path and Git status code.
   - Add the frontmatter-only dirty-note allowance.
   - Add pre-write note/PDF race checks in or immediately before `execute_pdf_sync()`.

4. Update docs.
   - Document `highlights_marker_base` as an internal pipeline field.
   - Explain that non-overlapping marker/frontmatter edits auto-merge.
   - Explain that same-field conflicts still require review and `--prefer`.
   - Clarify the frontmatter edit workflow: edit the ref note, run `bob highlights-ref sync --write-pdf <PDF>`, and the
     command may update the dirty ref note only when the dirty changes are frontmatter-only and current.

5. Update tests.
   - Unit tests for snapshot serialization and parsing.
   - Unit tests for merge cases: marker-only, frontmatter-only, same-value both-sides edit, non-overlapping both-sides
     edit, delete-vs-unchanged, delete-vs-change conflict, same-key different-value conflict.
   - CLI test that initial sync writes the base snapshot and repeat sync stays idempotent.
   - CLI test where marker changes `status` and frontmatter adds `title`; `sync --write-pdf` auto-merges, updates both
     note and PDF marker, and settles on the next run.
   - CLI test where both sides change `status` differently; command fails and leaves both files unchanged.
   - Git-backed CLI test where a tracked ref note has an unstaged frontmatter-only edit; `sync --write-pdf` succeeds.
   - Git-backed CLI test where a tracked ref note has a body edit; command still refuses as dirty.
   - Dry-run tests confirming no file changes and clear merge reporting.

6. Verify.
   - `cargo fmt --check`
   - Focused highlights-ref tests while iterating, for example `cargo test highlights_ref`
   - Full `cargo test`
   - `cargo clippy --all-targets --all-features`
   - `git diff --check`

## Risks and Mitigations

- Base snapshot bloat: store compact JSON and only user-sync fields, not pipeline fields.
- Obsidian property noise: keep the field pipeline-owned and documented. If it becomes too noisy, move the snapshot to a
  sidecar cache in a follow-up.
- False safe merges without a base: do not auto-merge old notes until a real base snapshot exists.
- Deletion ambiguity: treat delete-vs-change as a conflict.
- Dirty-note overreach: allow only unstaged tracked frontmatter-only changes, and fail for body edits or staged changes.
- Race conditions: compare current file bytes/hashes to planning-time inputs immediately before writing.
- Backward compatibility: keep `highlights_marker_hash` semantics and current `--prefer` behavior for unresolved
  conflicts.
