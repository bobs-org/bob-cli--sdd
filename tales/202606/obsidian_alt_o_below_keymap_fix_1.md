---
create_time: 2026-06-15 07:47:21
status: done
prompt: sdd/prompts/202606/obsidian_alt_o_below_keymap_fix_1.md
---
# Fix Plain Option+o Child-Bullet Keymap in Obsidian

## Goal

Make plain `Option+o` / `Alt+o` create the child bullet below the current line in Bryan's live Obsidian vault, matching
the now-working `Option+Shift+o` / `Alt+Shift+o` behavior for creating the child bullet above.

The fix must preserve:

- Vim normal-mode only behavior.
- Existing plain `o` / `O` continuation behavior.
- Existing `Option+Shift+o` child-bullet-above behavior.
- The child prefix rule: current leading whitespace plus two spaces plus `- `.
- Cursor placement after the generated `- ` and transition into Vim insert mode.

## Context Reviewed

- Required Obsidian memory was read with:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault/plugin workflow before diagnosing live hotkey behavior"`.
- Workspace short memory `memory/short/sase.md` was reviewed.
- Live vault instructions `/home/bryan/bob/AGENTS.md` were reviewed. The vault is actively synced, so status must be
  checked before editing, unrelated dirty files must be left alone, and any vault edits must be committed with the SASE
  git commit workflow before termination.
- The live target is `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`.
- Current live vault status has unrelated dirty note files plus an uncommitted `task-status-cycler/main.js` change from
  the previous hotkey attempt.
- `.obsidian/hotkeys.json` already contains the Obsidian command bindings:
  - `task-status-cycler:open-child-bullet-line-below` -> `Alt` + `o`
  - `task-status-cycler:open-child-bullet-line-above` -> `Alt` + `O`
- The current plugin has a document-capture `keydown` fallback that recognizes:
  - physical `event.code === "KeyO"`
  - macOS-produced `event.key === "ø"` / `"Ø"`
  - plain `"o"` / `"O"`
- The current resolver also checks Vim mode through `cm.state.vim` and the enabled `obsidian-vimrc-support`
  `currentVimStatus` fallback.

## Current Differential Diagnosis

`Option+Shift+o` working is an important new fact. It proves the following pieces are good enough at runtime:

- the plugin is loaded;
- the child-bullet command/handler path works;
- the focused Markdown editor and CodeMirror resolver can succeed;
- the Vim normal-mode gate can allow the action;
- the "above" direction handler works.

That narrows the remaining failure to behavior specific to the unshifted `Option+o` input event. The likely failure is
not the insertion handler or the command registration. The likely failure is that the unshifted macOS key event is
taking a different browser/Electron path than `Option+Shift+o`.

Most likely causes, in order:

1. Plain `Option+o` is being delivered as a text/composition input (`ø`) and either has `event.isComposing === true` or
   reaches CodeMirror through `beforeinput` instead of the current `keydown` listener. The current fallback rejects
   composing keydown events and does not handle `beforeinput`.
2. Plain `Option+o` is stopped before the event reaches the plugin's `document` capture listener, while the shifted
   variant is not. A `window` or editor-input-field capture hook may be needed.
3. Plain `Option+o` is falling through to CodeMirror/Vim's existing plain `o` behavior because the fallback does not
   intercept it early enough.

The enabled `obsidian-vimrc-support` plugin has a relevant precedent: its fixed-layout workaround hooks the CodeMirror
input field directly and rewrites keys from `event.code`. That supports moving this fallback closer to the editor input
event path instead of relying only on `document` `keydown`.

## Files Expected To Change

- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`

The existing uncommitted changes in this file are part of the current Alt/Option keymap fix line. The final commit
should include the cumulative task-related plugin change.

## Files Expected Not To Change

- `/home/bryan/bob/.obsidian/hotkeys.json`, unless runtime evidence shows the current entries have been removed or
  malformed.
- `/home/bryan/bob/obsidian_vimrc.md`
- Other community plugin files.
- Markdown note content and unrelated dirty vault files.
- `bob-cli` source files and memory files.

## Implementation Plan

1. Re-check live state before editing.
   - Run `git -C /home/bryan/bob status --short --branch`.
   - Review the current plugin diff with `git -C /home/bryan/bob diff -- .obsidian/plugins/task-status-cycler/main.js`.
   - Confirm `hotkeys.json` still has the two child-bullet command entries, but do not edit it unless it has drifted.

2. Add diagnosis focused on the actual unshifted event path.
   - If a GUI Obsidian DevTools session is available, inspect `keydown`, `beforeinput`, and composition events for
     `Option+o` and `Option+Shift+o`, logging `type`, `key`, `code`, `altKey`, `shiftKey`, `isComposing`, `inputType`,
     `data`, and target class names.
   - If the GUI is not automatable from this shell, proceed with the robust fix below and cover the likely event shapes
     in the Node harness.

3. Broaden the fallback from "document keydown only" to "early keydown plus text-input fallback".
   - Register the keydown handler on `window` / `activeWindow` in capture phase when available, with cleanup on unload.
   - Keep or replace the existing `document` capture registration as needed for compatibility, using a per-event marker
     or WeakSet so the same physical event cannot be handled twice.
   - Add a capture-phase `beforeinput` listener for the active document/editor path to catch macOS text input for
     `data === "ø"` and `data === "Ø"` when no usable keydown reaches the plugin.

4. Consolidate dispatch through one helper.
   - Keep one helper that resolves the focused Markdown editor, resolves the usable normal-mode Vim `cm`, prevents the
     default event, stops propagation, and calls the existing below/above child-bullet handlers.
   - Keep the existing insertion handlers unchanged unless validation exposes a separate bug.

5. Fix the unshifted recognition rules narrowly.
   - For `keydown`, accept `Alt/Option+KeyO` even when `event.isComposing` is true; composition is exactly one plausible
     macOS path for plain `Option+o`.
   - Continue rejecting ctrl/meta combinations and non-editor targets.
   - For `beforeinput`, accept only `data === "ø"` for below and `data === "Ø"` for above, and only when the same
     normal-mode Vim resolver succeeds.
   - Do not broadly map all `event.key === "Dead"` events to the child-bullet command unless runtime evidence shows it
     is specifically necessary and can be tied to physical `KeyO`; a broad dead-key match would be too risky.

6. Preserve normal-mode fallthrough.
   - The fallback should still return without preventing default in insert, visual, and replace modes when those modes
     are positively detected through `cm.state.vim` or `obsidian-vimrc-support.currentVimStatus`.
   - Unknown Vim state may remain fail-open only after a usable CodeMirror object is found, matching the previous fix.

7. Validate with static checks and a focused harness.
   - `node --check /home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`
   - `git -C /home/bryan/bob diff --check -- .obsidian/plugins/task-status-cycler/main.js`
   - Focused Node harness with mocked Obsidian and fake CodeMirror object:
     - `keydown` `Alt+KeyO` with `key: "ø"`, no shift -> below.
     - `keydown` `Alt+KeyO` with `key: "ø"` and `isComposing: true` -> below.
     - `keydown` `Alt+Shift+KeyO` with `key: "Ø"` -> above.
     - `beforeinput` with `data: "ø"` -> below.
     - `beforeinput` with `data: "Ø"` -> above.
     - insert/visual/replace mode fall through without preventing default.
     - non-editor targets fall through.
     - duplicate window/document listeners do not double-insert.
     - existing command callback path still works.

8. Manual smoke test in live Obsidian after reload.
   - In Vim normal mode, `Option+o` creates a plain child bullet below and enters insert mode.
   - In Vim normal mode, `Option+Shift+o` still creates a plain child bullet above and enters insert mode.
   - In Vim insert mode, both chords fall through.
   - Plain `o` / `O`, `Alt+]` / `Alt+[`, and other task-status-cycler mappings still work.

9. Review and commit.
   - Confirm the final vault diff is limited to `.obsidian/plugins/task-status-cycler/main.js`.
   - Stage only that file.
   - Commit through the required SASE git commit workflow.
   - Leave unrelated dirty note files untouched.

## Risks And Mitigations

- Risk: `beforeinput` catches a real `ø` typed from another keyboard layout in normal mode.
  - Mitigation: the handler is limited to the focused Markdown editor and normal-mode Vim resolver. In insert mode it
    must fall through.
- Risk: adding both window and document listeners double-handles the same event.
  - Mitigation: mark handled events or track them in a WeakSet before dispatching the insertion.
- Risk: intercepting composing `Option+o` breaks a text composition path in insert mode.
  - Mitigation: do not prevent default until after the normal-mode resolver succeeds.
- Risk: the issue is actually an Obsidian native hotkey conflict.
  - Mitigation: re-check `hotkeys.json`; if runtime evidence points to a hotkey conflict, report it and make a
    config-only adjustment only with explicit confirmation.

## Done Criteria

- `Option+o` creates the child bullet below in Vim normal mode in the live vault.
- `Option+Shift+o` remains working for the child bullet above.
- Both chords fall through outside normal mode.
- Existing plain `o` / `O` behavior is unchanged.
- Static checks and focused harness validation pass.
- The final vault diff is limited to the task plugin file.
- The vault plugin change is committed through SASE git commit, with unrelated dirty files untouched.
