---
create_time: 2026-06-02 23:12:10
status: done
prompt: sdd/prompts/202606/pomodoro_jump_center_fix.md
---
# Fix `\\` Pomodoro Jump `zz`-Style Centering

## Goal

When pressing the `\\` Vim normal-mode keymap in my Obsidian vault, the editor should jump to the current Pomodoro line
**and redraw the viewport so that line sits at the vertical center** — i.e. emulate Vim's `zz`. Today the jump moves the
cursor to the right line, but the screen does **not** recenter on it (the line ends up parked at the top/bottom edge,
wherever the cursor happened to scroll into view). This plan diagnoses the root cause and fixes it so the line lands
centered.

## Context Reviewed

- Read project short memory (`memory/short/sase.md`): SASE runs from ephemeral `bob-cli_<N>` workspace clones; be
  careful not to run build/test commands outside the workspace's isolated venv. No sibling repos configured.
- Read Obsidian long memory via the audited command (`sase memory read long/obsidian.md --reason ...`): `~/bob/` is the
  Obsidian vault, driven headlessly through the `ob` command for Sync.
- The `\\` keymap is **not** in `bob-navigation-hotkeys`; it lives in the vault plugin
  `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`. `hotkeys.json` only binds `Ctrl-\` (alternate file) —
  the bare `\\` is a Vim mapping registered by the plugin, not an Obsidian hotkey.
- The mapping is registered in `registerVimMappings()`:
  `vim.mapCommand("\\\\", "action", "bobLedgerJumpToCurrentPomodoro", {}, { context: "normal" })`, whose action calls
  `jumpToCurrentPomodoro(cm)`.
- The centering was added in vault commit `5e60f6a "feat: center pomodoro jump in editor"`. Before that the jump used
  `setEditorCursor(cm, line, 0)` (plain CM5 `scrollIntoView`, i.e. "nearest"). The commit switched to: set cursor with
  `{ scroll: false }`, then dispatch a CodeMirror 6 `EditorView.scrollIntoView(pos, { y: "center" })` effect on the live
  `EditorView`, with a fallback to the old CM5 scroll.
- There is no automated test for this plugin. Validation to date is `node -c main.js`, `jq` on the manifest, and ad-hoc
  Node helper assertions with stubbed `obsidian` / `@codemirror/*` modules. `centerEditorViewOnPosition` and
  `editorViewPositionFromLineCh` are already exported on `module.exports.helpers`.

## Root Cause

The centering logic itself is correct in isolation, but it is **dispatched in the wrong place in the event lifecycle, so
a later scroll overrides it.**

`jumpToCurrentPomodoro(cm)` runs _synchronously inside the codemirror-vim command cycle_ (the action fired by the `\\`
mapping). Within that single cycle it does two things, in order:

1. `setEditorCursor(cm, target.line, 0, { scroll: false })` — moves the Vim/CM cursor to the Pomodoro line.
2. `centerEditorViewOnPosition(getActiveEditorView(this.app), target.line, 0)` — dispatches a CM6
   `scrollIntoView(..., { y: "center" })` effect.

The problem: **codemirror-vim issues its own "keep the cursor visible" scroll as it finalizes the keystroke, and that
scroll happens _after_ our center effect.** Vim's post-command cursor-visibility scroll uses "nearest" alignment (just
bring the cursor onto screen), not "center". Because it is the _last_ scroll dispatched in the cycle, it wins: the
viewport settles with the line merely visible at an edge, discarding our centering. Net symptom = exactly what's
observed: cursor on the right line, screen not centered.

This is why the bug slipped through: the exported helper `centerEditorViewOnPosition` does dispatch a valid center
effect (any unit test against a fake `EditorView` passes), but in the live Vim cycle its effect is immediately clobbered
by Vim's trailing nearest-scroll. The defect is timing/ordering, not the center math.

Secondary hypothesis to rule out during implementation (cheap to verify, changes the fix if true): if
`EditorView.scrollIntoView` is not actually a function in Obsidian's bundled CM6 (so `centerEditorViewOnPosition`
returns `false` and we fall into the CM5 `scrollEditorIntoView` fallback), then centering never even runs and we always
get "nearest". The implementation step will confirm which path executes before finalizing.

## Fix

Move the centering scroll **out of the synchronous Vim command cycle so it is the last scroll to run**, then let it
center. Concretely, in `jumpToCurrentPomodoro`:

1. Keep moving the cursor with `cm.setCursor(...)` (so Vim's own cursor state stays authoritative and consistent — don't
   bypass the adapter by writing the selection straight to the `EditorView`).
2. Defer the `centerEditorViewOnPosition(...)` call to **after** the current Vim cycle completes, via
   `window.requestAnimationFrame(...)` (fallback `setTimeout(fn, 0)` where rAF is unavailable). Re-resolve the active
   `EditorView` inside the deferred callback and dispatch the CM6 center effect there. By that point Vim's trailing
   nearest-scroll has already run, so our centered scroll is the final word and the line lands centered.
3. Preserve the existing fallback chain: if the deferred CM6 center can't run (no `EditorView`, or
   `EditorView.scrollIntoView` is missing), fall back to `scrollEditorIntoView(cm, line, 0)` so the line is at least
   brought into view as it is today.

Design notes / guardrails:

- The position fed to the center effect is recomputed from `target.line` inside the deferred callback (not a stale
  closed-over position) so it stays valid if the document/layout shifted between frames.
- Guard the deferred callback against the plugin being unloaded or the active view having changed (re-fetch the active
  `EditorView`; bail quietly if it's gone). Register any timer/rAF so it is cleaned up on `onunload` if the plugin
  lifecycle makes that practical.
- This is the minimal, lowest-risk change: it keeps the existing helpers and fallback, and only changes _when_ the
  center effect is dispatched. No change to the `\p` / `\P` / `\o` / `\O` actions, which don't center.

If implementation inspection shows the secondary hypothesis is the real cause (CM6 `scrollIntoView` unavailable), the
fix instead becomes: drive the centering through a mechanism Obsidian's bundled editor actually honors (e.g. the
CM5-compat `scrollIntoView` with an explicit centered margin, or the editor's own center API) — still deferred past the
Vim cycle. The deferral is required in either case.

## Verification Plan

Static / structural checks (safe to run in the workspace):

```bash
node -c /home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js
jq '.' /home/bryan/bob/.obsidian/plugins/bob-ledger-tools/manifest.json
```

Focused Node helper assertions (stub `obsidian`, `@codemirror/state`, `@codemirror/view`):

- `editorViewPositionFromLineCh` still maps `(line, ch)` to the correct document offset (clamping out-of-range
  lines/cols) — unchanged behavior.
- `centerEditorViewOnPosition` still dispatches an `EditorView.scrollIntoView(pos, { y: "center" })` effect when given a
  fake `EditorView`, and returns `false` (no throw) when `scrollIntoView` is absent or `dispatch` is missing — confirms
  the fallback contract.
- If `jumpToCurrentPomodoro` is refactored to expose the deferred scheduling, assert (with a stubbed
  `requestAnimationFrame`/`setTimeout`) that the center call is scheduled _after_ the cursor is set, and that the CM5
  fallback fires only when the CM6 path is unavailable.

Manual confirmation in the live vault (the real acceptance test, since the bug is runtime-only):

- Open a daily note with a Pomodoros section, scroll so the current Pomodoro line is well off-center (near top or bottom
  edge), press `\\` in normal mode, and confirm the line redraws to the vertical center like `zz`.
- Repeat with the current Pomodoro both above and below the viewport to confirm centering in both scroll directions, and
  with the file already centered (no-op should stay centered, not jump).

## Finalization

- Re-check `git status` in both the `bob-cli` workspace and the `~/bob` vault before finishing.
- The vault has unrelated pre-existing dirty notes; touch only `bob-ledger-tools/main.js` (clean today) and commit
  **only** that task-related vault file via the required `/sase_git_commit` workflow, leaving unrelated dirty notes
  untouched.
- Report any skipped validation, remaining dirty files, and whether the `bob-cli` repo (SDD prompt/tale) changes were
  committed or left per the finalizer/user instructions.

## Risks

- **Wrong root cause (the secondary hypothesis).** Mitigation: the implementation step first confirms which scroll path
  actually executes in the live editor (CM6 center vs. CM5 fallback) before locking in the fix; the deferral is needed
  either way.
- **Deferred scroll firing after unload / view switch.** Mitigation: re-fetch the active `EditorView` inside the
  deferred callback, bail quietly if absent, and clean up the timer/rAF on `onunload`.
- **rAF/timer changing perceived responsiveness.** A one-frame defer is imperceptible and is the price of out-ordering
  Vim's trailing scroll; acceptable for a manual navigation command.
- **No automated coverage for live scroll behavior.** Mitigation: keep/extend the exported-helper unit checks and rely
  on the documented manual acceptance test; the change is deliberately narrow (only _when_ the existing center effect is
  dispatched).
