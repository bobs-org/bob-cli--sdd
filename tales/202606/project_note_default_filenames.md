---
create_time: 2026-06-12 17:18:40
status: wip
prompt: sdd/prompts/202606/project_note_default_filenames.md
---
# Plan: Default Filenames for New Project Notes

## Goal

When Bob's Obsidian project-note commands create a project note without an explicit task block-ID-derived name, give the
new root-level project note a deterministic default filename:

- Source note `~/bob/foo_bar.md` -> first available `~/bob/foo_bar_<X>.md`.
- `<X>` uses the lowercase alphanumeric alphabet `0123456789abcdefghijklmnopqrstuvwxyz`.
- Check all one-character suffixes first, in alphabet order: `0` through `z`.
- Then check all two-character suffixes in the same alphabet order: `00`, `01`, ..., `zz`.
- Continue with three-character suffixes, then longer suffixes as needed.

This should cover both:

- `<Ctrl+Alt+Shift+N>` / `create-project-note-from-task`, but only when the promoted task has no block ID.
- `<Ctrl+Shift+N>` / `create-project-note`, which creates a project note from scratch.

Tasks that already have a block ID should keep the existing block-ID-derived filename behavior.

## Context Reviewed

- Project short memory: `memory/short/sase.md`.
- Required Obsidian memory through:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault/task/project-note workflow context before changing project note keymap defaults"`.
- Plan workflow from `/home/bryan/.codex/skills/sase_plan/SKILL.md`.
- Prior SDD tales:
  - `sdd/tales/202606/obsidian_project_from_task_keymap.md`
  - `sdd/tales/202606/obsidian_project_from_task_block_id.md`
  - `sdd/tales/202606/obsidian_cmd_n_new_note_template.md`
  - `sdd/tales/202606/new_note_current_parent_fallback.md`
- Live vault instructions: `/home/bryan/bob/AGENTS.md`.
- Live vault status via `git -C /home/bryan/bob status --short`.
- Current implementation:
  - `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
  - `/home/bryan/bob/.obsidian/hotkeys.json`
  - `/home/bryan/bob/_templates/new_project.md`

No `bob-cli` subcommands or options are being added, so `memory/long/cli_rules.md` is not required.

## Current Findings

- Both target keymaps are already registered:
  - `bob-navigation-hotkeys:create-project-note` is bound to `<Ctrl+Shift+N>`.
  - `bob-navigation-hotkeys:create-project-note-from-task` is bound to `<Ctrl+Alt+Shift+N>`.
- Both commands flow through the shared helper `createProjectNoteFile(creatingFile, basename)`.
- `createProjectNote()` currently calls `createProjectNoteFile(creatingFile)` with no basename.
- `createProjectNoteFromTask()` derives and passes a basename only when the source task has a block ID; no-block-ID
  tasks currently pass `undefined`, which lets Templater create an untitled note.
- Existing block-ID behavior should remain unchanged:
  - `^foo-bar-baz` in `fake_project.md` creates `fake_project_foo_bar_baz.md`.
  - Block links to the old task block ID are rewritten before the source task is removed.
- `hotkeys.json` already has the right key bindings, so this task should not need a hotkey change.
- `_templates/new_project.md` already contains the placeholder that the project-from-task flow seeds. It is dirty before
  this task and should not be touched.
- The live vault is dirty before this task, including `.obsidian/plugins/bob-navigation-hotkeys/main.js`. The existing
  dirty plugin diff appears unrelated to project-note creation, so implementation must work with that state and avoid
  reverting it.

## Design

Keep the change inside `bob-navigation-hotkeys/main.js`.

Add a small, testable default-name path:

1. Add a constant for the suffix alphabet:
   `PROJECT_DEFAULT_BASENAME_SUFFIX_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"`.
2. Add pure helpers near the existing project-note helpers:
   - `getProjectBasenameSuffixForIndex(index, length)` or an equivalent generator helper for suffix enumeration.
   - `getNextDefaultProjectBasename(sourceBasename, existingBasenames)` returning the first `<sourceBasename>_<X>` not
     present in the supplied root-basename set.
3. Add a plugin method that builds the current root Markdown basename set from the vault:
   - Prefer `app.vault.getMarkdownFiles()`.
   - Include only root-level Markdown files, because the requested target shape is `~/bob/<name>.md`.
   - Use each file's `basename`, falling back to `getVaultPathBasenameWithoutExtension(file.path)`.
4. Add a plugin method such as `getDefaultProjectNoteBasename(creatingFile)`:
   - Source basename is `creatingFile.basename` or the basename-without-extension of `creatingFile.path`.
   - Return `getNextDefaultProjectBasename(sourceBasename, rootBasenames)`.
   - If no usable source basename can be derived, return `null` and show a specific notice from the command path.
5. Update `createProjectNoteFile(creatingFile, basename)`:
   - If `basename` is supplied, keep using it exactly as today. This preserves block-ID-derived filenames.
   - If `basename` is missing, derive the default basename from `creatingFile`.
   - Pass the resolved basename to Templater's `create_new_note_from_template(...)`.

This centralizes the behavior in the one project-note creation helper shared by both keymaps. It also keeps the existing
current-tab and rename-mode Templater behavior, but starts rename mode with the generated default name rather than
`Untitled`.

## Sequence Details

The helper should enumerate suffixes in this order:

```text
0
1
...
9
a
...
z
00
01
...
0z
10
...
zz
000
...
```

Implementation should avoid an accidental infinite loop. Because the root-basename set is finite, the helper can check
at most `existingBasenames.size + 1` generated candidates; by pigeonhole principle, at least one of those candidates
cannot already be in that finite set.

## Scope

Expected implementation file:

- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`

Expected files not to edit:

- `/home/bryan/bob/.obsidian/hotkeys.json`
- `/home/bryan/bob/_templates/new_project.md`
- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/manifest.json`
- Any `bob-cli` Rust source
- Any memory files

## Implementation Steps

1. Re-check `git -C /home/bryan/bob status --short` immediately before editing.
2. Patch `bob-navigation-hotkeys/main.js` only:
   - Add the suffix alphabet constant.
   - Add/export pure default-basename helper(s).
   - Add plugin methods for root basename collection and default project basename derivation.
   - Resolve a default basename inside `createProjectNoteFile()` when its `basename` parameter is empty.
3. Inspect the resulting diff and confirm the pre-existing unrelated plugin changes are preserved.
4. Do not touch the hotkey file unless inspection after implementation unexpectedly shows the key bindings are missing.

## Validation

Static checks:

```bash
node --check /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js
git -C /home/bryan/bob diff --check -- .obsidian/plugins/bob-navigation-hotkeys/main.js
```

Focused Node helper checks:

- No existing `foo_bar_*` root files -> `foo_bar_0`.
- Existing `foo_bar_0` -> `foo_bar_1`.
- Existing `foo_bar_0` through `foo_bar_z` -> `foo_bar_00`.
- Existing `foo_bar_00` after that -> `foo_bar_01`.
- Existing suffixes with unrelated prefixes are ignored.
- Source basenames are preserved verbatim before the added suffix.

Command-flow smoke checks with mocks if practical:

- `<Ctrl+Shift+N>` path calls Templater with the generated basename.
- `<Ctrl+Alt+Shift+N>` no-block-ID task path calls Templater with the generated basename.
- `<Ctrl+Alt+Shift+N>` block-ID task path still calls Templater with the existing block-ID-derived basename.

Manual acceptance after reloading Obsidian:

- In `foo_bar.md`, press `<Ctrl+Shift+N>`: the title rename field starts from `foo_bar_0` or the next available suffix.
- In `foo_bar.md`, place the cursor on an open `#task` without a block ID and press `<Ctrl+Alt+Shift+N>`: the project is
  created as `foo_bar_<X>.md`, the `^prj` task is seeded, and the source task is removed as before.
- A task with a block ID still creates the block-ID-derived filename and rewrites block links as before.

## Risks / Notes

- The live vault is under Obsidian Sync and already dirty. Implementation must preserve unrelated working-tree changes
  in the plugin and avoid staging or committing unrelated files.
- The default basename is computed against root-level Markdown files to match the requested `~/bob/<name>.md` target.
  This intentionally does not skip a suffix solely because a same-basename note exists in a subfolder.
- Templater still owns actual file creation and may keep its normal rename-mode behavior. Passing a basename should give
  the user the requested default filename while still letting them rename immediately.
- If Obsidian's runtime lacks `vault.getMarkdownFiles()`, implementation should fall back to a direct root-path
  existence check or abort with a clear notice rather than creating `Untitled`.

## Finish Criteria

- This plan is submitted with:

  ```bash
  sase plan sase_plan_project_note_default_filenames.md
  ```

- No live vault implementation file is edited before plan submission.
- After implementation, any vault changes are committed with `/sase_git_commit` as required by
  `/home/bryan/bob/AGENTS.md`.
