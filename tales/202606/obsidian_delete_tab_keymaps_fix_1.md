---
title: Fix Non-Firing Obsidian Delete-Tab Vim Keymaps
create_time: 2026-06-18 21:23:27
status: proposed
supersedes_commit: 478a0f6
prior_plan: sdd/tales/202606/obsidian_delete_tab_keymaps.md
prompt: sdd/prompts/202606/obsidian_delete_tab_keymaps_fix_1.md
---

# Fix Non-Firing Obsidian Delete-Tab Vim Keymaps

## Symptom

The previously shipped chords (commit `478a0f6`) do nothing. Pressing `d<`, `d>`, or `dD` in Obsidian Vim normal mode
never closes any tabs and produces no error — the keypresses are simply swallowed as ordinary Vim delete-operator input.

## Root Cause (confirmed by source inspection)

The three mappings in `obsidian_vimrc.md` all begin with `d`:

```
nmap d< :bob_close_tabs_left<CR>
nmap d> :bob_close_tabs_right<CR>
nmap dD :bob_close_other_tabs<CR>
```

`d` is a built-in **operator** in CodeMirror Vim (the engine behind Obsidian's Vim mode). Trace of why these maps are
dead on arrival:

1. `obsidian-vimrc-support`'s `loadVimCommands` reads each vimrc line and calls
   `codeMirrorVimObject.handleEx(cmEditor, line)` (plugin `main.js:792-799`). So `nmap ...` is registered as a normal
   CodeMirror Vim user keymap (lhs/rhs split on whitespace by CodeMirror's own ex parser).
2. On the first keystroke `d`, CodeMirror Vim's `matchCommand` evaluates the keymap. The built-in `d` operator yields a
   **full** match; the user map `d<`/`d>`/`dD` yields only a **partial** match. When a full match exists, `matchCommand`
   returns it immediately and discards the partial — so `d` resolves as the delete operator and enters operator-pending
   state.
3. The user map therefore never gets the chance to complete. This is true for _every_ normal-mode mapping whose lhs
   starts with an existing operator key (`d`, `c`, `y`, etc.).

The earlier "notation verification" (whether `<` needed `<lt>` escaping) examined an unrelated parse layer and had no
bearing on the failure: the maps loaded fine; they were simply shadowed by the `d` operator.

The plugin command layer is **not** at fault. The three commands (`close-tabs-left`, `close-tabs-right`,
`close-other-tabs`) and the `closeSiblingTabs` helper exist and pass `node --check` in
`.obsidian/plugins/bob-navigation-hotkeys/main.js` (commit `478a0f6`). They were never invoked because the keymaps never
fired.

## The Fix (chord scheme approved by user: backslash leader)

Re-point the three normal-mode chords onto a leader key that has **no** built-in CodeMirror Vim command, so the first
keystroke produces only a partial match and CodeMirror waits for the rest of the chord:

| Action                  | Old (broken) | New (working) | Command ID         |
| ----------------------- | ------------ | ------------- | ------------------ |
| Close tabs to the left  | `d<`         | `\d<`         | `close-tabs-left`  |
| Close tabs to the right | `d>`         | `\d>`         | `close-tabs-right` |
| Close all other tabs    | `dD`         | `\do`         | `close-other-tabs` |

Rationale:

- `\` is unbound in CodeMirror Vim, so `\` (partial) → `\d` (partial) → `\d<` / `\d>` / `\do` (full match) fires
  cleanly. Verified there are no existing `\`-prefixed mappings in `obsidian_vimrc.md`, so no chord collides.
- `\` is also Bryan's Neovim localleader, and `\do` mirrors his Neovim `<leader>do` for "close other buffers", keeping
  muscle memory consistent. Mnemonic preserved: `d` = delete/close, `<` left / `>` right / `o` others.
- Use the literal `\` character (not `<leader>`); CodeMirror Vim does not reliably honor a `mapleader` abstraction,
  whereas a literal key always works.

This is the only behavioral change. The exmap wrappers and command IDs are unchanged; only the three `nmap` left-hand
sides change.

## Scope

Single file edited under `/home/bryan/bob`:

- `obsidian_vimrc.md` — change the three `nmap` LHS values (`d<`→`\d<`, `d>`→`\d>`, `dD`→`\do`). The three `exmap` lines
  (16-18) stay as-is.

No edits to:

- `.obsidian/plugins/bob-navigation-hotkeys/main.js` (commands + helper already correct)
- `.obsidian/hotkeys.json`, `.obsidian/plugins/obsidian-vimrc-support/data.json`, `community-plugins.json`, manifests
- any Markdown notes/templates, memory files, or bob-cli sources
- the vault's unrelated dirty/untracked files (must remain untouched and unstaged)

## Implementation Steps

1. Re-check state immediately before editing:
   - `git -C /home/bryan/bob status --short --untracked-files=all` (confirm `obsidian_vimrc.md` still clean).
   - Re-read the three `nmap d*` lines so the edit targets the exact current text.

2. Edit `obsidian_vimrc.md`:
   - `nmap d< :bob_close_tabs_left<CR>` → `nmap \d< :bob_close_tabs_left<CR>`
   - `nmap d> :bob_close_tabs_right<CR>` → `nmap \d> :bob_close_tabs_right<CR>`
   - `nmap dD :bob_close_other_tabs<CR>` → `nmap \do :bob_close_other_tabs<CR>`

3. Validate statically:
   - `git -C /home/bryan/bob diff -- obsidian_vimrc.md` shows exactly the three LHS changes and nothing else.
   - `git -C /home/bryan/bob diff --check -- obsidian_vimrc.md` (no whitespace errors).

4. Manual verification after reloading the plugin / re-sourcing the vimrc (cannot be driven headlessly):
   - **Isolate the helper first:** run each command from the Command Palette ("Close tabs to the left/right", "Close
     other tabs") with ≥4 tabs in one group. This confirms `closeSiblingTabs` works independent of the keymap. (If a
     command misbehaves here, that's a separate plugin-helper bug to fix — out of scope for this keymap fix.)
   - **Then the chords:** with an interior tab active, `\d<` closes left-only, `\d>` right-only, `\do` all others;
     active tab stays focused. Boundary cases (leftmost `\d<`, rightmost `\d>`, single-tab `\do`) no-op without errors.
   - Regression: confirm `d`, `dw`, `dd`, `D` still behave as native Vim deletes; confirm insert mode types `\`
     normally; confirm other splits/tab-groups are unaffected.

5. Commit only `obsidian_vimrc.md` via the SASE git workflow, leaving all unrelated dirty/untracked vault files
   untouched. Review the staged diff before committing.

## Risks & Mitigations

- **Risk:** literal `<`/`>` as the final chord key is mis-parsed. _Mitigation:_ `<`/`>` are matched as single literal
  keys by CodeMirror's key splitter (same as the working `[<Space>` map already in the vimrc); only the `d`-operator
  shadow caused the prior failure, which the leader change removes. The command-palette test in step 4 also de-risks by
  exercising the commands without the chord.
- **Risk:** `\` collides with an existing or future mapping. _Mitigation:_ confirmed no current `\`-prefixed maps;
  `\d<`/`\d>`/`\do` share the `\d` prefix only with each other.
- **Risk:** the helper itself has a latent bug (never exercised before). _Mitigation:_ step 4 tests the commands via
  palette first to surface any helper bug separately from the keymap fix.
- **Risk:** staging unrelated dirty vault files. _Mitigation:_ re-check status; stage only `obsidian_vimrc.md`.

## Done Criteria

- `obsidian_vimrc.md` maps normal-mode `\d<`, `\d>`, `\do` to the three existing close-tab commands; no `d`-prefixed tab
  maps remain.
- `git diff` shows only the three LHS changes.
- Manual smoke test confirms the chords close the correct tabs, the active tab stays focused, and native `d`/`dw`/
  `dd`/`D` deletes are unaffected.
- Final vault commit contains only the `obsidian_vimrc.md` change.
