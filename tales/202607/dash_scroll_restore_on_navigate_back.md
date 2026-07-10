---
create_time: 2026-07-10 10:31:44
status: wip
prompt: .sase/sdd/prompts/202607/dash_scroll_restore_on_navigate_back.md
---
# Plan: Restore `dash.md` scroll position on `<Ctrl+0>` even when it is not already open in a tab

## Problem / product context

The `bob-navigation-hotkeys` Obsidian plugin binds `<Ctrl+0>` (command `open-dash-tasks`, method `openDashTasks()`) to
jump to `~/bob/dash.md`. It was recently changed to _preserve the dashboard's scroll position_ when returning to it.

Today that preservation only works when `dash.md` is **still open in an existing Obsidian tab**: in that case `<Ctrl+0>`
merely re-activates the existing leaf, and Obsidian keeps the leaf's live scroll position for free.

It does **not** work when `dash.md` is no longer open in any tab. The most common way this happens: the user clicks a
link inside `dash.md`, so that _same leaf_ navigates away to the link target and `dash.md` no longer has a leaf.
Pressing `<Ctrl+0>` then re-opens `dash.md` fresh and jumps to the `## Tasks` header (cursor near the top), losing the
scroll position the user was at.

**Goal:** `<Ctrl+0>` should restore the previous scroll/cursor position of `dash.md` in this "navigated-away-then-back"
case too — while NOT regressing the already-open-in-a-tab case.

## Root cause (from git history)

Two recent commits on `bob-plugins` `master` bracket this feature:

- `98f946e` — _"fix: preserve dashboard position on hotkey"_ — added a full **`dashLocation` remember/restore system**.
  It continuously captures `dash.md`'s cursor + `scrollTop`/`scrollLeft` **plus a re-render-robust "rendered
  Tasks-query" snapshot** (which live Tasks-query block sits at the viewport top and the pixel offset within it), and on
  `<Ctrl+0>` restores that location. The Tasks-query snapshot exists because `dash.md` is dominated by live `tasks`
  query blocks whose rendered heights change as tasks are checked off, so a raw `scrollTop` would drift; the snapshot is
  anchored to a specific query block instead.

- `f650ce7` — _"fix: preserve dashboard scroll on tab switch"_ — **reverted essentially all of that machinery.** Its
  rationale: `98f946e` restored the remembered location _even when re-activating an already-open `dash.md` tab_, which
  clobbered that tab's live scroll. Rather than gate the restore, the commit deleted the whole system, leaving only: (1)
  if `dash.md` is the active view → do nothing; (2) if `dash.md` is open in another leaf → activate it (scroll kept by
  Obsidian); (3) otherwise → open fresh and jump to the `## Tasks` header.

So the current bug is a direct consequence of `f650ce7` over-reverting: it correctly protected the already-open case but
threw away restore-on-return-after-navigating-away, which is what the user now wants back.

The machinery from `98f946e` was sound; only its _gating_ was wrong (it restored in too many cases).

## Design

Re-introduce the `dashLocation` remember/restore machinery from `98f946e`, but **gate the restore so it runs only on the
fresh-open path** — i.e. only when `dash.md` was NOT already open in a tab. When we activate an existing `dash.md` leaf,
we must NOT restore (leave the tab's live scroll untouched); that is exactly the case `f650ce7` was protecting.

### Behavior matrix (target end state)

| `<Ctrl+0>` scenario                                                        | Action                                                                          | Scroll result                                                     |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 1. `dash.md` is the active/focused view                                    | Refresh the scroll-capture listener + capture current location; do nothing else | Untouched (already there)                                         |
| 2. `dash.md` open in another tab (existing leaf, not active)               | Activate that leaf; **do NOT restore**                                          | Obsidian keeps the tab's live scroll ✅ (no `f650ce7` regression) |
| 3. `dash.md` NOT open anywhere (clicked a link → same leaf navigated away) | Open fresh; **restore** remembered `dashLocation`                               | **Scroll restored ✅ (fixes the bug)**                            |
| 4. First `dash.md` open of the session (nothing captured yet)              | Open fresh; nothing remembered → jump to `## Tasks` header                      | Jump to Tasks (unchanged)                                         |

The distinction between #3 (restore) and #4 (jump to Tasks) falls out naturally: `getRememberedDashLocation()` returns
`null` until `dash.md` has been viewed/scrolled at least once, so a first-ever open jumps to Tasks and a
return-after-navigate restores.

### How capture stays current (so #3 has something to restore)

The machinery keeps `this.dashLocation` up to date while `dash.md` is on screen, via:

- a `scroll` event listener attached to the dash editor's `scrollDOM` (`refreshDashScrollCaptureTarget` /
  `scheduleDashLocationCapture` → `captureDashLocationFromView`);
- `trackSelectionUpdate` capturing on cursor/selection/viewport changes when the active file is `dash.md`;
- listener (re)attachment wired on `onLayoutReady`, `active-leaf-change`, and `file-open` (`trackOpenedFile`), with
  cleanup on unload.

So by the time the user clicks a link and navigates away, `this.dashLocation` already holds the last on-screen
scroll/cursor of `dash.md`. A programmatic-restore feedback loop is prevented by the `isRestoringDashLocation` guard
(captures are suppressed while a restore is in flight).

## Implementation

All changes are in the `bob-plugins` repo, file `plugins/bob-navigation-hotkeys/main.js`. Access the repo with
`sase workspace open -p bob-plugins <workspace_num>` (use the path it prints).

### Step 1 — Re-introduce the machinery reverted by `f650ce7`

The cleanest, lowest-risk way to reproduce the ~300 lines of `98f946e` machinery exactly is to revert the reverting
commit:

```bash
git revert --no-commit f650ce7
```

`f650ce7` is the current tip of `master`, so this applies cleanly and restores the full `98f946e` state. This re-adds,
verbatim:

- **Constants:** `DASH_LOCATION_RESTORE_RETRIES`, `DASH_RENDERED_TASKS_QUERY_RESULT_SELECTOR`,
  `DASH_RENDERED_TASKS_BLOCK_SELECTOR`, `DASH_RENDERED_TASKS_SCROLL_PADDING_PX`.
- **Module helpers:** `getScrollDOMMaxScrollTop`, `getScrollDOMMaxScrollLeft`, `setScrollDOMPosition`,
  `getRenderedTasksQueryContexts`, `findDashboardRenderedTasksQueryContext`, `getDashboardRenderedTasksQuerySnapshot`,
  `normalizeDashboardRenderedTasksQuerySnapshot`, `normalizeDashLocation`, `getDashboardQueryRestoreScrollTop` (and
  their re-additions to the `module.exports.helpers` block). (`finiteNumberOrNull`, `clampNumber`,
  `getEditorViewFromEditor`, `getElementRect`, `getVerticalIntersectionHeight` already survived the revert — the
  un-revert will not duplicate them.)
- **Instance fields** in `onload()`: `this.dashLocation`, `this.pendingDashLocationRestoreDeferred`,
  `this.pendingDashLocationCaptureDeferred`, `this.activeDashScrollDOM`, `this.activeDashScrollHandler`,
  `this.isRestoringDashLocation`.
- **Wiring:** `refreshDashScrollCaptureTarget()` call in the `onLayoutReady` callback; the `active-leaf-change` →
  `refreshDashScrollCaptureTarget()` registration; the `refreshDashScrollCaptureTarget()` /
  `clearDashScrollCaptureTarget()` calls in `trackOpenedFile`; the dash capture block in `trackSelectionUpdate`; and the
  three cancels/clear in the `this.register(() => …)` unload cleanup.
- **Methods:** `getRememberedDashLocation`, `refreshDashScrollCaptureTarget`, `clearDashScrollCaptureTarget`,
  `scheduleDashLocationCapture`, `cancelPendingDashLocationCapture`, `captureActiveDashLocation`,
  `captureDashLocationFromView`, `restoreOrDeferDashLocation`, `restoreOrDeferDashLocationInternal`,
  `restoreActiveDashLocation`, `cancelPendingDashLocationRestore`.

It will also restore `98f946e`'s version of `openDashTasks`, which contains the mis-gating bug. Step 2 replaces that
method.

> If a direct `git revert` is undesirable, the alternative is to hand-re-add the exact functions, fields, wiring, and
> methods listed above from the `98f946e` diff — the end state is identical.

### Step 2 — Correct the gating in `openDashTasks()`

Replace `openDashTasks()` with the version below. The **only** semantic change from `98f946e` is that the restore now
happens **exclusively on the fresh-open branch**; when we activate an existing leaf we return early WITHOUT restoring
(matching `f650ce7`'s protection of the already-open case).

```js
async openDashTasks() {
  const file = this.app.vault.getAbstractFileByPath(DASH_FILE_PATH);
  if (!this.isMarkdownFile(file)) {
    new Notice(`${DASH_FILE_PATH} not found`);
    return false;
  }

  const activeView = this.getActiveMarkdownView();
  if (activeView && activeView.file.path === file.path) {
    // dash.md already focused: keep it fresh for capture, do not disturb scroll.
    this.cancelPendingDashTasksJump();
    this.cancelPendingDashLocationRestore();
    this.refreshDashScrollCaptureTarget(activeView);
    this.captureDashLocationFromView(activeView);
    return true;
  }

  this.captureActiveFilePosition();
  // Read the remembered location BEFORE opening: openFile makes dash active and
  // may overwrite this.dashLocation (via capture) with the fresh top-of-file state.
  const rememberedDashLocation = this.getRememberedDashLocation();

  try {
    const existingLeaf = this.findMarkdownLeafByPath(file.path);
    if (existingLeaf && (await this.activateWorkspaceLeaf(existingLeaf))) {
      // dash.md is already open in a tab; leave its live scroll untouched.
      this.cancelPendingDashTasksJump();
      this.cancelPendingDashLocationRestore();
      this.refreshDashScrollCaptureTarget();
      return true;
    }

    await this.app.workspace.getLeaf(false).openFile(file);
  } catch (error) {
    new Notice(`Could not open ${DASH_FILE_PATH}`);
    return false;
  }

  // Fresh open (dash.md was not already open in a tab): restore the remembered
  // scroll/cursor if we have one, otherwise jump to the Tasks section.
  this.refreshDashScrollCaptureTarget();

  if (rememberedDashLocation) {
    this.restoreOrDeferDashLocation(rememberedDashLocation);
  } else {
    this.jumpOrDeferDashTasks();
  }
  return true;
}
```

Key correctness points:

- `rememberedDashLocation` is captured into a local **before** `openFile`, so restore is immune to `this.dashLocation`
  being overwritten by the fresh open.
- The existing-leaf branch returns early with no restore — no `f650ce7` regression.
- `restoreOrDeferDashLocation` sets `isRestoringDashLocation = true` (suppressing capture feedback) and retries up to
  `DASH_LOCATION_RESTORE_RETRIES` frames so the rendered Tasks queries have time to render before the query-anchored
  scroll is resolved.

## Verification

There is no automated test harness in this repo (only `npm run validate`, a manifest + `node --check` syntax check).
Verify as follows.

1. **Syntax / manifest validation** (from the `bob-plugins` workspace):

   ```bash
   npm run validate
   ```

2. **Deploy to the vault**, then reload the plugin in Obsidian (see memory `bob-plugins-deploy-from-workspace`):

   ```bash
   bob plugins sync -p bob-navigation-hotkeys -r "$PWD" --dry-run   # preview
   bob plugins sync -p bob-navigation-hotkeys -r "$PWD"
   ```

3. **Manual functional checks in Obsidian:**
   - **Fixes the bug (#3):** Open `dash.md`, scroll well down into the Tasks section, click a link in `dash.md` so the
     same tab navigates away, then press `<Ctrl+0>` → `dash.md` reopens at the same scroll position (not the top / not
     the `## Tasks` header).
   - **No `f650ce7` regression (#2):** Open `dash.md` in a tab, scroll down, switch to a _different_ tab, press
     `<Ctrl+0>` → the dash tab activates with its original scroll intact (no jump).
   - **First-open behavior (#4):** With no prior dash view this session, press `<Ctrl+0>` → opens and jumps to the
     `## Tasks` header.
   - **Already-focused (#1):** With `dash.md` focused, press `<Ctrl+0>` → nothing jarring happens (scroll unchanged).
   - Sanity: confirm restoration still lands correctly after checking off / completing some tasks in the queries (the
     query-anchored snapshot should keep it robust to height changes).

## Notes / open questions

- **Manifest version bump:** `bob-navigation-hotkeys` is at `1.8.0`. Neither `98f946e` nor `f650ce7` bumped it, so this
  change follows suit and leaves the version as-is unless Bryan prefers a patch bump.
- **Simpler alternative considered & rejected:** using Obsidian's native `getEphemeralState()` / `setEphemeralState()`
  (line-based scroll) instead of the custom machinery. Rejected because the author deliberately built the
  rendered-Tasks-query-anchored snapshot to survive the live query blocks' changing heights; native line-based scroll
  would regress restore fidelity on the query-heavy `dash.md`.
