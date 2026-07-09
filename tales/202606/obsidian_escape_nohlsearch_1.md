---
title: Clear Obsidian Vim Search Highlight on Normal-Mode Escape
status: proposed
create_time: 2026-06-22 10:02:15
prompt: sdd/prompts/202606/obsidian_escape_nohlsearch_1.md
---

# Plan: Clear Obsidian Vim Search Highlight on Normal-Mode Escape

## Goal

Make a second `<Esc>` press in Obsidian Vim mode clear any `/` search highlight. The first `<Esc>` from insert mode
should still leave insert mode. Once already in Vim normal mode, pressing `<Esc>` should run the Vim `:nohlsearch`
behavior: remove current search highlighting without disabling highlighting for the next search.

## Context Reviewed

- Obsidian long-term memory was read through the audited `sase memory read obsidian.md` workflow.
- `bob-cli` project memory says Bob Obsidian plugin source lives in the linked `bob-plugins` repo and should be deployed
  with `bob plugins sync`; plugin files should not be edited directly in the vault.
- The linked `bob-plugins` repo has existing Vim integration in `bob-vim-surround`, `bob-navigation-hotkeys`,
  `bob-ledger-tools`, and `task-status-cycler`.
- The active Vimrc Support config in the vault points at `obsidian_vimrc.md`, not `.obsidian.vimrc`, so the normal
  syncable Markdown vimrc is the intended place for declarative Vim keymaps.
- `~/bob/obsidian_vimrc.md` is tracked and currently clean.
- The installed Vimrc Support plugin sends vimrc lines through CodeMirror Vim's Ex handler and supports `nmap`.
- Upstream `replit/codemirror-vim` defines `:nohlsearch` / `:noh`, and that command clears the search overlay and
  scrollbar annotations via CodeMirror Vim's search state.
- The vault has its own AGENTS.md rule: inspect status before editing; after making changes under `~/bob`, stage and
  commit only the task-related files with the SASE git commit workflow.

## Primary Approach

Use the active Obsidian vimrc file:

```vim
nmap <Esc> :nohlsearch<CR>
```

This is the smallest correct change because:

- it uses CodeMirror Vim's public Ex command path rather than private search overlay internals;
- `nohlsearch` clears current highlights without turning future search highlighting off;
- `nmap` scopes the mapping to normal mode, so insert-mode `<Esc>` should still be handled by Vim as "leave insert";
- CodeMirror Vim has a separate `omap` context for operator-pending mappings, so the normal-mode mapping should not own
  operator-pending Escape;
- `bob-vim-surround` already captures `<Esc>` while a `cs`/`ds` surround operation is pending, so its cancel behavior
  should remain intact.

Place the mapping near the top of `obsidian_vimrc.md`, after the clipboard setting and before the Bob command `exmap`
block, so it reads as a general Vim behavior rather than a Bob command dispatch mapping.

## Fallback If Vimrc Escape Mapping Fails

If live testing shows Vimrc Support or CodeMirror Vim cannot reliably bind `<Esc>` in normal mode, do not force a
brittle vimrc workaround. Instead, implement a focused plugin fallback in `bob-navigation-hotkeys` in the linked
`bob-plugins` repo:

1. Add a high-priority `Escape` editor keymap or capture-phase keydown handler.
2. Return `false` unless the active editor is a Markdown editor in Vim normal mode.
3. In normal mode, resolve the CodeMirror Vim adapter and invoke CodeMirror Vim's Ex command path for `nohlsearch`
   (prefer `vim.handleEx(cm, "nohlsearch")` if available; otherwise use the exposed ex dispatcher path if present).
4. Return `true` only after clearing highlights, so insert-mode Escape, search-prompt Escape, visual/replace mode, and
   non-editor UI Escape keep their existing behavior.
5. Deploy through `bob plugins sync` rather than editing vault plugin files directly.

This fallback should only be used if the one-line vimrc mapping is proven insufficient.

## Implementation Steps

1. Re-check state immediately before editing:
   - `git status --short` in `bob-cli`;
   - `git status --short` in `bob-plugins`;
   - `git -C ~/bob status --short -- obsidian_vimrc.md .obsidian/plugins/obsidian-vimrc-support/data.json`.
2. Edit only `~/bob/obsidian_vimrc.md` for the primary approach.
3. Add `nmap <Esc> :nohlsearch<CR>` near the general Vim settings.
4. Load the mapping in Obsidian by either running `:source obsidian_vimrc.md` from Vim command mode or
   reloading/toggling Vimrc Support.
5. Verify the behavior manually in desktop Obsidian:
   - `/term<CR>` highlights matches; pressing `<Esc>` in normal mode clears them.
   - From insert mode, the first `<Esc>` exits insert mode; a second `<Esc>` clears the highlight.
   - Starting another `/` search still highlights matches, proving highlighting was not disabled.
   - Pressing `<Esc>` with no active search highlight is harmless.
   - Existing mappings in `obsidian_vimrc.md` still work, especially `-`, `[[`, `]]`, `!`, `<C-j>`, and `<C-k>`.
   - Pending surround cancel still works for `cs<Esc>` and `ds<Esc>`.
6. Inspect the final diff and commit only `obsidian_vimrc.md` using the SASE git commit workflow required by the vault
   instructions.

## Out of Scope

- No `bob-cli` Rust changes.
- No changes to memory files.
- No changes to Vimrc Support settings or enabling JavaScript vimrc commands.
- No plugin changes unless the vimrc mapping fails in live testing.
