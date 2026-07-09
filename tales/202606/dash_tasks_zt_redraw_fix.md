---
create_time: 2026-06-12 13:05:07
status: wip
prompt: sdd/prompts/202606/dash_tasks_zt_redraw_fix.md
---
# Plan: Fix `\|` Dash Tasks Jump — `## Tasks` Not Redrawn at Top of Viewport

## Context

The new `\|` vim keymap (commit `d5338b2`, vault `~/bob`) focuses `dash.md` and moves the cursor to the `## Tasks` line,
but the `zt` redraw — the line landing at the **top** of the viewport — is not working. The `<C-j>`/`<C-k>`
section-header jumps top-align correctly, and Bryan asked that we study how they handle the redraw to find the root
cause.

All code involved lives in the vault, not the bob-cli repo:

- `~/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js` — `openDashTasks` (main.js:3375), `jumpOrDeferDashTasks`
  (main.js:3461), `jumpToActiveDashTasks` (main.js:3481), `activateWorkspaceLeaf` (main.js:3429), `jumpToSectionHeader`
  (main.js:3346, the working `<C-j>/<C-k>` path), `setEditorCursor` (main.js:1534), `scrollEditorLineToTop`
  (main.js:1560).
- `~/bob/.obsidian/plugins/bob-ledger-tools/main.js` — the proven "jump after a file open / vim keystroke" machinery for
  the `\\` pomodoro jump.
- `~/bob/obsidian_vimrc.md` — mappings; both `<C-j>/<C-k>` and `\|` route identically through `exmap … obcommand` +
  `nmap`, and obsidian-vimrc's `obcommand` executes the command callback synchronously
  (obsidian-vimrc-support/main.js:902-931). The mapping itself is fine and needs no change.

## Root Cause

The jump _sequence_ (`setEditorCursor` then `scrollEditorLineToTop`) is byte-for-byte the same as the working
`<C-j>/<C-k>` path. What differs is **when it runs**. CM6 keeps a single pending scroll target: the last
`scrollIntoView` dispatched before the next measure/layout cycle wins. `<C-j>/<C-k>` operate on a settled,
already-active editor with no pending file-open machinery, so their `y: "start"` dispatch is the final scroll and it
sticks. The dash command runs in a hostile window:

1. **Open path race (primary bug).** `openDashTasks` dispatches the `zt` scroll synchronously, immediately after
   `await getLeaf(false).openFile(file)` resolves (main.js:3397-3404). Obsidian's markdown view applies its remembered
   scroll state and finishes live-preview layout _asynchronously after_ that moment, so Obsidian's scroll lands last and
   clobbers the top-align. This exact clobbering is documented in this vault by bob-ledger-tools:
   codemirror-vim/Obsidian issue trailing scrolls as a keystroke/file-open settles, so ledger sets the cursor with
   `{scroll: false}` and defers its centering scroll past the synchronous turn so it is "the last word — never
   clobbered" (`jumpToPomodoroTarget` ledger main.js:1599-1612, `scheduleCenterOnLine` ledger main.js:1641-1678,
   `deferToNextFrame` comment ledger main.js:1432-1434). The dash daily-note analog (`\\` fallback) additionally _waits_
   for the opened view (10×50ms polls) before jumping.

2. **Retry machinery guards the wrong thing.** `jumpOrDeferDashTasks` retries (8 frames) only while the _jump_ fails —
   i.e. while no active dash editor exists. The moment one cursor-set succeeds it stops. A jump that succeeds but whose
   scroll is stomped one frame later is never re-asserted, so the retry helper cannot save the `zt`.

3. **Reveal path never activates (secondary bug, same feature).** When dash is open in another tab,
   `activateWorkspaceLeaf` returns `true` right after `workspace.revealLeaf(leaf)` and never reaches the
   `setActiveLeaf(leaf, {focus: true})` fallback (main.js:3435-3442). Per the Obsidian API, `revealLeaf` brings a leaf
   to the foreground but does **not** make it the active/focused leaf. `jumpToActiveDashTasks` requires the _active_
   markdown view to be dash, so every retry fails and the command dies with a "No active markdown editor" Notice — no
   jump, no scroll. (bob-ledger-tools sidesteps this by waiting on `leaf.view` directly rather than the active view.)

## Fix

One file changes: `~/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`. The vimrc is untouched. The `<C-j>/<C-k>`
path (`jumpToSectionHeader`) is untouched.

### 1. Activate, don't just reveal

In `activateWorkspaceLeaf`, after a successful `revealLeaf(leaf)`, also call `setActiveLeaf(leaf, {focus: true})`
(keeping the existing try/catch fallback chain and the no-`revealLeaf` branch). This makes the reveal path actually
produce an active dash view for the jump machinery.

### 2. Make the `zt` scroll the last word

Keep the immediate cursor-set + top-scroll in `jumpToActiveDashTasks` (the dash-already-active case stays identical to
the proven `<C-j>/<C-k>` behavior, and the user sees no added latency). Then, when the cursor placement succeeded and
`scrollEditorLineToTop` is viable, schedule a **bounded scroll re-assertion** so the top-align outlasts Obsidian's
deferred scroll restore:

- New constant `DASH_TASKS_SCROLL_ASSERT_FRAMES = 8` (matches the existing 8-frame retry budget, ~130ms).
- A `scheduleDashTasksScrollAssert(targetLine)` method chains `deferToNextFrame` for up to N frames. Each frame it
  checks the active markdown view is still `dash.md`; if not, it stops (user navigated away). Otherwise it re-places the
  cursor on `targetLine` if something (e.g. Obsidian's restore) moved it, and re-dispatches `scrollEditorLineToTop`. The
  final frame's dispatch is the last scroll issued, mirroring ledger's "last word" doctrine.
- Track the handle in `pendingDashTasksScrollDeferred`; cancel it in `cancelPendingDashTasksJump` (so each new `\|`
  press resets cleanly) — which `onunload` already calls (main.js:3174).
- The "No `## Tasks` header" Notice path schedules nothing (no repeat Notices). If CM6 is unavailable
  (`scrollEditorLineToTop` returns false), schedule nothing — `setEditorCursor`'s centered scroll remains the
  graceful-degradation contract from the original plan.

## Validation

1. `node --check /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`.
2. Ad-hoc Node tests (established stub pattern: temp dir, stub `obsidian` + `@codemirror/view`, plus a fake
   `window.requestAnimationFrame` queue we drain manually):
   - re-assert scheduler dispatches the top-scroll on each drained frame while the active view is dash and stops at the
     frame budget;
   - re-assert scheduler stops early when the active view's file changes;
   - cursor is re-placed when a frame finds it moved off the target line;
   - regression: existing exported helpers (`getDashTasksHeaderLine`, `scrollEditorLineToTop`) still load and pass their
     prior checks. (Requires exporting the new method or a thin testable wrapper via `module.exports.helpers`,
     consistent with the existing export list at main.js:5150+.)
3. Re-read the diff: only `main.js` modified; `git -C /home/bryan/bob status --short` before/after shows the
   pre-existing unrelated dirty files (including `dash.md`, which must never be staged) untouched.
4. Commit only `main.js` via `/sase_git_commit`.

## Manual Smoke Test (after reloading the plugin in Obsidian)

1. From a non-dash note with dash closed everywhere: `\|` opens dash, cursor on `## Tasks`, line redrawn at the **top**
   (not centered, not at the remembered scroll position).
2. With dash open in another tab: `\|` switches to that tab (no duplicate), focuses it, same jump + top-align — and no
   "No active markdown editor" Notice.
3. Already in dash, scrolled to the bottom: `\|` snaps `## Tasks` back to the top.
4. Regressions: `<C-j>`/`<C-k>` still top-align; `\\`/`\p` ledger maps unaffected; cursor-restore/alternate-file
   behavior unchanged.

## Risks

- **8 frames may not outlast a slow restore** (large file / slow machine). dash.md is small, so ~130ms should cover it;
  if the smoke test still shows clobbering, the documented escalation is ledger's wait-then-jump approach (50ms-poll for
  the settled view before the final scroll) or a larger frame budget — a one-constant change.
- **Re-asserting the cursor could fight immediate user input** inside the ~130ms window. Mitigated by the
  stop-when-not-dash guard and the tiny window; ledger's deferred-scroll precedent has not produced complaints.
- **`setActiveLeaf` semantics**: already used as the fallback today and by ledger with `{focus: true}`; calling it after
  `revealLeaf` is additive and matches the original plan's stated intent ("activate via revealLeaf … with setActiveLeaf
  fallback").
