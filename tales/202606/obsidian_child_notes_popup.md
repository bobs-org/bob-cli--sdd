---
status: planned
create_time: 2026-06-03 10:09:28
prompt: sdd/prompts/202606/obsidian_child_notes_popup.md
---

# Obsidian Child Notes Popup Plan

## Goal

Add an Obsidian keymap for `Option+Ctrl+C` that opens a popup listing the active note file's direct child note files.
Selecting one child in the popup should jump to that note.

A direct child note is any Markdown note whose `parent` frontmatter property points to the currently active Markdown
note. This feature should not use `Ctrl+C`, so it does not conflict with copy. In Obsidian hotkey JSON, macOS Option is
stored as `Alt`, so the binding should be `Ctrl` + `Alt` + `C`.

## Context Reviewed

- Read project short memory from `memory/short/sase.md`.
- Read Obsidian long memory through:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault and obsidian-headless context before adding an Obsidian keymap and note-child popup"`.
- Read `/home/bryan/bob/AGENTS.md`; the vault is actively synced, so any vault edits must preserve unrelated dirty files
  and be committed with the required `/sase_git_commit` workflow before finishing.
- Current vault status has unrelated dirty note/generated paths:
  - `obsidian.md`
  - `sase.md`
  - `2026/20260603_day.md`
  - `lib/`
  - `old_lib/`
  - `ref/`
- The likely target files are clean and tracked:
  - `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
  - `/home/bryan/bob/.obsidian/hotkeys.json`
- `bob-navigation-hotkeys` already owns nearby navigation behavior:
  - frontmatter `parent` and `template` navigation commands;
  - next/previous body link navigation;
  - alternate-file navigation;
  - current/alternate file tracking;
  - link target normalization and Obsidian link resolution helpers.
- Existing hotkeys are persisted in `/home/bryan/bob/.obsidian/hotkeys.json`, including
  `bob-navigation-hotkeys:open-parent-note` on `Ctrl+6` and `bob-navigation-hotkeys:open-alternate-file` on `Ctrl+\`.

## Product Decisions

1. Implement this in `bob-navigation-hotkeys`.
   - The new behavior is navigation-oriented and should reuse existing link parsing/resolution helpers.
   - No `bob-cli` Rust change is expected.

2. Treat "children" as direct children only.
   - Include a note if its own `parent` frontmatter resolves to the active note file.
   - Do not include grandchildren.
   - Do not include non-Markdown files.

3. Resolve parent values the same way the existing parent-note command resolves frontmatter links.
   - Support wikilinks like `[[obsidian]]`, aliases like `[[obsidian|Obsidian]]`, markdown links, quoted values, bare
     note targets like `obsidian`, and path-like targets like `projects/foo` or `projects/foo.md`.
   - Support scalar and array frontmatter values.
   - Compare resolved files by vault-relative path, using `metadataCache.getFirstLinkpathDest(...)` with the child file
     as the source path.

4. Make the popup quick to operate from the keyboard.
   - Show all direct child notes in a modal.
   - Add a filter input so long child lists can be narrowed.
   - Support ArrowUp/ArrowDown selection movement, Enter to open the selected child, click to open, and Escape via the
     normal Obsidian modal behavior.
   - Sort children by vault-relative path for stable results.

5. Preserve existing navigation state behavior.
   - Capture the current editor cursor before opening a selected child, matching the plugin's alternate-file position
     tracking intent.
   - Use `workspace.getLeaf(false).openFile(file)` for the selected child so the existing `file-open` listener updates
     `currentFilePath` and `alternateFilePath`.
   - Leave existing commands and Vim mappings unchanged.

6. Keep styling minimal.
   - Use Obsidian's built-in modal/input/button/list classes where practical.
   - Avoid adding a new `styles.css` unless implementation shows the built-in styles are insufficient.

## Implementation Scope

Expected vault files to edit:

- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
- `/home/bryan/bob/.obsidian/hotkeys.json`

Likely `main.js` changes:

- Import `Modal` from `obsidian`.
- Add a command:
  - id: `open-child-note`
  - name: `Open child note`
  - callback: `() => this.openChildNotePicker()`
- Add `openChildNotePicker()`:
  - require an active Markdown file;
  - collect direct child files;
  - show a `Notice("No child notes found")` if none exist;
  - otherwise open a child-note picker modal.
- Add `collectChildNotes(parentFile)`:
  - iterate `this.app.vault.getMarkdownFiles()`;
  - skip `parentFile`;
  - inspect each file's cached frontmatter via `metadataCache.getFileCache(file)?.frontmatter`;
  - test whether any `parent` value resolves to `parentFile`.
- Add helpers around existing parsing/resolution:
  - `getFrontmatterLinks(frontmatter, fieldName)` returning all normalized link targets instead of only the first;
  - `frontmatterFieldPointsToFile(frontmatter, fieldName, targetFile, sourcePath)`;
  - `resolveLinkTargetFile(linkTarget, sourcePath)` to share the existing `getFirstLinkpathDest` logic.
- Adjust existing `getFrontmatterLink(...)` to delegate to `getFrontmatterLinks(...)[0]` so current parent/template
  behavior stays unchanged.
- Add a `ChildNotePickerModal extends Modal` class:
  - render a title, filter input, and selectable rows;
  - keep `selectedIndex` within visible results;
  - rerender on filter changes;
  - open the selected file through a plugin method such as `openChildNote(file)`;
  - close after successful selection.
- Add an `openChildNote(file)` method that captures the active file position and opens the chosen Markdown file.

Likely `hotkeys.json` change:

- Add:

```json
"bob-navigation-hotkeys:open-child-note": [
  {
    "modifiers": ["Ctrl", "Alt"],
    "key": "C"
  }
]
```

## Verification Plan

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js
jq '.' /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/manifest.json
jq '.' /home/bryan/bob/.obsidian/hotkeys.json
```

Focused Node checks with stubbed `obsidian` and `@codemirror/view` modules:

- `getFrontmatterLinks` returns all parent targets from scalar and array frontmatter values.
- Existing `getFrontmatterLink` still returns the first usable target.
- Child collection includes notes whose `parent` frontmatter resolves to the active note.
- Child collection supports bare parent values, wikilinks, aliases, markdown links, and `.md` suffixes through existing
  normalization.
- Child collection excludes non-children, the active note itself, and Markdown files without `parent`.
- The picker modal filters visible rows case-insensitively and keeps selection in range.
- Enter opens the currently selected child file; click opens the clicked child file.
- `openChildNote` captures the current cursor position before opening the selected file.

Manual live-vault acceptance check:

- Open a note that has at least one direct child via `parent` frontmatter.
- Press `Option+Ctrl+C`.
- Confirm a popup appears with the direct child notes.
- Type part of a child path/name to filter.
- Use ArrowUp/ArrowDown and Enter to open a child.
- Reopen the parent and confirm clicking a child row also opens it.
- Open a note without direct children and confirm the command shows a clear notice rather than an empty modal.

Before finishing:

```bash
git -C /home/bryan/bob status --short
git status --short
```

If vault files were changed, commit only the task-related vault files with the required `/sase_git_commit` workflow,
leaving pre-existing dirty note/generated paths alone.

## Risks

- `metadataCache` can be stale immediately after an unsaved frontmatter edit. This is acceptable for a hotkey navigator;
  the command should use Obsidian's cached metadata and pick up changes after Obsidian processes them.
- Parent values that cannot be resolved by Obsidian's link resolver will not be treated as children. Supporting the
  existing parent command's link formats keeps the behavior consistent.
- Automated checks can validate parsing and modal behavior, but final focus timing should still be smoke-tested manually
  in Obsidian.
