---
title: Obsidian Vimrc Keymap Migration Plan
create_time: 2026-06-05 13:59:25
status: done
prompt: sdd/prompts/202606/obsidian_vimrc_keymaps.md
---

# Obsidian Vimrc Keymap Migration Plan

## Goal

Move the simple Bob Obsidian Vim-mode key bindings into the newly installed `obsidian-vimrc-support` plugin, centered on
`~/bob/.obsidian.vimrc`, while preserving existing behavior for mappings that still require custom JavaScript editor
logic.

The migration should make `.obsidian.vimrc` the declarative home for normal-mode command dispatch, not a replacement for
the Bob plugins' command implementations.

## Context Reviewed

- Project short memory: `memory/short/sase.md`.
- Obsidian long memory via the required audited command:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault and workflow context before planning keymap migration to the Obsidian vimrc plugin"`.
- Research source: `sdd/research/202606/obsidian_improvements_consolidated.md`. Its first recommended improvement is to
  install `obsidian-vimrc-support` and move command-only Vim keymaps out of bespoke CM6 plugins.
- Live vault instructions: `/home/bryan/bob/AGENTS.md`. The vault is actively synced; implementation must inspect
  status, preserve unrelated dirty files, and commit any task-related vault edits with the required SASE commit workflow
  before terminating after edits.
- Current vault state: `/home/bryan/bob` is dirty with unrelated note/config changes, including
  `.obsidian/hotkeys.json`, templater data, daily notes, Bases files, and many untracked restaurant notes. These must be
  left alone except for the exact keymap files changed for this task.
- Installed vimrc plugin state: `obsidian-vimrc-support` is enabled in `.obsidian/community-plugins.json`. Its
  `data.json` points at `.obsidian.vimrc`, but `/home/bryan/bob/.obsidian.vimrc` does not exist yet. JavaScript commands
  are disabled, which is the safer default and should remain disabled.
- Current Bob keymap surfaces:
  - `bob-navigation-hotkeys/main.js` registers Vim mappings for `[[`, `]]`, `!`, and `-`.
  - `bob-navigation-hotkeys/main.js` registers Obsidian commands for parent, child, template, next link, previous link,
    and alternate file navigation.
  - `bob-ledger-tools/main.js` registers Vim mappings for `\\`, `\p`, `\P`, `\o`, and `\O`.
  - `.obsidian/hotkeys.json` currently binds global Obsidian hotkeys such as `Ctrl+6`, `Ctrl+-`, `Ctrl+.`, `Ctrl+\`,
    `Alt+P`, and app navigation.

## Key Product Decisions

1. Use `.obsidian.vimrc` for key-to-command dispatch.
   - Add a vault-root `/home/bryan/bob/.obsidian.vimrc`.
   - Prefer `exmap` wrappers plus `nmap` mappings, for example: `exmap bob_daily obcommand daily-notes` followed by
     `nmap - :bob_daily<CR>`.
   - This follows the research note's warning that `exmap` is the robust path when mapping Ex commands with arguments.

2. Keep JavaScript command implementations where they encode Bob behavior.
   - `bob-navigation-hotkeys` should still own parent/child/template/link resolution, child-note popup behavior,
     alternate-file tracking, and transclusion line mutation.
   - `bob-ledger-tools` should still own Pomodoro/ledger parsing, repeat-count behavior, cursor placement, and
     centering.
   - The migration should remove only redundant Vim key registration from those plugins after the equivalent command
     mapping exists in `.obsidian.vimrc`.

3. Treat `[[` and `]]` as part of the migration.
   - The installed vimrc plugin maps `[[` and `]]` to its own heading motions during initialization.
   - Bob currently uses those mappings for "previous labeled body link" and "next labeled body link".
   - Reasserting these mappings in `.obsidian.vimrc` avoids a load-order regression where the vimrc plugin silently
     changes Bob's `[[` and `]]` behavior.

4. Migrate daily-note `-` first.
   - The current `-` mapping only opens the core Daily Notes command.
   - It is the cleanest command-only migration and should become an `.obsidian.vimrc` normal-mode mapping to
     `daily-notes`.
   - Remove the corresponding `vim.defineAction` and `vim.mapCommand` from `bob-navigation-hotkeys` once the vimrc
     mapping is in place.

5. Migrate child-note `Ctrl+-` if CodeMirror Vim accepts the chord reliably.
   - The child-note command already exists as `bob-navigation-hotkeys:open-child-note`.
   - The current binding is a global Obsidian hotkey in `hotkeys.json`, so it can fire outside Vim normal mode.
   - Preferred target: `exmap bob_child_note obcommand bob-navigation-hotkeys:open-child-note` plus a normal-mode Vim
     mapping for `Ctrl+-`.
   - Because control-minus notation can be environment-sensitive, verify the exact CodeMirror Vim notation in live
     Obsidian. The likely notation is `<C-->`. If live testing shows the vimrc plugin cannot capture it reliably, keep
     the existing `hotkeys.json` binding and document the limitation instead of shipping a broken migration.

6. Migrate transclusion `!` by exposing it as an Obsidian editor command first.
   - The current `!` mapping calls a private Vim action with the raw CodeMirror editor object.
   - To move the mapping into `.obsidian.vimrc`, add a normal Obsidian `editorCallback` command such as
     `bob-navigation-hotkeys:toggle-line-transclusions`.
   - Reuse the existing pure transclusion helpers and editor helpers so the behavior remains the same: line-level
     toggle, cursor adjustment, notices, and no unrelated parsing expansion.
   - Then map `!` in `.obsidian.vimrc` through `obcommand`.

7. Do not migrate the ledger mappings in this pass.
   - `\\`, `\p`, `\P`, `\o`, and `\O` use current editor state, repeat counts, Pomodoro parsing, cursor placement, and
     deferred scroll centering.
   - They are not simple command-only dispatch yet.
   - Moving them would either require additional command wrappers and repeat plumbing or would risk losing behavior.

8. Do not enable vimrc JavaScript support.
   - The installed plugin has `supportJsCommands: false`.
   - Keep it false. All needed behavior should route through audited local plugin commands, not arbitrary vault
     JavaScript.

## Proposed `.obsidian.vimrc` Shape

Start with only task-relevant mappings:

```vim
" Bob command mappings managed by obsidian-vimrc-support.
" JavaScript vimrc commands intentionally remain disabled.

exmap bob_daily obcommand daily-notes
exmap bob_prev_link obcommand bob-navigation-hotkeys:open-prev-link
exmap bob_next_link obcommand bob-navigation-hotkeys:open-next-link
exmap bob_toggle_transclusions obcommand bob-navigation-hotkeys:toggle-line-transclusions
exmap bob_child_note obcommand bob-navigation-hotkeys:open-child-note

nmap - :bob_daily<CR>
nmap [[ :bob_prev_link<CR>
nmap ]] :bob_next_link<CR>
nmap ! :bob_toggle_transclusions<CR>
" Candidate pending live verification:
" nmap <C--> :bob_child_note<CR>
```

If live verification confirms the `Ctrl+-` syntax, uncomment/add the child-note mapping and remove the corresponding
`hotkeys.json` entry. If it does not, leave `hotkeys.json` unchanged for child-note and keep the commented note out of
the final file unless a comment is useful for future maintainers.

## Implementation Scope

Expected vault files to edit:

- `/home/bryan/bob/.obsidian.vimrc`
- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
- `/home/bryan/bob/.obsidian/hotkeys.json`, only if `Ctrl+-` is successfully migrated out of global Obsidian hotkeys.

No expected edits:

- `/home/bryan/bob/.obsidian/plugins/obsidian-vimrc-support/data.json`
- `/home/bryan/bob/.obsidian/community-plugins.json`
- `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`
- Daily notes, Bases files, Templater data, or unrelated vault content
- `bob-cli` Rust/Python/CLI code
- Memory files

## Implementation Steps

1. Re-check repository state.
   - Run `git status --short` in the `bob-cli` workspace.
   - Run `git -C /home/bryan/bob status --short`.
   - Confirm target files' starting diffs, especially `.obsidian/hotkeys.json`, because it is already dirty with
     unrelated app navigation additions and no trailing newline.

2. Add the Obsidian command wrapper for transclusion toggling.
   - In `bob-navigation-hotkeys/main.js`, add an `addCommand` entry with an `editorCallback`.
   - Reuse existing `toggleLineTransclusions`, cursor adjustment, and line replacement helpers.
   - Prefer adapting helpers so they work with Obsidian's `Editor` interface, since `obcommand` invokes
     `editorCallback(editor, view)` rather than passing the CodeMirror Vim `cm` object.

3. Create `.obsidian.vimrc`.
   - Add `exmap` wrappers for daily, previous link, next link, transclusion toggle, and child note.
   - Add `nmap` lines for `-`, `[[`, `]]`, and `!`.
   - Add the `Ctrl+-` mapping only after confirming the syntax is accepted in the installed vimrc plugin.

4. Remove redundant JavaScript Vim mappings from `bob-navigation-hotkeys`.
   - Remove `bobNavigationOpenDailyNote` action definition and `-` mapping.
   - Remove `bobNavigationOpenPrevLink` and `bobNavigationOpenNextLink` action definitions and their `[[`/`]]` mappings
     if the vimrc mappings are in place.
   - Remove the `bobNavigationToggleLineTransclusions` Vim action and `!` mapping after the command wrapper is mapped
     through vimrc.
   - Keep the `registerVimMappings()` retry flow only if other navigation Vim mappings remain. If none remain, remove
     that registration path cleanly.
   - Keep the actual Obsidian command methods and behavior unchanged.

5. Update `hotkeys.json` only for a successful child-note migration.
   - If `Ctrl+-` works in vimrc normal mode, remove `bob-navigation-hotkeys:open-child-note` from `hotkeys.json`.
   - Preserve all unrelated dirty additions in `hotkeys.json`, including app go-back/go-forward bindings.
   - Avoid broad formatting that rewrites unrelated JSON.
   - If `Ctrl+-` does not work in vimrc, leave `hotkeys.json` unchanged and report that child-note remains global for
     now.

6. Validate statically.
   - `node -c /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
   - `jq '.' /home/bryan/bob/.obsidian/hotkeys.json`
   - `jq '.' /home/bryan/bob/.obsidian/plugins/obsidian-vimrc-support/data.json`
   - `git -C /home/bryan/bob diff --check -- .obsidian.vimrc .obsidian/plugins/bob-navigation-hotkeys/main.js .obsidian/hotkeys.json`

7. Add focused automated checks where practical.
   - Use the existing exported helper pattern in `bob-navigation-hotkeys` to test the transclusion line toggle behavior
     if the wrapper touches helper code.
   - Stub the vimrc/Obsidian command path only enough to prove command IDs and mapping strings are present in
     `.obsidian.vimrc`.
   - Do not attempt to fully simulate Obsidian's plugin runtime in Node.

8. Manual Obsidian smoke test after reload.
   - Reload Obsidian or the affected plugins.
   - In Vim normal mode:
     - `-` opens today's daily note.
     - `[[` opens the previous Bob labeled body link.
     - `]]` opens the next Bob labeled body link.
     - `!` toggles transclusion markers on the current line.
     - `Ctrl+-` opens the child-note picker only if the migration was applied.
   - In Vim insert mode:
     - `-` inserts a literal hyphen.
     - `!` inserts or behaves as ordinary text input.
     - `Ctrl+-` does not open the child picker if it was removed from `hotkeys.json`.
   - Confirm `\\`, `\p`, `\P`, `\o`, and `\O` still work through `bob-ledger-tools`.

9. Final git hygiene and commit.
   - Re-check `git -C /home/bryan/bob status --short`.
   - Confirm the final vault diff is limited to the intended files.
   - Commit only the task-related vault files with the required `sase_git_commit` workflow before finishing after
     implementation edits.
   - Leave unrelated dirty and untracked vault files untouched.

## Risks And Mitigations

- Risk: `obsidian-vimrc-support` default mappings override Bob's `[[` and `]]`. Mitigation: explicitly map them in
  `.obsidian.vimrc` to Bob commands.

- Risk: `Ctrl+-` cannot be captured by CodeMirror Vim or uses a different notation than expected. Mitigation: live-test
  the chord before removing the global hotkey. If it is unreliable, keep the existing `hotkeys.json` binding and
  document the exception.

- Risk: `obcommand` command execution differs between callback and editorCallback commands. Mitigation: expose
  transclusion as an `editorCallback`, keep daily/link/child commands as existing callback commands, and manually
  smoke-test all mapped commands after plugin reload.

- Risk: removing all navigation Vim registration changes plugin initialization assumptions. Mitigation: keep the cleanup
  minimal and verify the remaining command registration, file tracking, and editor update listener still initialize.

- Risk: the vault's pre-existing dirty state obscures the task diff. Mitigation: inspect status and targeted diffs
  before and after each edit, and stage/commit only the files changed for this migration.

## Done Criteria

- `.obsidian.vimrc` exists and owns the migrated normal-mode command mappings.
- `bob-navigation-hotkeys` no longer registers redundant Vim mappings for the migrated keys.
- Transclusion `!` still behaves exactly as before through an Obsidian command wrapper.
- Daily `-`, Bob `[[`/`]]`, and any successfully migrated child-note mapping work only in Vim normal mode.
- Ledger mappings remain unchanged and still work.
- Static validation passes.
- The final committed vault diff is limited to the task-related files, with unrelated synced/user changes preserved.
