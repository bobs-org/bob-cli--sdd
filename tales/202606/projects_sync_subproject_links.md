---
create_time: 2026-06-12 14:01:11
status: done
prompt: sdd/prompts/202606/projects_sync_subproject_links.md
---
# Plan: `bob projects sync` — maintain sub-project link bullets under the `^prj` task

## Problem

Since the projects_sync_subprojects_1 change, `bob projects sync` knows which projects are parents: it computes the set
of open sub-projects (children whose `parent` wikilink resolves to this note and whose own `^prj` task is open) and uses
it for the `[p::2]` surface/hide decision. But that knowledge is invisible in the note itself — a parent project's
`^prj` task gives no hint of which sub-projects its work lives in. The user wants the parent's `^prj` task to carry one
sub-bullet per discovered sub-project, each a wikilink to the child note, e.g.:

```markdown
- [ ] #task Design and configure “projects” in Obsidian! [p::2] ^prj
  - [[bob_projects_clean_bad_links]]
  - [[sase_blog]]
```

## New behavior

`sync` reconciles a set of **sub-project link bullets** nested directly under the open `^prj` task line so that, after a
run, there is exactly one link bullet per open sub-project.

### Which children get a bullet: the same set that drives `[p::2]`

A child earns a bullet iff it counts as an **open sub-project** under the existing rule: its `parent` wikilink resolves
to this note's file stem (case-insensitively) and its own `^prj` task is `Open`. Reusing the exact children set already
built between the two sync passes keeps one rule and one source of truth, and preserves single-run convergence: the run
that checks a child's `^prj` (flipping its status to done) sees that child as not-open and removes its bullet from the
parent in the same run — mirroring how `[p::2]` removal already converges, so the existing idempotency-style tests
extend naturally.

Rejected alternative — listing children by non-terminal frontmatter status regardless of `^prj` state: a child with a
missing/malformed `^prj` already surfaces errors and pushes the parent onto the dash; keeping its bullet would require a
second "effective status" children computation and would break single-run convergence when a child closes.

### Bullet format and placement

- Each generated bullet is a **plain list item**, not a checkbox and with no `#task` tag:
  `- [[<child file stem, original case>]]`. Plain bullets are invisible to everything that matters: the Tasks-plugin
  query in `dash.md` only renders task lines (and its `[p::N]` filter reads `task.originalMarkdown` of the task line
  itself), and the scanner's own counters (`open_task_count`, `open_unprioritized_count`) only count `#task` checkbox
  lines — so link bullets never feed back into the sync logic.
- The link target is the child's file stem with its original casing, no directory path and no alias — the same shape the
  `parent` convention uses (`[[bob]]`, not `[[gtd/bob]]`).
- Bullets are nested one level under the `^prj` line: indentation is the `^prj` line's own leading whitespace plus one
  **tab** (the vault and Obsidian-default convention for sub-bullets under tasks; space-indented bullets in the vault
  are confined to imported/generated areas). If the `^prj` task already has sub-bullets, new bullets reuse the
  indentation of the existing sub-bullet lines instead, so a hand-built block stays uniform.
- New bullets are inserted immediately after the last existing recognized link bullet, or immediately after the `^prj`
  line when there are none. Multiple new bullets in one run are added in case-insensitive alphabetical order by stem.
  Existing still-valid bullets are left exactly where they are — no reordering, minimal churn.

### Reconciliation rules

Define the **`^prj` sub-block** as the run of consecutive non-blank lines immediately following the `^prj` line whose
leading whitespace strictly extends the `^prj` line's leading whitespace (tab- and space-safe prefix comparison; the
common real layout — `^prj`, blank line, `## Tasks` — yields an empty sub-block). Within the sub-block:

- A **pure link bullet** is a list item whose entire content after the bullet marker is a single wikilink (alias and
  path-qualified forms allowed); its target resolves through the existing `wikilink_target()` normalization.
- **Add:** a child with no wikilink to it anywhere in the sub-block gets a new bullet. The duplicate check scans every
  wikilink in every sub-block line — so a hand-written `- [[child]] kickoff notes here` bullet suppresses the add rather
  than producing a duplicate.
- **Remove:** a pure link bullet whose target is not in the current open-children set is deleted (the whole line). This
  covers checked/canceled children, children archived into `done/`, and renamed children. It also means sync owns the
  "bare wikilink bullet under `^prj`" namespace: a manually added pure link bullet pointing at a non-project note will
  be removed. Bullets with any extra text are never touched, so prose-style sub-bullets are the escape hatch.
- Edits are gated exactly like the other `^prj` line edits: only for projects whose effective status is non-terminal and
  whose `^prj` state is `Open`. Terminal projects keep the "never get `^prj` line edits" guarantee, and
  `Missing/Malformed/Multiple` `^prj` states are untouched.

### Output

Reuse the existing `SyncEvent::PrjEdit` shape so the report and summary stay uniform:

```text
  ok bob_projects  added [[sase_blog]] to ^prj  open sub-project
  ok bob_projects  removed [[old_child]] from ^prj  no longer an open sub-project
```

Dry-run renders the existing `would add`/`would remove` verbs. These edits count toward the existing `^prj edited`
summary bucket; no new summary column.

## Implementation

All changes live in `src/native/projects.rs` plus docs and tests.

### 1. Parse the `^prj` sub-block

- `Project` gains the original-case file stem (`link_name` stays the lowercased matching key; derive one from the other
  in `project_link_name()`/a sibling helper).
- `parse_project()` records, for the (single) `^prj` candidate, its sub-block: for each sub-block line, whether it is a
  pure link bullet (and its normalized target), every wikilink target it contains, and its indentation. Store a small
  `PrjSubBullet` list on `Project` (or `PrjTask`) — enough for planning (linked-target set, pure-link targets) and for
  choosing insertion indentation. Multiple-`^prj` files never plan, so associating the block with the first candidate is
  safe.

### 2. Children map instead of children set

Replace `open_subproject_parent_link_names() -> HashSet<String>` with a map from parent link name to the deduplicated,
case-insensitively sorted list of child stems (original case, for writing links). `has_open_subprojects` becomes "the
map has an entry"; the `[p::2]` logic is otherwise unchanged. Two children in different directories sharing a stem
collapse to one bullet — the same stem-level ambiguity the parent-matching rule already accepts.

### 3. Planning

`plan_project_sync()` takes the project's open-children slice (empty slice = no open sub-projects). Inside the existing
open-`^prj`/non-terminal block, after the priority logic:

- `ProjectChange::AddSubprojectLink { stem }` for each child stem (sorted) absent from the sub-block's linked-target
  set;
- `ProjectChange::RemoveSubprojectLink { target }` for each pure link bullet whose target is outside the children set.

Both variants render through `ProjectChange::event()` as `PrjEdit` events with field `[[<name>]]` and the reasons shown
above.

### 4. Applying edits

- `remove_subproject_link_edit`: delete the matching pure-link-bullet line's full span (start through `next_start`),
  CRLF-safe.
- Adding: build **one combined `TextEdit`** for all of a file's added bullets (single insertion point — after the last
  existing recognized link bullet, else directly after the `^prj` line), inserting `<indent>- [[stem]]` lines with the
  file's line ending; one event is still emitted per child. A single edit sidesteps the existing
  apply-in-descending-start order being undefined for equal-offset inserts, and handles the `^prj`-as-last-line-
  without-trailing-newline case in one place (existing `line_ending()` helper).
- Insertions land strictly after the `^prj` line while the priority edits land within it, so edit spans never overlap.

### 5. Docs and help text

- `docs/projects.md`: new Sync Rules bullets for add/remove of sub-project link bullets (including the pure-link- bullet
  ownership caveat and the "extra text is never touched" escape hatch); extend the example output.
- `sync` subcommand `long_about`: one sentence noting sync also maintains sub-project link bullets under `^prj`.

### 6. Tests

Unit tests (`projects.rs`):

- Sub-block parsing: pure link bullets (bare/alias/path-qualified), bullets with extra text, indentation capture, empty
  block when a blank line follows `^prj`, sub-block bullets do not affect task counts.
- Planning: adds missing children sorted; dedups against any wikilink in the block (including extra-text bullets);
  removes stale pure link bullets only; no link changes when `^prj` is missing/checked or the project is terminal;
  case-insensitive matching.
- Edit application: insert directly after `^prj` (tab indent, no existing block); insert after existing link bullets
  reusing their indentation; remove a middle bullet; CRLF preservation; `^prj` as final line without trailing newline.

Integration tests (`tests/cli.rs`, same inline-fixture style as
`projects_sync_hides_parent_projects_with_open_ subprojects`, tests/cli.rs:1879):

- Parent with two open children: both bullets added in sorted order under `^prj`, second run is a no-op.
- Child `^prj` checked: one run flips the child to done, removes the child's bullet, and removes the parent's `[p::2]`
  (when it was the only child); second run is a no-op.
- Stale pure link bullet (child archived/closed) is removed while a prose sub-bullet with extra text survives.
- Dry-run prints the add/remove lines without writing.

## Out of scope

- `bob projects list` output is unchanged.
- No status decoration of child links (no checkboxes, no done-children rendering) and no alias text in generated links.
- Links elsewhere in the note (e.g. hand-maintained "child posts" lists in the body) are untouched.
- No new CLI flags or subcommands.
- No validation of `parent` values (cycles, dangling links) — unchanged from the previous tale.
