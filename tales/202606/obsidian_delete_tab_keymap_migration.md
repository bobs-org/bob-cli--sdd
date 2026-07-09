---
create_time: 2026-06-19 07:07:50
status: wip
prompt: sdd/prompts/202606/obsidian_delete_tab_keymap_migration.md
---
# Plan: Shorten Obsidian Close-Tab Vim Keymaps

## Problem

The current Obsidian Vim normal-mode close-tab mappings work around the original `d`-operator shadowing bug by using
backslash-prefixed chords:

```vim
nmap \d< :bob_close_tabs_left<CR>
nmap \d> :bob_close_tabs_right<CR>
nmap \do :bob_close_other_tabs<CR>
```

Bryan wants a shorter mnemonic set:

| Action           | Current live LHS | Requested target LHS |
| ---------------- | ---------------- | -------------------- |
| Close other tabs | `\do`            | `\\`                 |
| Close tabs left  | `\d<`            | `\<`                 |
| Close tabs right | `\d>`            | `\>`                 |

Note: the prompt mentions migrating `\dD`, but the live vault no longer contains `\dD`; the prior approved fix changed
the close-other-tabs mapping from `dD` to `\do`. This plan treats the requested first target, `\\`, as applying to the
existing close-other-tabs action.

## Evidence

- `~/bob` is the live Obsidian vault.
- `obsidian_vimrc.md` is currently clean and contains only the three `\d*` close-tab mappings above.
- The vault has unrelated dirty files; those must stay untouched and unstaged.
- `obsidian-vimrc-support` loads each non-comment vimrc line through `CodeMirror.Vim.handleEx(...)` and records mapping
  LHS strings verbatim for chord display.
- The bundled Obsidian CodeMirror Vim source parses mapping args by splitting on whitespace only, then stores
  `mapping.keys = lhs` verbatim. It does not treat backslash as an escape while parsing `nmap`.
- CodeMirror Vim command matching is string equality/prefix matching. `\` has no built-in normal-mode command, so a `\`
  prefix still avoids the original `d`-operator shadowing. Built-in `<` and `>` operators do not conflict after the
  first `\`, because the pressed sequence becomes `\<` or `\>`, not plain `<` or plain `>`.

## Proposed Change

Edit only `/home/bryan/bob/obsidian_vimrc.md`:

```diff
-nmap \d< :bob_close_tabs_left<CR>
-nmap \d> :bob_close_tabs_right<CR>
-nmap \do :bob_close_other_tabs<CR>
+nmap \< :bob_close_tabs_left<CR>
+nmap \> :bob_close_tabs_right<CR>
+nmap \\ :bob_close_other_tabs<CR>
```

No changes to:

- the three `exmap bob_close_*` wrappers;
- `.obsidian/plugins/bob-navigation-hotkeys/main.js`;
- `.obsidian/hotkeys.json`;
- plugin manifests or settings;
- memory files, notes, or unrelated dirty vault files.

## Implementation Steps

1. Re-check `/home/bryan/bob` status and confirm `obsidian_vimrc.md` is clean before editing.
2. Re-read the three current mapping lines immediately before applying the edit.
3. Update only the three `nmap` left-hand sides shown above.
4. Validate statically:
   - `git -C /home/bryan/bob diff -- obsidian_vimrc.md` shows only the three LHS changes;
   - `git -C /home/bryan/bob diff --check -- obsidian_vimrc.md`;
   - grep confirms no remaining close-tab mapping uses `\d<`, `\d>`, `\do`, or `\dD`.
5. Manual Obsidian smoke test after reloading/sourcing the vimrc:
   - command palette still runs close-left, close-right, and close-other-tabs correctly;
   - `\<` closes only tabs to the left;
   - `\>` closes only tabs to the right;
   - `\\` closes all sibling tabs except the active tab;
   - boundary cases no-op cleanly;
   - native Vim `d`, `dw`, `dd`, `D`, `<`, `>`, `<<`, and `>>` behavior remains intact.
6. If implementation is approved after this plan, commit only `obsidian_vimrc.md` through the SASE git commit workflow,
   leaving all unrelated dirty/untracked vault files untouched.

## Risks

- `\\` is visually easy to misread in Markdown/vimrc diffs. Mitigation: validate the exact source line and manually test
  the chord in Obsidian.
- `\` becomes a prefix for three two-key chords, so pressing a lone `\` in normal mode will continue to wait for another
  key instead of doing anything by itself. This is already true with the current `\d*` mappings.
- Headless validation cannot prove the Obsidian UI reload picked up the new mappings. Manual reload/smoke testing
  remains required.

## Done Criteria

- `obsidian_vimrc.md` maps close-left to `\<`, close-right to `\>`, and close-other-tabs to `\\`.
- Static diff validation passes and only the three intended LHS values changed.
- Manual Obsidian smoke testing confirms the three chords and native Vim operators behave as expected.
- Any final commit contains only the `obsidian_vimrc.md` change.
