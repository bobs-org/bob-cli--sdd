---
create_time: 2026-07-10 10:49:29
status: done
prompt: .sase/sdd/prompts/202607/dash_restore_cursor_reveal_fix.md
---
# Plan: Fix `dash.md` restore landing on `## Projects` — cursor-reveal stomps the query-anchored scroll restore

## Problem / product context

Commit `ff33e83` (bob-plugins) re-introduced the `dashLocation` remember/restore machinery so that `<Ctrl+0>`
(`open-dash-tasks` in `bob-navigation-hotkeys`) restores the dashboard's scroll position when `dash.md` has to be
re-opened fresh (the "clicked a link → same leaf navigated away → came back" flow).

**It does not work.** Reported repro: scroll to the middle of the READY Tasks query results, click a task link to
navigate away, press `<Ctrl+0>` → the view **always** lands with the cursor on the `## Projects` section header (the
header immediately below the READY Tasks section), regardless of where in the READY results the user was.

## Root cause diagnosis

All line references are `plugins/bob-plugins`-repo `plugins/bob-navigation-hotkeys/main.js` at `master` tip `ff33e83`.

`dash.md` structure (source line numbers, 1-indexed): `## Tasks` (21), `### WIP Tasks` + `tasks` block (23–27),
`### NEXT Tasks` + block (29–33), `### READY Tasks` + block (35–39), `## Projects ([[projects.base]])` (41). So the
first selectable source position **after** the READY query widget is the blank line 40 / `## Projects` line 41.

### Primary cause — a poisoned cursor capture plus a _revealing_ cursor restore

Two facts combine deterministically:

1. **Clicking a link inside the rendered READY block moves the cursor to the `## Projects` line.** In live preview the
   whole `tasks` fenced block is replaced by one atomic CodeMirror block widget. A mousedown inside the widget cannot
   place the selection _inside_ the replaced range, so CM maps the click to the nearest valid boundary — for clicks in
   the body of the tall READY widget, the position just **after** it (line 40/41, visually the `## Projects` header).
   That selection change fires `trackSelectionUpdate` (`update.selectionSet`, main.js:10512) _before_ the navigation,
   which calls `captureDashLocationFromView(view, { position })` (main.js:10539) and overwrites
   `dashLocation.sourcePosition` with the Projects-header position. The scroll/query snapshot parts of the capture
   remain correct — only the cursor is poisoned.

2. **The restore path _reveals_ that cursor with a centered scroll, asynchronously, after the scroll writes.**
   `restoreActiveDashLocation` (main.js:9162) first calls `setEditorCursor` (main.js:9189), and `setEditorCursor`
   (main.js:4132) doesn't just set the cursor — it also calls `editor.scrollIntoView({ from, to }, true)` (main.js:4145,
   `center=true`). Obsidian implements that as a CM6 scroll _effect_, which CM applies in its next **measure cycle —
   i.e. asynchronously, after** the synchronous `scrollDOM.scrollTop` writes that follow in the same function (raw
   scroll at main.js:9215, query-anchored scroll at main.js:9229). The centered reveal of the Projects line therefore
   always wins. Worse, the cursor is re-set on **every** retry frame (up to `DASH_LOCATION_RESTORE_RETRIES = 12`), so
   even when the query-anchored scroll succeeds on a later frame, that frame still ends with another scheduled centered
   reveal.

Net effect: the view always ends centered on `## Projects` with the cursor on it — exactly the reported symptom, and
deterministic because every click anywhere in the READY widget maps to the same post-widget position.

(Contrast: the `## Tasks` jump path gets away with the revealing `setEditorCursor` because it immediately follows it
with a `scrollEditorLineToTop` **dispatch** for the same line (main.js:8961) — a later CM scroll effect supersedes the
reveal — and then re-asserts for 8 frames.)

### Secondary defects (would still degrade restore fidelity after the primary fix)

- **S1 — DOM-index anchor is unstable.** The snapshot stores `index` = position of the anchor query among
  `ul.plugin-tasks-query-result` lists currently in the editor DOM (main.js:3828–3876, 3948). Only _rendered_ results
  match the selector, the three Tasks queries render asynchronously and independently, and CM6 virtualizes offscreen
  content out of the DOM. So the index at capture time (scrolled deep — top blocks may be virtualized away, READY can be
  index 0) need not equal the index at restore time (top of file — later blocks missing) → `contexts[index]` is
  `undefined` or the _wrong_ block (main.js:4023).
- **S2 — the anchor may never materialize.** After a fresh open the view sits at `scrollTop = 0`. If the READY block is
  far below the viewport, CM may never create its DOM during the retry loop (nothing ever scrolls toward it), so
  `getDashboardQueryRestoreScrollTop` returns `null` every frame and the 12-rAF (~200 ms) budget exhausts silently,
  leaving only the raw `scrollTop` — which was captured against a fully-rendered layout but applied to a
  partially-rendered one, i.e. wrong.
- **S3 — premature success, no re-assert.** `needsQueryRetry` flips to `false` on the _first_ successful anchored write
  (main.js:9238) while the WIP/NEXT queries above the anchor may still be rendering; when they grow they push the READY
  block down and the already-written `scrollTop` goes stale. The `## Tasks` jump solved exactly this with an 8-frame
  assert window (`scheduleDashTasksScrollAssert`, main.js:4430); the restore path has no equivalent.
- **S4 — retry churn.** Every retry frame re-applies the stale raw `scrollTop` (main.js:9203–9218) before attempting the
  anchored write, yanking the viewport around while queries render.

## Design

All changes in `bob-plugins`, `plugins/bob-navigation-hotkeys/main.js`. Access the repo with
`sase workspace open -p bob-plugins <workspace_num>` (use the path it prints).

### Fix A (primary) — restore the cursor without revealing it

Add a non-scrolling cursor setter (e.g. `setEditorCursorWithoutScroll(editor, position)`: `editor.setCursor` only, no
`scrollIntoView`; Obsidian's `setCursor` does not scroll on its own — that is why `setEditorCursor` calls
`scrollIntoView` explicitly). Use it in `restoreActiveDashLocation`, and set the cursor **once per restore attempt
sequence** (the first frame where the dash view is active), not on every retry frame. Scroll position is owned
exclusively by the scroll writes.

Keep `setEditorCursor` (revealing) untouched for all other call sites — the `## Tasks` jump and the general
alternate-file flows rely on the reveal.

### Fix B — anchor the snapshot by source line, with index as fallback

At capture, resolve each rendered-query container to its source line via `editorView.posAtDOM(container)` +
`state.doc.lineAt(...)` (feature-detected; the widget maps to the block's start = its `tasks` fence line). Store
`sourceLine` in the snapshot alongside the existing `index`/`offsetTop`/`height`. At restore, select the context whose
own `posAtDOM`-derived line equals the stored `sourceLine`; fall back to the current index behavior when `sourceLine` or
`posAtDOM` is unavailable. Thread `sourceLine` through `normalizeDashboardRenderedTasksQuerySnapshot` /
`normalizeDashLocation` so it round-trips.

### Fix C — force the anchor region to materialize

In the restore retry loop, when no matching context is found but `sourceLine` is known, dispatch a coarse
`scrollEditorLineToTop(editor, sourceLine)` (existing helper, main.js:4158) before scheduling the next retry. That makes
CM materialize/render the anchor's region so a later frame can find the container and apply the precise query-anchored
offset. This turns the S2 dead-end into a converging loop.

### Fix D — re-assert window after the first successful anchored write

Add `DASH_LOCATION_RESTORE_ASSERT_FRAMES = 8` (mirroring `DASH_TASKS_SCROLL_ASSERT_FRAMES`). After the first successful
query-anchored write, keep recomputing `getDashboardQueryRestoreScrollTop` and re-applying it each frame for the assert
window, so late-rendering queries above the anchor can't leave the scroll stale. Keep `isRestoringDashLocation = true`
(captures suppressed) until the assert window completes, then clear it. Reuse the existing single
`pendingDashLocationRestoreDeferred` slot for cancellation, and make `cancelPendingDashLocationRestore` end the assert
window too.

### Fix E — stop re-applying the raw scroll on every retry

Apply the raw `scrollTop`/`scrollLeft` fallback only until the first query-anchored write succeeds (it is the
best-effort placeholder while the anchor is missing), never after; once anchored writes begin, they own the scroll.

### Tuning

Bump `DASH_LOCATION_RESTORE_RETRIES` from 12 to 24: Tasks query rendering can exceed 200 ms on a fresh open, retries are
cheap rAF frames, and with Fix C each frame now makes forward progress. Total worst-case budget stays well under a
second.

## Implementation steps

1. Constants: add `DASH_LOCATION_RESTORE_ASSERT_FRAMES = 8`; change `DASH_LOCATION_RESTORE_RETRIES` to 24.
2. Add `setEditorCursorWithoutScroll` next to `setEditorCursor`; add it to the `module.exports.helpers` block
   (convention: existing helpers are exported there).
3. `getRenderedTasksQueryContexts`: compute and attach `sourceLine` per context via feature-detected
   `editorView.posAtDOM` + `doc.lineAt`; tolerate failures by leaving `sourceLine` null.
4. `getDashboardRenderedTasksQuerySnapshot`: include `sourceLine` in the returned snapshot.
   `normalizeDashboardRenderedTasksQuerySnapshot`: round-trip `sourceLine` (integer ≥ 0 or null).
5. `getDashboardQueryRestoreScrollTop`: select the anchor context by `sourceLine` match first, `index` fallback.
6. Rework the restore loop (`restoreOrDeferDashLocation` / `restoreOrDeferDashLocationInternal` /
   `restoreActiveDashLocation`) to implement Fixes A, C, D, E: track per-sequence state (cursor applied? raw scroll
   applied? anchored write succeeded? assert frames remaining), dispatch the coarse materializing scroll when the anchor
   is missing, and run the assert window after first anchored success.
7. `npm run validate` (manifest + `node --check` across plugins).
8. Deploy per memory `bob-plugins-deploy-from-workspace`:
   `bob plugins sync -p bob-navigation-hotkeys -r "$PWD" --dry-run` then without `--dry-run`; verify deployed file
   matches source.

## Verification

No automated test harness exists in bob-plugins (`npm run validate` is syntax/manifest only). After deploy, reload the
plugin in Obsidian and run this manual matrix:

1. **The repro (must pass):** open `dash.md`, scroll to the _middle of the READY Tasks results_, click a task link,
   press `<Ctrl+0>` → view returns to the same spot in READY results; cursor is **not** revealed at `## Projects`.
2. Repeat #1 but click a link near the very top edge of the READY widget (click may map _before_ the widget) and from
   the WIP and NEXT sections → restore still lands correctly.
3. **No `f650ce7` regression:** `dash.md` open in another tab, scrolled down; from a different tab press `<Ctrl+0>` →
   tab activates with its live scroll untouched.
4. **First open of the session:** `<Ctrl+0>` jumps to `## Tasks` header (unchanged).
5. **Already focused:** `<Ctrl+0>` on a focused `dash.md` does nothing jarring.
6. **Robustness:** check off / uncheck a few tasks (query heights change), navigate away and back → restore still lands
   on the same visual content (query-anchored offset holds).
7. **Slow-render tolerance:** immediately after an Obsidian restart (cold Tasks index), repro flow again — the longer
   retry budget + materializing scroll should still converge.

## Notes / open questions

- **Manifest version stays `1.8.0`** — consistent with `98f946e`/`f650ce7`/`ff33e83`, which did not bump it.
- The poisoned `sourcePosition` (Projects line) is still captured and restored — but non-revealingly, so it is invisible
  to the user and harmless. Filtering out click-on-widget selection captures was considered and rejected: there is no
  reliable way to distinguish them from intentional cursor moves, and once the reveal is gone the value is cosmetic.
- If `dash.md` is edited between capture and restore, a stored `sourceLine` may drift; the index fallback plus the
  offset clamps keep the failure mode mild (nearest-block restore), matching today's behavior at worst.
- `editor.setCursor` is assumed non-scrolling (it is why `setEditorCursor` adds an explicit `scrollIntoView`);
  verification step 1 confirms this interactively.
