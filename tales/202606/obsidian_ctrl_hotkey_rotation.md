---
create_time: 2026-06-06 08:12:23
status: done
prompt: sdd/prompts/202606/obsidian_ctrl_hotkey_rotation.md
---
# Obsidian Ctrl Hotkey Rotation Plan

## Goal

Rotate two persisted Obsidian global hotkeys in Bryan's `~/bob` vault:

- Move `bob-navigation-hotkeys:open-child-note` from `<Ctrl+->` to `<Ctrl+=>`.
- Move `bob-navigation-hotkeys:open-parent-note` from `<Ctrl+6>` to `<Ctrl+->`.

The command behavior should remain unchanged. This is expected to be a one-file hotkey configuration change, not a
plugin implementation change.

## Context Reviewed

- Project short memory: `memory/short/sase.md`.
- Obsidian long memory via:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault and hotkey workflow context before planning keymap migration"`.
- Vault instructions: `/home/bryan/bob/AGENTS.md`.
  - The vault is actively synced.
  - Existing uncommitted changes may be legitimate user or sync changes.
  - Inspect status before editing.
  - Do not overwrite, revert, stage, or commit unrelated changes.
  - Any task-related changes under `~/bob` must be committed with the required SASE commit workflow before terminating
    after implementation edits.
- Live hotkey file: `/home/bryan/bob/.obsidian/hotkeys.json`.
- Live command registration: `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`.
- Live vimrc file: `/home/bryan/bob/.obsidian.vimrc`.
- Prior keymap plans:
  - `sdd/tales/202606/obsidian_child_notes_popup.md`
  - `sdd/tales/202606/child_note_keymap_dash.md`
  - `sdd/tales/202606/daily_dash_keymap.md`
  - `sdd/tales/202606/obsidian_vimrc_keymaps.md`

## Current Findings

- `/home/bryan/bob/.obsidian/hotkeys.json` is currently clean relative to vault `HEAD`.
- The vault has unrelated dirty and untracked files, including `.obsidian/community-plugins.json`, several notes, and
  today's daily note. These must be left untouched.
- The two relevant hotkey entries currently are:

```json
"bob-navigation-hotkeys:open-parent-note": [
  {
    "modifiers": ["Ctrl"],
    "key": "6"
  }
],
"bob-navigation-hotkeys:open-child-note": [
  {
    "modifiers": ["Ctrl"],
    "key": "-"
  }
]
```

- No existing `Ctrl+=` binding is present in `hotkeys.json`.
- No other current hotkey uses `Ctrl+-` except `bob-navigation-hotkeys:open-child-note`.
- `bob-navigation-hotkeys/main.js` registers stable command IDs:
  - `open-parent-note` -> `bob-navigation-hotkeys:open-parent-note`
  - `open-child-note` -> `bob-navigation-hotkeys:open-child-note`
- `.obsidian.vimrc` defines an `exmap bob_child_note obcommand bob-navigation-hotkeys:open-child-note`, but it does not
  currently bind `Ctrl+-`, `Ctrl+6`, or `Ctrl+=`. This request should not require vimrc changes.

## Product Decision

Use Obsidian's persisted global hotkey configuration as the source of truth for this migration.

This keeps the current command scope the same as before: both parent-note and child-note actions remain global Obsidian
hotkeys rather than Vim-normal-mode-only mappings. The earlier vimrc migration intentionally left the global child-note
hotkey in `hotkeys.json`; this request is a rotation of those global chords, not a migration into vimrc.

## Implementation Scope

Expected file to edit:

- `/home/bryan/bob/.obsidian/hotkeys.json`

Expected changes:

- Change `bob-navigation-hotkeys:open-child-note` from:
  - modifiers: `["Ctrl"]`
  - key: `"-"`
- to:
  - modifiers: `["Ctrl"]`
  - key: `"="`

- Change `bob-navigation-hotkeys:open-parent-note` from:
  - modifiers: `["Ctrl"]`
  - key: `"6"`
- to:
  - modifiers: `["Ctrl"]`
  - key: `"-"`

No expected edits:

- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/manifest.json`
- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/styles.css`
- `/home/bryan/bob/.obsidian.vimrc`
- `/home/bryan/bob/.obsidian/plugins/obsidian-vimrc-support/data.json`
- Daily notes, templates, Bases files, Templater data, or unrelated synced vault content
- `bob-cli` Rust, Python, shell, or project memory files

## Implementation Approach

1. Re-check starting state immediately before editing.
   - `git -C /home/bryan/bob status --short`
   - `git -C /home/bryan/bob diff -- .obsidian/hotkeys.json`
   - Confirm `hotkeys.json` is still clean or only has task-understood changes.

2. Make a minimal JSON edit.
   - Update only the two `key` values for the two Bob navigation command entries.
   - Preserve modifier arrays as `["Ctrl"]`.
   - Preserve unrelated hotkeys and file formatting as much as practical.
   - Avoid broad reformatting that rewrites the whole JSON file.

3. Verify no duplicate/conflicting target chord remains.
   - Confirm `Ctrl+=` maps only to `bob-navigation-hotkeys:open-child-note`.
   - Confirm `Ctrl+-` maps only to `bob-navigation-hotkeys:open-parent-note`.
   - Confirm `Ctrl+6` no longer maps to `bob-navigation-hotkeys:open-parent-note`.

4. Validate statically.
   - `jq '.' /home/bryan/bob/.obsidian/hotkeys.json`
   - `git -C /home/bryan/bob diff --check -- .obsidian/hotkeys.json`
   - `git -C /home/bryan/bob diff -- .obsidian/hotkeys.json`

5. Optional syntax sanity for the plugin command source.
   - Run `node -c /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js` only as a guardrail if the file is
     touched unexpectedly or if command registration needs rechecking.

6. Manual live-vault smoke test after Obsidian reloads/syncs the hotkey file.
   - Press `Ctrl+=` from a note context and confirm the child-note picker opens.
   - Press `Ctrl+-` and confirm the parent note opens.
   - Press `Ctrl+6` and confirm it no longer opens the parent note unless another Obsidian/user binding exists outside
     this JSON.
   - Confirm nearby bindings still work: `Ctrl+.` opens the template note, `Ctrl+\` opens the alternate file, and bare
     `-` in Vim normal mode still opens the daily note through `.obsidian.vimrc`.

7. Finish with repository hygiene.
   - Re-check `git -C /home/bryan/bob status --short`.
   - Confirm the final task diff is limited to `.obsidian/hotkeys.json`.
   - If implementation edits are made under `~/bob`, commit only the task-related file with the required
     `sase_git_commit` workflow, leaving unrelated dirty and untracked vault files untouched.

## Risks And Mitigations

- Risk: Obsidian may serialize the equals key differently on this platform.
  - Mitigation: start with `"key": "="`, which matches Obsidian's JSON style for literal keys; if live testing shows
    Obsidian rewrites or ignores it, adjust only that one key value to Obsidian's observed representation.

- Risk: `Ctrl+-` may overlap with zoom-out or another app/OS-level shortcut.
  - Mitigation: this chord is already used successfully by Obsidian for the child-note picker, so moving it to the
    parent-note command should preserve the same capture behavior.

- Risk: `Ctrl+=` may overlap with zoom-in semantics or may require `Ctrl+Shift+=` on some keyboards.
  - Mitigation: validate manually in Obsidian. If Obsidian cannot capture `Ctrl+=`, report the observed behavior before
    changing plugin code or inventing a fallback.

- Risk: the vault's unrelated dirty state could hide accidental edits.
  - Mitigation: use targeted diffs against `.obsidian/hotkeys.json` before and after editing, and never stage or commit
    unrelated paths.

## Done Criteria

- `bob-navigation-hotkeys:open-child-note` is bound to `Ctrl+=` in `/home/bryan/bob/.obsidian/hotkeys.json`.
- `bob-navigation-hotkeys:open-parent-note` is bound to `Ctrl+-` in `/home/bryan/bob/.obsidian/hotkeys.json`.
- No remaining Bob navigation hotkey entry uses `Ctrl+6`.
- Static JSON and diff checks pass.
- No unrelated vault files are modified, staged, reverted, or committed.
- If implementation edits are made, the task-related vault change is committed with the required SASE commit workflow.
