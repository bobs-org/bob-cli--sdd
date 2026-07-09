---
create_time: 2026-07-09 13:28:35
status: done
prompt: .sase/sdd/prompts/202607/dash_scroll_preserve_on_tab_switch.md
---
# Plan: Preserve `dash.md` Tasks-query scroll on `<Ctrl+0>` tab switch

## Context

`<Ctrl+0>` is the `open-dash-tasks` command in the `bob-navigation-hotkeys` Obsidian plugin (in the linked `bob-plugins`
repo, `plugins/bob-navigation-hotkeys/main.js`). A prior change ("preserve dashboard position on hotkey") added an
in-session scroll-memory feature: it captures the dashboard's source cursor, absolute scroll, and a
rendered-Tasks-query-relative scroll snapshot, then re-applies ("restores") them whenever `<Ctrl+0>` runs.

Reported bug: when the user has scrolled to the **middle** of a rendered Tasks query (e.g. WIP / NEXT / READY under
`## Tasks`), switches to another tab, and presses `<Ctrl+0>` to come back, the view **always jumps to the bottom of that
query** instead of returning to where they were.

The user has scoped the requirement: this only needs to work correctly for the case where `dash.md` is **already loaded
in a tab**. A simple tab switch back to that tab is sufficient — no custom scroll math is required for that case.

## Root cause

The restore logic is clobbering a scroll position Obsidian had already preserved correctly.

1. `openDashTasks()` finds the already-open `dash.md` leaf and activates it via `activateWorkspaceLeaf()`
   (`revealLeaf` + `setActiveLeaf`). That activation does **not** touch scroll — Obsidian natively keeps each open
   editor leaf at its own scroll position across tab switches. At this point the view is already correct.

2. `openDashTasks()` then **unconditionally** calls `restoreOrDeferDashLocation(rememberedDashLocation)`, which
   overwrites that correct position:
   - It sets the source cursor with `setEditorCursor()`, which also calls `editor.scrollIntoView(...)` on the tiny
     source `tasks` fence line (above the rendered results).
   - It applies the saved absolute `scrollTop`.
   - It computes and applies a query-relative `scrollTop` via `getDashboardQueryRestoreScrollTop()` — this is the final,
     winning write.

3. `getDashboardQueryRestoreScrollTop()` clamps the saved mid-query offset to
   `maxRelativeOffset = currentQueryHeight - PADDING`, using the query's **current** rendered height. On a tab switch
   the Tasks query re-renders and is **transiently short**, so a middle offset exceeds the short query's height and
   clamps to that query's (current) bottom.

4. Because that clamped computation **succeeds** (returns a non-null scrollTop), `needsQueryRetry` is cleared and the
   deferred retry loop **stops** — locking in the bottom position and never re-correcting after the query expands to
   full height.

Net effect: every `<Ctrl+0>` tab switch discards Obsidian's correctly-preserved scroll and lands at the query's bottom —
exactly the reported "always jumps to the bottom" symptom. The restore is not only unnecessary for an already-open tab;
it is the direct cause of the bug. (The same geometry is unreliable for the fresh-open case too, but the user does not
need that case to be perfect.)

## Goal

Make `<Ctrl+0>` rely on Obsidian's native per-leaf scroll preservation for the case that matters, and stop running the
buggy custom restore:

- If `dash.md` is already the active view → leave it exactly as-is (do not move scroll or cursor, do not jump to
  `## Tasks`).
- If `dash.md` is already open in another tab/leaf → activate that leaf and do nothing else; its scroll position (mid-
  query included) is preserved by Obsidian.
- If `dash.md` is not open anywhere → open it and keep the existing first-open behavior of jumping to `## Tasks`.

Keep the good behavioral wins from the prior change (never force an already-open/already-active dashboard back to
`## Tasks`). Remove the scroll-memory capture/restore machinery that produced the bug.

## Implementation plan

Work only in the linked `bob-plugins` repo (`plugins/bob-navigation-hotkeys/main.js`). Do not edit the deployed vault
copy directly; deploy via `bob plugins sync` after validation.

1. **Simplify `openDashTasks()` to activate-only for open leaves.**
   - Already-active `dash.md`: cancel any pending first-open jump and return without capturing/restoring or jumping.
   - Existing `dash.md` leaf: activate it and return. Do **not** call any dashboard restore. Rely on Obsidian preserving
     the leaf's scroll.
   - No existing leaf (truly fresh open): open the file in a leaf, then call the existing `jumpOrDeferDashTasks()` so a
     brand-new dashboard still lands at `## Tasks`.

2. **Remove the dashboard scroll-memory capture/restore feature** (the source of the bug and now unused):
   - Plugin state: `dashLocation`, `isRestoringDashLocation`, `activeDashScrollDOM`, `activeDashScrollHandler`,
     `pendingDashLocationRestoreDeferred`, `pendingDashLocationCaptureDeferred`.
   - Methods: `getRememberedDashLocation`, `refreshDashScrollCaptureTarget`, `clearDashScrollCaptureTarget`,
     `scheduleDashLocationCapture`, `cancelPendingDashLocationCapture`, `captureActiveDashLocation`,
     `captureDashLocationFromView`, `restoreOrDeferDashLocation`, `restoreOrDeferDashLocationInternal`,
     `restoreActiveDashLocation`, `cancelPendingDashLocationRestore`.
   - Free helpers made unused by the above: the rendered-Tasks-query geometry/snapshot functions
     (`getRenderedTasksQueryContexts`, `findDashboardRenderedTasksQueryContext`,
     `getDashboardRenderedTasksQuerySnapshot`, `normalizeDashboardRenderedTasksQuerySnapshot`,
     `getDashboardQueryRestoreScrollTop`, `normalizeDashLocation`) and any scroll-DOM helpers that become unused as a
     result (e.g. `setScrollDOMPosition`, `getScrollDOMMaxScrollTop`, `getScrollDOMMaxScrollLeft`). Before deleting each
     helper, confirm it is not referenced by any other feature in this file (e.g. `getElementRect`,
     `getVerticalIntersectionHeight`, `finiteNumberOrNull`, `clampNumber` are shared and must stay).
   - Constants: `DASH_LOCATION_RESTORE_RETRIES`, `DASH_RENDERED_TASKS_QUERY_RESULT_SELECTOR`,
     `DASH_RENDERED_TASKS_BLOCK_SELECTOR`, `DASH_RENDERED_TASKS_SCROLL_PADDING_PX`.
   - Update the `module.exports.helpers` list to drop every deleted function.

3. **Unwire the capture hooks from lifecycle/events.**
   - Remove the `refreshDashScrollCaptureTarget()` calls in `onLayoutReady`, the `active-leaf-change` handler,
     `trackOpenedFile`, and `trackSelectionUpdate`, plus the dash-specific `captureDashLocationFromView(...)` call in
     `trackSelectionUpdate`.
   - Remove the corresponding cleanup calls (`cancelPendingDashLocationRestore`, `cancelPendingDashLocationCapture`,
     `clearDashScrollCaptureTarget`) from the unload `register(() => ...)` block.
   - Leave the generic per-file cursor tracking (`filePositions` / `saveFilePosition`) untouched; it serves other
     navigation commands.

4. **Keep the first-open path intact.**
   - Retain `getDashTasksHeaderLine`, `jumpOrDeferDashTasks`, `jumpToActiveDashTasks`, `scheduleDashTasksScrollAssert`,
     `scrollEditorLineToTop`, and `DASH_TASKS_JUMP_RETRIES`, and the "`## Tasks` header missing" notice behavior.

## Validation

1. In the linked `bob-plugins` repo: `node --check plugins/bob-navigation-hotkeys/main.js` and `npm run validate`.
2. Deploy: `bob plugins sync -p bob-navigation-hotkeys -r <linked bob-plugins repo path>`.
3. Manual checks in Obsidian (primary requirement first):
   - Open `dash.md`, scroll to the **middle** of a rendered WIP/NEXT/READY Tasks query, switch to another tab, press
     `<Ctrl+0>` → returns to that same mid-query position (no jump to the bottom or top).
   - Open `dash.md` in a background tab, scroll near `## Projects` / `## Reading List`, switch away, press `<Ctrl+0>` →
     activates that tab at its existing scroll.
   - Press `<Ctrl+0>` while already viewing `dash.md` → nothing moves.
   - With `dash.md` not open in any tab, press `<Ctrl+0>` → opens it and lands at `## Tasks`.
   - Confirm unrelated navigation hotkeys (parent/child/alternate, `<Ctrl+d>/<Ctrl+u>`) are unchanged.

## Risks and alternatives

- **Relies on Obsidian preserving per-leaf scroll across tab switches.** This is standard Obsidian behavior, the prior
  implementation already assumed it ("activation itself may already preserve the leaf's real scroll"), and the user has
  confirmed a plain tab switch suffices. If a future case surfaces where activation does not preserve scroll, revisit
  with a targeted, query-render-aware restore rather than the removed unconditional one.
- **Fresh-open (tab was closed) no longer restores the last scroll**, only jumps to `## Tasks`. This is acceptable per
  the stated scope (only the already-loaded-tab case must work).
- **Alternative (smaller diff):** keep all the capture/restore machinery and only skip `restoreOrDeferDashLocation` when
  an existing leaf was activated. This fixes the reported symptom with minimal change but leaves unreachable, buggy code
  and its per-scroll listeners in place. Preferred approach is the full removal above, since that machinery exists
  solely to serve the now-eliminated restore and was the bug's source.
