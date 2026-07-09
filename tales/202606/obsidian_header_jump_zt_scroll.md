---
create_time: 2026-06-12 07:55:09
status: done
prompt: sdd/prompts/202606/obsidian_header_jump_zt_scroll.md
---
# Plan: Scroll Jumped-To Section Header to Top of Viewport (vim `zt` behavior)

## Context

Bryan's Obsidian vault (`~/bob`) already has working `<Ctrl+J>` / `<Ctrl+K>` keymaps that jump to the next/previous
markdown section header (built per `sdd/tales/202606/obsidian_ctrl_jk_header_navigation.md`). Both keymaps — the vim
normal-mode `nmap`s in `~/bob/obsidian_vimrc.md` and the insert-mode/non-vim bindings in `~/bob/.obsidian/hotkeys.json`
— resolve to the same two editor commands (`jump-to-next-section-header` / `jump-to-prev-section-header`) registered by
the local plugin `~/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`.

Relevant facts from the current implementation:

- `jumpToSectionHeader(editor, direction)` (main.js:2879) computes the target header line and moves the cursor via the
  shared helper `setEditorCursor` (main.js:1125).
- `setEditorCursor` calls Obsidian's `editor.scrollIntoView({ from, to }, true)` — the `true` flag **centers** the
  cursor line in the viewport. Obsidian's `Editor.scrollIntoView` API only offers "nearest" or "center"; it has no "top"
  mode, so the `zt` behavior needs the underlying CodeMirror 6 view.
- The plugin already imports `EditorView` from `@codemirror/view` (main.js:3) and already reaches the CM6 view through
  `editor.cm` elsewhere (main.js:3609). CM6's `EditorView.scrollIntoView(offset, { y: "start" })` effect is the
  canonical way to scroll a position to the top of the viewport — exactly what vim's `zt` does.
- `setEditorCursor` is shared with the cursor-position-restore feature (main.js:3684), so its centering behavior must
  not change globally; the `zt` scroll must be scoped to the header-jump command.
- Pure/editor helpers are exported via `module.exports.helpers` for ad-hoc Node tests with mocked `obsidian` and
  `@codemirror/view` modules (the established validation pattern for this plugin).
- The vault is synced by Obsidian Sync and currently has unrelated uncommitted changes (`_templates/daily.md`, a daily
  note, a chat ref note). Per `~/bob/AGENTS.md`, only the file changed for this task may be staged/committed, via
  `/sase_git_commit`.

## Goal

After `<Ctrl+J>` / `<Ctrl+K>` jumps the cursor to a section header, redraw the editor with that header line at the
**top** of the viewport — the same visual result as pressing `zt` in vim — instead of today's centered scroll. This must
apply to both invocation paths (vim normal-mode mappings and hotkeys.json bindings), since both call the same command.

## Behavior Specification

1. On a successful jump, the target header line becomes the first visible line of the editor viewport (a few pixels of
   margin, CM6's default `yMargin`, keeps the line from being clipped by the pane edge).
2. Near the end of the file, where there is not enough content below the header to fill the viewport, the editor scrolls
   as far down as it can (CM6 does not scroll past the end) — same caveat as `zt` in editors without scroll-past-end.
3. Failed jumps are unchanged: no cursor movement, no scrolling, existing `No next/previous section header` Notice.
4. Graceful degradation: if the CM6 view is unavailable (e.g. `editor.cm` missing in some future Obsidian build), the
   jump still works and falls back to the current centered scroll from `setEditorCursor` — never a broken jump.
5. All other plugin commands that use `setEditorCursor` (e.g. cursor position restore) keep their current centering
   behavior.

## Implementation

Single file change: `~/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`.

1. Add a defensive editor helper `scrollEditorLineToTop(editor, line)` next to the other editor helpers:
   - Resolve `cm = editor.cm`; return `false` unless `cm.dispatch`, `cm.state.doc.line`, and `EditorView.scrollIntoView`
     are all available (mirrors the plugin's existing feature-detection style around `EditorView`, main.js:2696).
   - Compute the document offset of the line start (`cm.state.doc.line(line + 1).from` — CM6 lines are 1-based) and
     dispatch `EditorView.scrollIntoView(offset, { y: "start" })`; wrap in `try/catch` returning `false` on error.
   - Return `true` on success. Export it via `module.exports.helpers` for testability.

2. In `jumpToSectionHeader`, after the existing successful `setEditorCursor` call, invoke
   `scrollEditorLineToTop(editor, targetLine)`. Sequencing note: `setEditorCursor`'s centered scroll dispatches first
   and the `y: "start"` effect dispatches second, so the top-align wins; if the helper returns `false`, the centered
   scroll simply remains in effect (spec item 4). The helper's return value is intentionally not treated as a jump
   failure.

No changes to `obsidian_vimrc.md`, `hotkeys.json`, or the plugin manifest — the keymaps and command registrations are
untouched; only the command's scroll behavior changes.

## Validation

1. `node --check /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`.
2. Ad-hoc Node test (temp dir with stub `obsidian` and `@codemirror/view` modules, per the established pattern)
   exercising `helpers.scrollEditorLineToTop`:
   - Dispatches one effect built by the mocked `EditorView.scrollIntoView` with the offset of the requested line's start
     and `{ y: "start" }`, and returns `true`, when given a mock `editor.cm` that records `dispatch` calls.
   - Returns `false` (and does not throw) when `editor` is null, `editor.cm` is missing, `cm.dispatch` is missing, or
     `cm.state.doc.line` throws (out-of-range line).
   - Also re-run a quick regression of `getSectionHeaderJumpLine` next/prev picks to confirm helper exports still load.
3. `git -C /home/bryan/bob status` / diff review: confirm only the plugin `main.js` changed and the pre-existing synced
   changes are untouched.
4. Commit only `main.js` via `/sase_git_commit`.

## Manual Smoke Test

After reloading Obsidian (or toggling the `bob-navigation-hotkeys` plugin):

1. In a long note, press `<Ctrl+J>` from a body paragraph in vim normal mode: the cursor lands on the next header and
   that header is redrawn at the top of the viewport (not centered).
2. Press `<Ctrl+K>`: previous header, also redrawn at the top.
3. Repeat both in insert mode (hotkeys.json path) — same top-aligned result.
4. Jump to the last header of a note whose tail is shorter than the viewport: editor scrolls to its bottom limit, no
   error.
5. Trigger the no-target case (`<Ctrl+K>` above the first header): Notice appears, no scroll jump.
