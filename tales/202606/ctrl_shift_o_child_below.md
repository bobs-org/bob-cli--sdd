---
create_time: 2026-06-15 08:22:50
status: done
prompt: sdd/prompts/202606/ctrl_shift_o_child_below.md
---
# Change Child-Bullet Trigger From Alt+Shift+o To Ctrl+Shift+o

## Goal

Change Bryan's live Obsidian child-bullet-below trigger from `<Alt+Shift+o>` / `<Option+Shift+o>` to `<Ctrl+Shift+o>`.

The desired behavior after implementation:

- In Vim normal mode, `<Ctrl+Shift+o>` creates a plain child bullet below the current line.
- The inserted line keeps the existing child-bullet prefix rule: current leading whitespace, one Obsidian tab indent,
  then `- `.
- The cursor lands after `- ` and Vim enters insert mode.
- `<Alt+Shift+o>` no longer creates a child bullet.
- The old child-bullet-above command remains available as a command, but it stays unbound unless there is an explicit
  reason to bind it again.

## Context Reviewed

- Required Obsidian memory was read with:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault and plugin workflow context before planning hotkey changes"`.
- Workspace short memory `memory/short/sase.md` was reviewed.
- The previous completed plan `sdd/tales/202606/obsidian_alt_shift_o_child_below.md` was reviewed.
- Live vault target files:
  - `/home/bryan/bob/.obsidian/hotkeys.json`
  - `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`
- Current live hotkey state:
  - `task-status-cycler:open-child-bullet-line-below` is bound to `{"modifiers":["Alt"],"key":"O"}`.
  - `task-status-cycler:open-child-bullet-line-above` is unbound with `[]`.
  - No configured hotkey currently uses `{"modifiers":["Ctrl","Shift"],"key":"O"}`.
- Current live plugin fallback state:
  - `getChildBulletKeydownDirection()` requires `altKey`, rejects `ctrlKey` and `metaKey`, accepts `KeyO` / `o` / `O` /
    `ø` / `Ø`, and returns `"below"`.
  - `getChildBulletBeforeInputDirection()` maps both `ø` and `Ø` to `"below"`.
  - The capture listeners are registered on both `window` and `document`, with a `WeakSet` guard to avoid duplicate
    insertion.

## Diagnosis

A hotkey-only edit would be incomplete. The previous Alt/Option workaround installed a capture-phase fallback so the
plugin can catch macOS Option-generated input paths before Obsidian or CodeMirror/Vim swallows them. If only
`hotkeys.json` changes to `<Ctrl+Shift+o>`, the existing fallback would still make `<Alt+Shift+o>` and possibly
Option-generated `Ø` insert a child bullet below.

The implementation therefore needs two coordinated changes:

1. Retarget the official Obsidian hotkey binding to `<Ctrl+Shift+o>`.
2. Retarget or remove the custom fallback paths so Alt/Option input is no longer a supported trigger.

`<Ctrl+Shift+o>` should arrive as a normal `keydown` event, so the macOS `beforeinput` handling for `ø` / `Ø` is not
part of the new desired behavior.

## Implementation Strategy

1. Update `.obsidian/hotkeys.json`.
   - Change `task-status-cycler:open-child-bullet-line-below` to: `{"modifiers":["Ctrl","Shift"],"key":"O"}`.
   - Keep `task-status-cycler:open-child-bullet-line-above` as `[]`.
   - Preserve the existing JSON formatting style and avoid unrelated hotkey churn.
   - Re-check that no other entry uses the same `Ctrl` + `Shift` + `O` chord.

2. Update `task-status-cycler/main.js` fallback dispatch.
   - Change `getChildBulletKeydownDirection()` so the child-bullet fallback only accepts the new chord:
     `ctrlKey === true`, `shiftKey === true`, `altKey === false`, `metaKey === false`, and `KeyO` / `O`.
   - Return `"below"` for that chord.
   - Stop accepting Alt/Option paths in this fallback.
   - Update comments so they describe the new Ctrl+Shift behavior rather than the old macOS Option workaround.

3. Remove or disable the obsolete `beforeinput` Option fallback.
   - Preferred implementation: remove the `beforeinput` listener and the `handleChildBulletBeforeInput()` /
     `getChildBulletBeforeInputDirection()` helpers if they have no remaining callers.
   - Acceptable minimal implementation: keep the helper shape but make it return `null` for all events, with comments
     explaining that Ctrl+Shift+o is handled by keydown only.
   - In either case, `ø` and `Ø` must no longer trigger child-bullet insertion.

4. Leave insertion behavior unchanged.
   - Do not change `handleVimOpenChildBulletLineBelow()`.
   - Do not change `getChildBulletOpenLinePrefix()`.
   - Do not change cursor placement, Vim insert-mode transition, editor-target gating, or normal-mode gating.
   - Keep command IDs stable so Obsidian's hotkey storage does not lose the command association.

## Files Expected To Change After Approval

- `/home/bryan/bob/.obsidian/hotkeys.json`
- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`

## Files Expected Not To Change

- Memory files.
- Markdown notes and unrelated dirty/untracked vault files.
- `obsidian_vimrc.md`.
- Other community plugins.
- Bob CLI source files, except for normal SASE plan/tale bookkeeping if this plan is approved and later finalized.

## Validation Plan

1. Pre-edit state checks after approval:
   - `git -C /home/bryan/bob status --short --branch`
   - `git -C /home/bryan/bob diff -- .obsidian/plugins/task-status-cycler/main.js .obsidian/hotkeys.json`
   - Query `hotkeys.json` for the below/above entries and any `Ctrl` + `Shift` + `O` conflicts.

2. Static validation:
   - `node --check /home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`
   - `jq` parse/assertions for `/home/bryan/bob/.obsidian/hotkeys.json`
   - `git -C /home/bryan/bob diff --check -- .obsidian/plugins/task-status-cycler/main.js .obsidian/hotkeys.json`

3. Focused harness validation against the real plugin code:
   - `Ctrl+Shift+KeyO` / `key: "O"` inserts below.
   - The inserted text uses `\t- ` for a first-level child bullet where appropriate.
   - Cursor lands after the child prefix and Vim insert mode is requested.
   - Insert, visual, and replace Vim modes fall through without preventing default.
   - Duplicate window/document capture dispatch for the same event inserts only once.
   - The direct `open-child-bullet-line-below` command still inserts below.
   - `Alt+Shift+KeyO`, `Alt+KeyO`, `key: "Ø"`, `key: "ø"`, and `beforeinput` data `Ø` / `ø` do not insert and do not
     prevent default.

4. Manual GUI smoke test after reloading Obsidian/plugin/hotkeys:
   - In Vim normal mode, `<Ctrl+Shift+o>` creates a child bullet below and enters insert mode.
   - In Vim normal mode, `<Alt+Shift+o>` no longer creates a child bullet.
   - In Vim insert mode, `<Ctrl+Shift+o>` falls through.
   - Existing sibling hotkeys still work, especially `Alt+]`, `Alt+[`, and `Ctrl+Shift+]`.

5. Review and commit only after validation:
   - Confirm the final vault diff is limited to the two target files.
   - Stage only those files.
   - Commit through the required SASE git commit workflow if the implementation is approved and completed.
   - Leave unrelated dirty note files untouched.

## Risks And Mitigations

- Risk: Obsidian serializes shifted letter hotkeys as uppercase keys, but a later GUI settings save could rewrite the
  entry.
  - Mitigation: follow existing local examples such as `Ctrl+Shift+N`, which use
    `{"modifiers":["Ctrl","Shift"],"key":"N"}`, and manually verify the GUI.

- Risk: Ctrl+Shift+O may be intercepted by the platform, Electron, or Obsidian before the plugin sees it.
  - Mitigation: keep a narrow capture-phase `keydown` fallback for exactly Ctrl+Shift+O, matching the command binding,
    and verify in the GUI.

- Risk: Leaving the old `beforeinput` fallback active would preserve the old Alt/Option trigger accidentally.
  - Mitigation: remove or disable beforeinput handling and test `ø` / `Ø` paths as negative cases.

- Risk: Over-removing fallback code could affect unrelated task-status-cycler keymaps.
  - Mitigation: touch only the child-bullet fallback functions/listeners and validate existing task/status hotkeys.

## Done Criteria

- `<Ctrl+Shift+o>` creates a child bullet below in Vim normal mode.
- `<Alt+Shift+o>` no longer creates a child bullet.
- `ø` / `Ø` beforeinput paths no longer trigger child-bullet insertion.
- Child-bullet prefix, cursor placement, and insert-mode transition match the current below handler.
- Non-normal Vim modes still fall through.
- Static checks and focused harness checks pass.
- Final implementation diff is limited to the plugin and hotkey config, with unrelated dirty files untouched.
