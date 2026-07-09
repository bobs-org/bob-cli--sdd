---
create_time: 2026-06-06 10:59:00
status: wip
prompt: sdd/prompts/202606/obsidian_task_checkbox_toggle.md
---
# Plan: Obsidian Ctrl+] Checkbox Marker Toggle

## Context

Bryan's Obsidian vault is `~/bob`. The existing local plugin `~/bob/.obsidian/plugins/task-status-cycler/main.js`
already owns custom task line behavior:

- Obsidian commands for task status cycling and open/done toggling.
- Vim normal-mode mappings through `window.CodeMirrorAdapter.Vim.mapCommand`.
- Helpers for parsing task list lines and preserving task metadata.

The vault's `hotkeys.json` currently maps:

- `Alt+]` and `Alt+[` to task status cycling.
- `Mod+]` to Obsidian forward navigation through `app:go-forward`.

On this Linux-style setup, `Mod+]` can conflict with the requested `Ctrl+]` binding, so the implementation needs to
address that hotkey collision rather than merely adding another command.

## Goal

Add a `<Ctrl+]>` keymap that toggles the active list item between a Markdown task checkbox marker and a plain list
bullet:

```md
- [ ] Foo bar baz
```

becomes:

```md
- Foo bar baz
```

Pressing `<Ctrl+]>` again on that same plain bullet restores:

```md
- [ ] Foo bar baz
```

## Implementation

1. Extend `task-status-cycler/main.js` rather than creating a new plugin.
   - This keeps all task/list editing behavior in the existing local plugin.
   - The new command will be available through Obsidian's command registry and through CodeMirror Vim normal mode.

2. Add pure line-rewrite helpers.
   - Detect task list items with indentation, optional blockquote prefixes, unordered markers, and ordered markers.
   - For task list items, remove the `[status]` marker and the following separator whitespace, preserving the list
     marker and body text.
   - For plain list items, insert `[ ] ` immediately after the list marker.
   - Return `null` for non-list lines so the command is disabled there.
   - Treat any single-character task status (`[ ]`, `[x]`, `[/]`, `[B]`, `[-]`, etc.) as a present checkbox marker;
     re-adding always uses `[ ]`.

3. Add an Obsidian editor command.
   - Command id: `toggle-task-checkbox-marker`.
   - Command name: `Toggle task checkbox marker`.
   - Use `editorCheckCallback` so Obsidian only enables it when the active line is a supported task or list item.
   - Replace only the active line.
   - Preserve the cursor near the same semantic text by shifting the column when `[ ] ` is inserted or removed and
     clamping to the rewritten line.

4. Add a Vim normal-mode mapping.
   - Define a CodeMirror Vim action such as `taskStatusCyclerToggleCheckboxMarker`.
   - Map `<C-]>` in normal mode next to the existing `<C-CR>`, `<BS>`, `o`, `<C-d>`, and `<C-u>` mappings.
   - Reuse the same editor command implementation path so Vim and non-Vim behavior stay consistent.

5. Add the vault hotkey.
   - Add `task-status-cycler:toggle-task-checkbox-marker` with `{ "modifiers": ["Ctrl"], "key": "]" }` in
     `~/bob/.obsidian/hotkeys.json`.
   - Remove only the conflicting `Mod+]` binding from `app:go-forward`, leaving its existing `Mod+Alt+ArrowRight`
     binding intact.
   - Leave unrelated hotkeys unchanged.

## Validation

1. Run syntax/config checks:
   - `node -c /home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`
   - `jq '.' /home/bryan/bob/.obsidian/hotkeys.json`
   - `jq '.' /home/bryan/bob/.obsidian/plugins/task-status-cycler/manifest.json`
   - `git -C /home/bryan/bob diff --check -- .obsidian/plugins/task-status-cycler/main.js .obsidian/hotkeys.json`

2. Run a small Node helper test with a mocked `obsidian` module to verify the pure rewrite behavior:
   - `  - [ ] Foo bar baz` -> `  - Foo bar baz`
   - `  - Foo bar baz` -> `  - [ ] Foo bar baz`
   - `> - [x] Done` -> `> - Done`
   - Non-list text returns no rewrite.

3. Review the final vault diff to confirm only the intended plugin and hotkey files changed.

## Manual Smoke Test

After reloading Obsidian or disabling/re-enabling `task-status-cycler`:

1. Place the cursor on `  - [ ] Foo bar baz`.
2. Press `<Ctrl+]>`; confirm the line becomes `  - Foo bar baz`.
3. Press `<Ctrl+]>` again; confirm the line becomes `  - [ ] Foo bar baz`.
4. Repeat in Vim normal mode to confirm the CodeMirror Vim mapping also works.
