---
create_time: 2026-06-06 13:19:03
status: done
prompt: sdd/prompts/202606/single_child_note_jump.md
---
# Plan: Single Child Note Direct Jump

## Goal

When Bryan presses the existing Obsidian `<Ctrl+=>` child-note hotkey and the active Markdown note has exactly one
direct child note, open that child note immediately instead of showing the child-note picker modal.

Keep the current behavior for the other cases:

- zero children: show the existing "No child notes found" notice;
- multiple children: show the existing polished child-note picker with filtering and keyboard navigation.

## Context Reviewed

- Project short memory: `memory/short/sase.md`.
- Obsidian long memory via:
  `sase memory read long/obsidian.md --reason "Need Obsidian workflow context before changing child-note navigation behavior"`.
- Live vault instructions: `/home/bryan/bob/AGENTS.md`.
  - The vault is actively synced.
  - Inspect vault status before editing.
  - Do not overwrite, revert, stage, or commit unrelated dirty files.
  - If implementation edits are made under `~/bob`, commit only task-related vault files with the required SASE commit
    workflow before terminating.
- Relevant prior plans:
  - `sdd/tales/202606/obsidian_child_notes_popup.md`
  - `sdd/tales/202606/obsidian_child_popup_usability.md`
  - `sdd/tales/202606/obsidian_child_popup_redesign.md`
  - `sdd/tales/202606/obsidian_vimrc_keymaps.md`
  - `sdd/tales/202606/obsidian_ctrl_hotkey_rotation.md`
- Live keymap state:
  - `/home/bryan/bob/.obsidian/hotkeys.json` binds `bob-navigation-hotkeys:open-child-note` to `<Ctrl+=>`.
  - `/home/bryan/bob/.obsidian.vimrc` defines `exmap bob_child_note obcommand bob-navigation-hotkeys:open-child-note`
    but does not bind `<Ctrl+=>`.
  - This request is a behavior change for the existing command, not a keymap migration.
- Live implementation:
  - `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js` registers the `open-child-note` command with
    `callback: () => this.openChildNotePicker()`.
  - `openChildNotePicker()` currently:
    - reads the active Markdown file;
    - calls `collectChildNotes(file)`;
    - shows "No child notes found" when `children.length === 0`;
    - opens `new ChildNotePickerModal(...)` for any non-empty child list.
  - `openChildNote(file)` already performs the desired direct-open behavior: validates the Markdown file, captures the
    current cursor position, opens the child in the current leaf, and shows notices for failure cases.
- Current vault status has unrelated dirty files, including `.obsidian/hotkeys.json`, other plugin files, notes, and
  untracked notes. The targeted diff for `bob-navigation-hotkeys/main.js` and `styles.css` is currently clean.

## Product Decision

Implement the direct jump inside `bob-navigation-hotkeys` by changing the command behavior, not the keymap.

The command should be cardinality-sensitive:

- `0` child notes: current notice behavior;
- `1` child note: call `openChildNote(children[0])` directly;
- `2+` child notes: current modal behavior.

This preserves the picker for ambiguous navigation and removes it only when it cannot add value.

## Implementation Scope

Expected file to edit:

- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`

Expected code change:

- Make `openChildNotePicker()` async, or otherwise await/catch the existing async direct-open path.
- After the zero-child branch, add a single-child branch:
  - `await this.openChildNote(children[0]);`
  - `return;`
- Leave the multiple-child branch unchanged:
  - `new ChildNotePickerModal(this.app, this, children, file).open();`

No expected edits:

- `/home/bryan/bob/.obsidian/hotkeys.json`
- `/home/bryan/bob/.obsidian.vimrc`
- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/styles.css`
- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/manifest.json`
- `bob-cli` Rust, Python, shell, docs, or memory files

## Verification Plan

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js
jq '.' /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/manifest.json
git -C /home/bryan/bob diff --check -- .obsidian/plugins/bob-navigation-hotkeys/main.js
```

Focused Node behavior check with stubbed `obsidian` and `@codemirror/view` modules:

- zero children: `openChildNotePicker()` shows the existing "No child notes found" notice and does not open a file;
- one child: `openChildNotePicker()` calls `openChildNote()` with that child and does not construct/open a modal;
- multiple children: `openChildNotePicker()` still opens the picker modal and does not directly open the first child.

Manual live-vault acceptance after reloading Obsidian or the `bob-navigation-hotkeys` plugin:

- Open a Markdown note with exactly one direct child and press `<Ctrl+=>`; confirm Obsidian jumps directly to that child
  note.
- Open a Markdown note with multiple direct children and press `<Ctrl+=>`; confirm the existing picker still appears and
  filtering/selection still works.
- Open a Markdown note with no direct children and press `<Ctrl+=>`; confirm the existing no-child notice still appears.
- Confirm nearby navigation still works: `<Ctrl+->` opens the parent note, `<Ctrl+.>` opens the template note, and
  `<Ctrl+\>` opens the alternate file.

Final hygiene:

```bash
git -C /home/bryan/bob status --short
git -C /home/bryan/bob diff -- .obsidian/plugins/bob-navigation-hotkeys/main.js
git status --short
```

If implementation edits are made under `~/bob`, stage and commit only `.obsidian/plugins/bob-navigation-hotkeys/main.js`
using the required SASE commit workflow, leaving unrelated vault changes untouched.

## Risks

- A direct jump skips the visual context/count shown by the picker. That is intentional only for the unambiguous
  one-child case.
- `metadataCache` can be stale immediately after editing frontmatter. This is already true for the picker because child
  collection uses the same cached metadata; no new behavior is introduced.
- If `openChildNote()` fails, the existing failure notices should remain responsible for user feedback. The new branch
  should not duplicate or obscure those notices.
- The vault has unrelated dirty files. Use targeted diffs before and after editing so the final implementation is
  limited to the navigation plugin source.

## Done Criteria

- Pressing `<Ctrl+=>` on a note with exactly one direct child opens that child directly.
- Pressing `<Ctrl+=>` on a note with multiple direct children still opens the child-note picker.
- Pressing `<Ctrl+=>` on a note with no direct children still shows "No child notes found".
- Static validation passes.
- Final task diff under `~/bob` is limited to `.obsidian/plugins/bob-navigation-hotkeys/main.js`.
