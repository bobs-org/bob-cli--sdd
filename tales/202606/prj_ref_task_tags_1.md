---
create_time: 2026-06-15 16:08:33
status: done
---
# Plan: Add `#prj` and `#ref` to Main Lifecycle Tasks

## Goal

Start tagging the special project and reference lifecycle tasks as typed tasks:

```md
- [ ] #task #prj <completion criteria> #hide ^prj
- [ ] #task #ref [[lib/.../paper.pdf]] #hide ^ref
```

The stable block IDs, `^prj` and `^ref`, remain the command-facing lifecycle anchors. The new `#prj` and `#ref` tags are
additional task tags placed immediately after the existing `#task` token so Obsidian task views can distinguish these
machine-managed main note tasks from ordinary follow-up tasks.

## Context Reviewed

- Project short memory: `memory/short/sase.md`.
- Required Obsidian long memory via:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault and note workflow context before changing bob project/reference task tagging and vault notes"`.
- CLI rules long memory via:
  `sase memory read long/cli_rules.md --reason "Need CLI command behavior rules before updating bob projects/highlights output and tests"`.
- Plan workflow from `/home/bryan/.codex/skills/sase_plan/SKILL.md`.
- Repository code and docs:
  - `src/native/projects.rs`
  - `src/native/highlights_ref/mod.rs`
  - `README.md`
  - `docs/projects.md`
  - `docs/highlights-ref-sync.md`
  - `tests/cli.rs`
- Prior design records:
  - `sdd/tales/202606/project_task_links_to_prj.md`
  - `sdd/tales/202606/ref_task_block_id_migration.md`
  - `sdd/tales/202606/highlights_ref_pdf_task_line.md`
  - `sdd/tales/202606/projects_prj_priority_sync.md`
- Live vault instructions: `~/bob/AGENTS.md`.

## Current Findings

### Code

- `bob projects` recognizes the special project task by an exact trailing `^prj` token plus a valid checkbox task with
  `#task`. It rewrites the line only for lifecycle sync behavior such as adding/removing `#hide`, removing stale
  `[scheduled::...]`, and maintaining the generated sub-projects child line.
- `PROJECT_TASK_SHAPE` and docs currently show `- [ ] #task <completion criteria> #hide ^prj`.
- `task_description()` strips `#task` and `#hide`, but not a future `#prj`; without a parser update, the displayed
  project description and placeholder checks would include the new tag.
- `bob highlights` creates new reference-note PDF task lines in `default_note_body()` as
  `- [ ] #task [[...pdf]] #hide ^ref`.
- `parse_pdf_task_line()` recognizes the generated reference task by exact `^ref`, `#task`, and a PDF wikilink. It does
  not require `#hide`, so adding `#ref` is parser-compatible.
- Annotation follow-up tasks created from highlight comments are separate user tasks and should not receive `#ref`.

### Live Vault Survey

- Exact `^prj` task lines currently tagged in `~/bob`: 12, including `_templates/new_project.md`.
- Exact `^ref` task lines currently tagged in `~/bob/ref`: 30.
- Exact untagged lifecycle task lines remaining: 0 for `^prj`, 0 for `^ref`.
- Similar-but-not-main block IDs exist, such as `^prj-sibling-state` and `^ref-notes`; those must stay untouched.
- Historical text contains `#prj/...` and `#ref/...` topic markers; those are not lifecycle task tags and must stay
  untouched.
- The vault is dirty with broad pre-existing user/sync edits, including many target files. The two files selected for an
  isolated commit, `bob_projects.md` and `bob_projects_clean_bad_links.md`, currently show only the `#prj` insertion in
  their diffs.

## Design

### Main Task Contract

1. Project lifecycle tasks should render and be documented as:

   ```md
   - [ ] #task #prj <completion criteria> #hide ^prj
   ```

2. Reference lifecycle tasks should render and be documented as:

   ```md
   - [ ] #task #ref [[lib/.../file.pdf]] #hide ^ref
   ```

3. `#prj` and `#ref` are additive tags. The commands should continue to use exact `^prj` and `^ref` block IDs as the
   special-treatment signal.
4. The parsers should tolerate both old and new lines so a partially migrated vault is readable and old notes do not
   fail just because they lack the new type tag.
5. Do not add `#ref` to annotation-derived follow-up tasks, routed tasks, or ordinary user tasks inside a reference
   note.

## Repository Changes

1. Update project task shape and description handling.
   - Change `PROJECT_TASK_SHAPE` to include `#task #prj`.
   - Add a project-task tag constant, e.g. `PROJECT_TASK_TAG: &str = "#prj"`.
   - Teach `task_description()` to strip `#prj` from the parsed description, just as it strips `#task` and `#hide`.
   - Keep malformed/missing `^prj` detection anchor-based and backward-compatible.

2. Update project docs and tests.
   - Update `docs/projects.md`, `README.md`, help examples, warning details, and test fixtures to show the new shape.
   - Add or adjust parser tests proving `#task #prj ... ^prj` parses cleanly and descriptions do not include `#prj`.
   - Keep at least one compatibility test for an old `#task ... ^prj` line unless existing coverage already proves it.

3. Update generated reference-note body rendering.
   - Change `default_note_body()` in `src/native/highlights_ref/mod.rs` to emit `#task #ref [[...]] #hide ^ref`.
   - Add a reference-task tag constant, e.g. `PDF_TASK_KIND_TAG: &str = "#ref"`.
   - Keep `parse_pdf_task_line()` tolerant of old lines without `#ref`.

4. Update reference docs and tests.
   - Update `README.md`, `docs/highlights-ref-sync.md`, error-message examples, and unit/integration fixtures that show
     generated `^ref` task lines.
   - Add or adjust tests proving new generated notes contain `#task #ref`.
   - Keep legacy parser cases for `#task [[...]] ^ref` and `#task [[...]] #hide ^ref`.

5. Do not rewrite historical SDD records except this new plan. Existing `sdd/tales` and `sdd/prompts` files record prior
   decisions and should remain history.

## Vault Migration

1. Preflight.
   - Re-run `git -C ~/bob status --short` immediately before editing.
   - Re-run exact candidate scans for `^prj` and `^ref`.
   - Save the candidate file/line list for post-edit comparison.

2. Rewrite only exact main lifecycle task lines if verification finds any remaining untagged target.
   - For each checkbox task line containing exact `#task` and exact whitespace-delimited `^prj`, insert `#prj` directly
     after the first `#task` token if it is not already there.
   - For each checkbox task line containing exact `#task` and exact whitespace-delimited `^ref`, insert `#ref` directly
     after the first `#task` token if it is not already there.
   - Preserve all other content and spacing on the line, including `#hide`, `[created::...]`, `[completion::...]`,
     `[cancelled::...]`, and trailing block IDs.
   - Include `_templates/new_project.md` if it still has the exact `^prj` template line, because it seeds future project
     notes.

3. Explicitly skip non-target shapes.
   - Do not touch `^prj-sibling-state`, `^ref-notes`, or any block ID where `^prj`/`^ref` is only a prefix.
   - Do not touch generated `_generated/` files, historical SDD files, topic marker prose, or annotation follow-up
     tasks.
   - Do not create or remove notes.

4. Verify the migration.
   - Confirm there are zero exact `^prj` lifecycle task lines missing `#task #prj`.
   - Confirm there are zero exact `^ref` lifecycle task lines missing `#task #ref`.
   - Confirm the migrated `#task #prj` and `#task #ref` counts match the preflight candidate counts.
   - Confirm known non-target IDs and historical tags remain unchanged.

5. Commit handling.
   - Because `~/bob/AGENTS.md` requires a commit after vault file changes, use the `/sase_git_commit` workflow after the
     vault migration.
   - The user selected the isolated commit option: commit only `bob_projects.md` and `bob_projects_clean_bad_links.md`,
     whose current diffs contain only this task's tag insertions.
   - Leave the other 40 vault tag insertions uncommitted in the working tree because their files also contain unrelated
     pre-existing user/sync edits that should not be mixed into this task's commit.

## Validation

Run focused repository checks first:

```bash
cargo fmt --check
cargo test projects
cargo test highlights_ref
cargo test --test cli projects
cargo test --test cli highlights_ref
```

If focused tests expose shared fallout, run the broader suite:

```bash
cargo test
```

For the vault:

```bash
rg -n -P '^\s*[-*+]\s+\[[^\]]\]\s+.*#task\s+(?!#prj\b).*?(?<!\S)\^prj(?!\S)' ~/bob --glob '*.md'
rg -n -P '^\s*[-*+]\s+\[[^\]]\]\s+.*#task\s+(?!#ref\b).*?(?<!\S)\^ref(?!\S)' ~/bob --glob '*.md'
rg -n -P '^\s*[-*+]\s+\[[^\]]\]\s+#task\s+#prj\b.*(?<!\S)\^prj(?!\S)' ~/bob --glob '*.md'
rg -n -P '^\s*[-*+]\s+\[[^\]]\]\s+#task\s+#ref\b.*(?<!\S)\^ref(?!\S)' ~/bob --glob '*.md'
```

Then sanity-check command behavior against the real vault without writing:

```bash
bob projects list -b ~/bob
bob highlights scan --dry-run -b ~/bob
```

## Risks and Mitigations

- Dirty vault files: many target files already have user or sync changes. Mitigation: line-level edits only, pre/post
  candidate lists, and hunk-only staging through the SASE commit workflow.
- Version skew: an old installed `bob` binary may still generate `#task [[...]] #hide ^ref` until reinstalled.
  Mitigation: update repo behavior and reinstall after tests if this checkout is the source for the local binary.
- Over-broad migration: naive replacements could corrupt related block IDs or historical `#ref` prose. Mitigation: exact
  checkbox-task, exact `#task`, and exact whitespace-delimited `^prj`/`^ref` matching.
- Parser strictness: requiring `#prj` or `#ref` immediately would make partially migrated notes fail. Mitigation: keep
  command recognition anchored on `^prj`/`^ref` and treat the new tags as additive.

## Acceptance Criteria

- New project task examples and warnings use `#task #prj ... ^prj`.
- New `bob highlights` reference notes use `#task #ref [[...pdf]] #hide ^ref`.
- Existing project/reference lifecycle task lines in `~/bob` have `#prj` or `#ref` inserted immediately after `#task`.
- Ordinary tasks, annotation-derived tasks, historical records, and similarly named block IDs are untouched.
- Focused tests pass, and vault verification shows no untagged exact `^prj`/`^ref` lifecycle task lines remain.
