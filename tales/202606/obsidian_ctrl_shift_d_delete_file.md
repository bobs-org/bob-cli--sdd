---
create_time: 2026-06-11 07:05:59
status: done
prompt: sdd/prompts/202606/obsidian_ctrl_shift_d_delete_file.md
---
# Obsidian Ctrl+Shift+D Delete Current File Keymap Plan

## Goal

Add a `Ctrl+Shift+D` hotkey to the Bob Obsidian vault that deletes the currently active file and shows a toast (Obsidian
`Notice`) confirming the deletion.

Expected behavior:

- With any file open and focused, pressing `Ctrl+Shift+D` deletes that file immediately (no confirmation dialog) and
  shows a toast such as `Deleted "path/to/note.md"`.
- The file is moved to trash according to the vault's existing "Deleted files" preference (currently the Obsidian
  default: system trash), so an accidental press is recoverable.
- If no file is active (e.g., an empty tab or a non-file view), show a toast like `No active file` and do nothing.
- If deletion fails for any reason, show a toast reporting the failure instead of failing silently.

## Context Reviewed

- Read project short memory from `memory/short/sase.md`. The Tier 2 `memory/long/cli_rules.md` trigger does not apply:
  no `bob-cli` CLI subcommands or options are added by this task.
- Read `/home/bryan/bob/AGENTS.md`: the vault is actively synced; inspect `git status` before editing, touch only task
  files, and commit any `~/bob` changes with the SASE commit workflow before finishing. The vault working tree is
  currently clean.
- Inspected the live navigation plugin `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`. It is the
  established home for whole-file commands (`open-parent-note`, `open-alternate-file`, `copy-active-file-path`, ...)
  registered via `this.addCommand(...)`, and it already uses `new Notice(...)` toasts and
  `this.app.workspace.getActiveFile()` extensively.
- Inspected `/home/bryan/bob/.obsidian/hotkeys.json`: custom plugin hotkeys are registered here (e.g.,
  `bob-navigation-hotkeys:open-child-note` on `Ctrl+=`). No existing binding uses `Ctrl+Shift+D`, and Obsidian ships no
  default on that chord.
- Inspected `/home/bryan/bob/.obsidian/app.json`: `promptDelete` is `false` (Bryan already prefers delete without
  confirmation) and `trashOption` is unset, meaning the Obsidian default of moving deleted files to the system trash.
- No `bob-cli` Rust change is involved; this mirrors prior keymap tasks (child-note hotkey, transclusion toggle) that
  were implemented entirely in the vault plugin plus `hotkeys.json`.

## Product Decisions

1. Implement the command in `bob-navigation-hotkeys`.
   - It is the established plugin for active-file-level commands and already has the helpers, `Notice` conventions, and
     command-registration block this feature needs.
   - No new plugin and no `bob-cli` Rust, script, or test changes.

2. Delete via `this.app.fileManager.trashFile(file)`.
   - This is the Obsidian API that respects the user's "Deleted files" setting, so the file lands in the system trash
     under the current vault config and would automatically follow any future change to that preference.
   - Do not permanently delete (`vault.delete`); recoverability matters for a one-chord destructive action.

3. No confirmation dialog, by design.
   - The point of the keymap is fast deletion, and the vault already sets `promptDelete: false` for Obsidian's own
     delete command. Recoverability comes from the trash, not a prompt.

4. Operate on any active file type, not just Markdown.
   - `getActiveFile()` returns the focused file regardless of type (notes, PDFs, images). "Delete the current file"
     should mean exactly that.

5. Toast contents.
   - Success: `Deleted "<vault-relative-path>"` — the path (not just the basename) so it is obvious which file was
     removed, matching the precision of existing notices in this plugin.
   - No active file: `No active file`.
   - Failure: `Could not delete "<vault-relative-path>"`.

6. Bind the hotkey in `.obsidian/hotkeys.json`, not as an `addCommand` default.
   - User-chosen bindings for this plugin live in `hotkeys.json` (`open-parent-note`, `open-child-note`,
     `open-template-note`, ...). Keep the new binding alongside them:
     `"bob-navigation-hotkeys:delete-current-file": [{ "modifiers": ["Ctrl", "Shift"], "key": "D" }]`.
   - Use explicit `Ctrl` (matching the existing entries and the literal request) rather than `Mod`.

7. Leave post-delete navigation alone.
   - After deletion Obsidian empties/closes the tab on its own. Jumping to the alternate file automatically is out of
     scope for the first pass; the plugin's existing `file-open` tracking handles subsequent navigation naturally.

## Implementation Scope

Expected vault files to edit:

- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
- `/home/bryan/bob/.obsidian/hotkeys.json`

No expected edits to:

- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/manifest.json` or `styles.css`
- Any other vault plugin
- Any `bob-cli` Rust, script, README, or test files

Likely JavaScript changes in `main.js`:

- Register the command in `onload()` next to the existing whole-file commands:
  - `this.addCommand({ id: "delete-current-file", name: "Delete current file", callback: () => this.deleteCurrentFile() })`
- Add an async action method on the plugin:
  - `deleteCurrentFile()`:
    - `const file = this.app.workspace.getActiveFile()`; if missing, `new Notice("No active file")` and return.
    - Capture `file.path` before deleting (the object is invalid afterwards).
    - `await this.app.fileManager.trashFile(file)` inside try/catch.
    - On success show the `Deleted "<path>"` notice; on error show the `Could not delete "<path>"` notice.
- Add a small pure helper for the notice text (e.g., `getDeletedFileNoticeText(path)`) exported through the existing
  `module.exports.helpers` block so it can be exercised from Node, mirroring `getCreatedNoteNoticeText`.

`hotkeys.json` change:

- Add the `bob-navigation-hotkeys:delete-current-file` entry with `["Ctrl", "Shift"] + "D"`, formatted consistently with
  the surrounding entries.

## Verification Plan

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js
jq '.' /home/bryan/bob/.obsidian/hotkeys.json
git -C /home/bryan/bob diff --check
```

Focused Node helper assertions (stubbed `obsidian` module, same harness style as prior keymap work):

- `getDeletedFileNoticeText("a/b.md")` returns `Deleted "a/b.md"`.
- The command id `delete-current-file` is registered by `onload()` against a stubbed `addCommand`.

Manual live-vault acceptance:

- Reload Obsidian (`Mod+R`) so the edited plugin and `hotkeys.json` are re-read. Note: edit `hotkeys.json` while
  Obsidian is not mid-edit of its own hotkey settings, since Obsidian rewrites that file from memory when hotkeys change
  in-app.
- Confirm in Settings → Hotkeys that `Ctrl+Shift+D` shows no conflict and is attached to "Bob Navigation Hotkeys: Delete
  current file".
- Create a scratch note, press `Ctrl+Shift+D`, and confirm the note disappears, the `Deleted "..."` toast appears, and
  the file is present in the system trash.
- Press `Ctrl+Shift+D` on an empty tab and confirm the `No active file` toast.
- Confirm existing bindings still work: `Ctrl+-`, `Ctrl+=`, `Ctrl+.`, `Ctrl+\`, `Mod+Y`.

Before finishing:

```bash
git -C /home/bryan/bob status --short
git status --short
```

Commit only the two edited vault files (`main.js`, `hotkeys.json`) with the required SASE commit workflow, leaving any
unrelated vault changes untouched.

## Risks

- This is a one-chord destructive action with no confirmation. Mitigated by using `trashFile` (recoverable from system
  trash) and by the toast making the deletion visible immediately. If accidental presses become a problem, a follow-up
  could add an undo affordance or a confirmation toggle.
- Deleting a scratch note in the live vault during acceptance testing creates and removes a real file in a synced vault;
  the test note will be created fresh and trashed, and `git status` checked afterwards so no stray test artifact is
  committed.
- If Obsidian is running while `hotkeys.json` is edited externally, an in-app hotkey change could clobber the new entry;
  the acceptance steps reload Obsidian right after editing to minimize that window.
- The deleted-file path is captured before the delete call; otherwise the toast could read from an invalidated file
  object.
