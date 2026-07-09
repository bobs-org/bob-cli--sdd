---
create_time: 2026-06-28 10:58:30
status: done
prompt: sdd/prompts/202606/depends_on_navigation_label.md
---
# Plan: Rename dependency navigation bullets to `DEPENDS ON`

## Goal

Start writing the managed human-navigation child bullet for task dependencies as:

```markdown
- **DEPENDS ON:** [[#^<block_id>]]
```

instead of:

```markdown
- **DEPENDENCIES:** [[#^<block_id>]]
```

This change is only about the visible navigation child bullet created by `bob-navigation-hotkeys`. The canonical
Obsidian Tasks metadata must remain `[dependsOn:: ...]`; renaming that inline field would break Tasks compatibility and
is out of scope.

## Repository scope

The implementation lives in the `bob-plugins` linked repo, under `plugins/bob-navigation-hotkeys/`, plus the repo
`README.md` and plugin `manifest.json` for the visible behavior/version update.

No `bob-cli` Rust changes and no `chezmoi` config migration are needed. The existing bullet-property config should
continue to define the Tasks-compatible `dependsOn` property with `local_task_id` values.

## Current findings

- `bob-navigation-hotkeys` currently hard-codes `**DEPENDENCIES:**` in the managed child-bullet regex, code comments,
  and `formatDependencyNavigationBullet`.
- All dependency writes already flow through a small set of helpers:
  - `formatDependencyNavigationBullet`
  - `parseDependencyNavigationBullet`
  - `planDependencyNavigationBulletInsertion`
  - `planDependencyNavigationBulletRemoval`
  - `setLocalTaskDependency`
  - `commitMarkedDependencies`
- The live vault Markdown scan found no current `**DEPENDENCIES:**` or `**DEPENDS ON:**` managed bullets, so a bulk note
  rewrite does not appear necessary. The code should still be backward-compatible because old bullets may exist in
  unsynced notes, backups, or notes created between scans.

## Product behavior

### New writes

Every new dependency navigation bullet created by the picker uses the new label:

```markdown
- [ ] #task Current task [dependsOn:: target-id]
  - **DEPENDS ON:** [[#^target-id]]
```

This applies to:

- single dependency linking via `<Enter>`;
- idempotent repair of an already-linked dependency;
- block-ID creation followed by linking;
- multi-select batch add/remove from the `<Tab>` flow.

### Backward compatibility

The plugin must continue to recognize legacy managed bullets:

```markdown
- **DEPENDENCIES:** [[#^target-id]]
```

as equivalent to the new managed shape for parsing, deduplication, grouping, and removal.

Important cases:

- If a legacy bullet already links to the target block, adding/repairing the same dependency must not insert a duplicate
  `**DEPENDS ON:**` bullet.
- If a user removes a dependency whose visible child bullet still says `**DEPENDENCIES:**`, the removal should delete
  that old bullet.
- If the picker touches a dependency child block that contains legacy managed bullets, it should opportunistically
  normalize the managed labels in that current child block to `**DEPENDS ON:**`. This avoids mixed labels after the task
  has been edited while avoiding a vault-wide rewrite.
- Unrelated child bullets, manually written notes, and non-matching wiki links must remain untouched.

### No bulk vault migration by default

Because the read-only scan found no old visible bullets in the vault, implementation should not perform a broad Markdown
rewrite. After code changes, run the scan again and report any old labels if they appear. If old labels are found
outside the plugin-touched flow, do not bulk-edit notes without explicit user approval.

## Technical design

### 1. Centralize the label strings

Add small constants near the existing dependency-navigation regex:

- `DEPENDENCY_NAVIGATION_LABEL = "DEPENDS ON"`
- `LEGACY_DEPENDENCY_NAVIGATION_LABELS = new Set(["DEPENDENCIES"])`

Use the new constant in formatting and tests so the literal does not drift.

### 2. Parse both labels, write one label

Update the managed-bullet regex to match both exact labels:

- `DEPENDS ON`
- `DEPENDENCIES`

Capture enough information to safely rewrite a legacy line in place:

- the list prefix, including indentation and marker;
- the label;
- the linked block ID.

Keep `parseDependencyNavigationBullet(line)` returning only the block ID for existing callers, and add a details helper
such as `parseDependencyNavigationBulletDetails(line)` for code that needs to know whether the line is legacy.

`formatDependencyNavigationBullet(blockId, indent)` should always emit:

```markdown
<indent>- **DEPENDS ON:** [[#^<block_id>]]
```

### 3. Make insertion an upsert/normalization operation

Extend the dependency navigation insertion planning so it treats old and new labels as the same managed bullet family.

The planner should return one of these outcomes:

- no-op: a `**DEPENDS ON:**` bullet for the block already exists under the current parent;
- replace/update: a legacy `**DEPENDENCIES:**` bullet for the block exists and should be rewritten in place with the new
  label;
- insert: no managed bullet for the block exists, so insert a new `**DEPENDS ON:**` bullet after the last managed
  dependency bullet in the current child block;
- guard failure: parent is out of range, not a bullet, or block ID is empty.

Call sites in `setLocalTaskDependency` and `commitMarkedDependencies` should handle both insert and replace plans. The
single-link notice can distinguish `added navigation link`, `updated navigation link label`, and
`navigation link already present`; the batch notice should count label updates alongside additions/removals if
practical.

### 4. Normalize legacy labels in the current dependency child block

Add a narrowly scoped helper, for example:

```text
planDependencyNavigationLabelNormalizations(content, parentLine)
```

It scans only the current bullet's child block and returns line replacements for managed dependency bullets whose label
is legacy. Apply it after removals and insertions are complete, re-reading editor content first so line numbers are
fresh.

This gives useful migration behavior when the picker edits a task, without sweeping unrelated vault files.

### 5. Keep removals label-agnostic

`planDependencyNavigationBulletRemoval(content, parentLine, blockId)` should match both new and legacy labels via the
shared parser. Removing a dependency should delete exactly the managed child bullet for that block ID, regardless of
which label it currently uses.

### 6. Preserve grouping and indentation behavior

The existing grouping rule should stay intact: dependency navigation bullets remain grouped directly under the current
parent bullet, before unrelated child notes. Both legacy and new labels count as managed dependency bullets when
choosing the insertion point.

When rewriting a legacy line, preserve the existing indentation and list marker where possible. New insertions can keep
using the existing formatter's `-` marker.

### 7. Metadata and docs

- Update code comments and any user-facing docs from `DEPENDENCIES` to `DEPENDS ON`.
- Update the `bob-navigation-hotkeys` README row to mention visible `**DEPENDS ON:**` dependency links.
- Bump `plugins/bob-navigation-hotkeys/manifest.json` from `1.5.0` to `1.6.0`, because this changes visible note output
  and compatibility behavior.

## Edge cases

- Existing `[dependsOn:: ...]` values are preserved exactly except for the normal add/remove reconciliation already
  implemented by the dependency picker.
- A legacy `**DEPENDENCIES:**` bullet for the same block is normalized, not duplicated.
- A legacy `**DEPENDENCIES:**` bullet for a removed block is deleted.
- Legacy bullets under a different parent task do not affect insertion/removal for the current task.
- Legacy labels under the current parent but for unrelated dependencies are normalized only when the picker is already
  editing that current dependency child block.
- Child bullets that merely contain the words "DEPENDENCIES" or "DEPENDS ON" but do not match the exact managed
  `[[#^block-id]]` shape are ignored.
- Dependency value/block-ID mismatches still behave as before: `[dependsOn:: <id-field>]` remains canonical for Tasks,
  while the visible link targets the actual block ID.

## Validation

Run from the `bob-plugins` checkout:

1. `node --check plugins/bob-navigation-hotkeys/main.js`
2. Focused Node helper assertions:
   - `formatDependencyNavigationBullet("abc", "  ")` emits `  - **DEPENDS ON:** [[#^abc]]`.
   - `parseDependencyNavigationBullet` recognizes both old and new labels.
   - the details parser reports legacy vs current labels.
   - insertion planning no-ops for an existing `DEPENDS ON` bullet.
   - insertion planning rewrites an existing `DEPENDENCIES` bullet for the same block instead of duplicating it.
   - insertion grouping treats old and new managed bullets as the same family.
   - removal planning deletes both old and new labels, scoped to the current child block.
   - normalization planning rewrites only managed legacy labels under the current parent.
3. In-memory editor checks around `setLocalTaskDependency` and `commitMarkedDependencies`:
   - add a new dependency writes `DEPENDS ON`;
   - already-linked dependency with legacy nav bullet updates the label;
   - batch add/remove deletes legacy labels for removals and writes new labels for additions;
   - unrelated child bullets and foreign parent blocks are preserved.
4. `npm run validate`
5. `git diff --check`
6. Read-only vault scan for old/new labels:
   - `rg -n "\\*\\*(DEPENDENCIES|DEPENDS ON):\\*\\*" ~/bob --glob '*.md'`
7. Deploy only after a scoped dry run:
   - `bob plugins sync --dry-run --repo <bob-plugins checkout> --plugin bob-navigation-hotkeys`
   - if the dry run shows only the expected plugin files, run the real scoped sync.

After sync, reload the Bob Navigation Hotkeys plugin in Obsidian.
