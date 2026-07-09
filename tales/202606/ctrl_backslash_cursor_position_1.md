---
create_time: 2026-06-03 04:57:25
status: planned
prompt: sdd/prompts/202606/ctrl_backslash_cursor_position_1.md
---

# Preserve `Ctrl-\` Alternate-Note Cursor Position

## Goal

Make the Obsidian `Ctrl-\` hotkey, currently bound to `bob-navigation-hotkeys:open-alternate-file`, return to the
previously focused Markdown note at the same editor cursor position that note last had during the current Obsidian
session.

Expected behavior:

- Open note A, place the cursor at line/ch X.
- Move to note B, place the cursor at line/ch Y.
- Press `Ctrl-\`.
- Obsidian opens note A and restores cursor line/ch X.
- Press `Ctrl-\` again.
- Obsidian opens note B and restores cursor line/ch Y.

This is an in-memory session behavior. No vault note contents, metadata, or persistent plugin data should change.

## Context Reviewed

- Project short memory (`memory/short/sase.md`): this agent is running in an ephemeral `bob-cli_<N>` workspace; no
  sibling repositories are configured.
- Obsidian long memory was read through the audited command:
  `sase memory read long/obsidian.md --reason "Need Obsidian workflow and keymap context before planning ctrl-backslash note navigation change"`.
- `/home/bryan/bob` is the active Obsidian vault. Its `AGENTS.md` requires checking status before edits, preserving
  unrelated dirty changes, and committing any vault file changes with `/sase_git_commit` before finishing.
- Current vault status has unrelated dirty note files:
  - `obsidian.md`
  - `sase.md`
  - untracked `2026/20260603_day.md`
- The target plugin file is clean: `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`.
- `.obsidian/hotkeys.json` binds `bob-navigation-hotkeys:open-alternate-file` to `Ctrl-\`; no hotkey JSON change is
  expected.
- Current implementation stores only paths:
  - `currentFilePath`
  - `alternateFilePath`
  - `trackOpenedFile(file)` updates those paths on the workspace `file-open` event.
  - `openAlternateFile()` resolves `alternateFilePath` and calls `workspace.getLeaf(false).openFile(file)`.
- Because only file paths are stored, the command cannot restore the old note's editor cursor.
- Depending only on `file-open` to capture the old cursor is risky: by the time `file-open` fires for the new note, the
  previous editor may no longer be available as the active Markdown editor.

## Design

Add lightweight in-memory position tracking to `bob-navigation-hotkeys`.

1. Keep the existing alternate-file path behavior.
   - Preserve `currentFilePath` and `alternateFilePath` semantics so the command continues toggling between the two most
     recently focused Markdown files.
   - Store cursor positions separately in a `Map` keyed by vault-relative file path.

2. Capture cursor positions before navigation and while editing.
   - Add a helper that reads the active `MarkdownView` editor cursor via `view.editor.getCursor()`.
   - Call that helper immediately before plugin-driven navigation that can switch files:
     - `openAlternateFile()`
     - `openResolvedLink(...)`
   - Register a CodeMirror 6 `EditorView.updateListener` to update the active file's last-known cursor when the editor
     selection changes. This covers ordinary cursor motion before the user leaves a note through non-plugin navigation.
   - Fall back gracefully if CodeMirror update data or editor APIs are unavailable.

3. Restore the stored position after `Ctrl-\` opens the alternate note.
   - Before opening the alternate file, capture the current note's latest cursor position.
   - Look up the alternate note's last-known position.
   - Await `openFile(file)`, then set the active Markdown editor cursor to the stored `{ line, ch }`.
   - Defer one retry to the next frame/timer if the editor is not ready immediately after `openFile`.
   - Clamp the stored line and character to the opened file's current bounds so stale positions do not throw if the note
     changed since the position was captured.

4. Do not change unrelated navigation behavior.
   - Parent/template/next/previous link commands may benefit from better position capture before they open another note,
     but they should not force a restore of the destination note unless they are the alternate-file command.
   - Vim mappings for `[[` and `]]` remain unchanged.
   - `.obsidian/hotkeys.json` remains unchanged unless implementation inspection finds direct config drift.

## Expected Implementation Scope

Expected vault file to edit:

- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`

No `bob-cli` Rust code change is expected.

Likely implementation details:

- Import `EditorView` from `@codemirror/view`, matching the existing vault plugin pattern in `bob-ledger-tools`.
- Initialize:
  - `this.filePositions = new Map()`
  - optional timer/rAF handle tracking if a deferred restore needs cleanup on unload.
- Add small helpers for:
  - validating/clamping `{ line, ch }`
  - converting a CodeMirror update selection head to Obsidian-style `{ line, ch }`
  - reading the active Markdown editor cursor
  - saving a position for a path
  - restoring a position in the active editor
  - deferring a restore retry safely
- Keep helper logic compact and local to the plugin; no persistent `data.json` is needed.
- Consider adding `module.exports.helpers` for pure helper verification if it keeps focused Node checks simple.

## Verification Plan

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js
jq '.' /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/manifest.json
jq '.' /home/bryan/bob/.obsidian/hotkeys.json
```

Focused Node checks with stubbed `obsidian` and `@codemirror/view` modules:

- Capturing an active editor cursor stores `{ line, ch }` under the active Markdown file path.
- A CodeMirror selection update converts document offsets to zero-based `{ line, ch }` and stores that position for the
  active Markdown file.
- `trackOpenedFile` continues to set `alternateFilePath` to the previous Markdown file path.
- `openAlternateFile`:
  - refuses cleanly when there is no alternate file;
  - captures the current file's cursor before opening the alternate;
  - calls `openFile` for the alternate file;
  - restores the alternate file's stored cursor after open.
- Restore clamps out-of-range line/ch values rather than throwing.
- Non-Markdown files are ignored as before.

Manual live-vault acceptance check:

- In Obsidian, open two Markdown notes.
- Put note A's cursor on a distinctive line/column.
- Put note B's cursor on a different distinctive line/column.
- Press `Ctrl-\` repeatedly and confirm each note reopens with its own last cursor position restored.
- Repeat after moving note A's cursor, navigating away through a non-`Ctrl-\` path, and then using `Ctrl-\` to confirm
  the update listener captured the newer position.

Before finishing:

```bash
git -C /home/bryan/bob status --short
git status --short
```

If the vault plugin is edited, commit only `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js` with the
required `/sase_git_commit` workflow, leaving the pre-existing dirty note files untouched.

## Risks

- Cursor updates from non-active editor panes could be misattributed if the active file lookup and CodeMirror update are
  out of sync. Mitigation: prefer active Markdown file checks, keep path updates conservative, and still capture
  directly immediately before plugin-driven file opens.
- `openFile` may resolve before the destination editor is ready. Mitigation: set cursor after `await openFile(...)` and
  schedule one deferred retry.
- Stored positions may be stale after note edits or sync changes. Mitigation: clamp line/ch to the opened document.
- Automated checks cannot fully prove live Obsidian focus timing. Mitigation: keep the implementation narrow and finish
  with a manual acceptance checklist.
