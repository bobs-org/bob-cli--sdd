---
create_time: 2026-07-09 13:06:47
status: done
prompt: .sase/sdd/prompts/202607/dash_location_memory.md
tier: tale
---
# Plan: Remember `dash.md` Location for `<Ctrl+0>`

## Context

`<Ctrl+0>` is implemented by the `bob-navigation-hotkeys` Obsidian plugin in the linked `bob-plugins` repository. The
command is `open-dash-tasks`, bound to `Ctrl+0`, and it currently calls `openDashTasks()`.

The current flow always forces the dashboard to `## Tasks`:

- `openDashTasks()` opens or activates `dash.md`.
- `jumpOrDeferDashTasks()` waits for the active markdown editor.
- `jumpToActiveDashTasks()` sets the cursor to the `## Tasks` source line.
- `scrollEditorLineToTop()` top-aligns that line.
- `scheduleDashTasksScrollAssert()` repeats that cursor/scroll correction across several frames.

That repeated assertion is why an already-open dashboard tab loses its previous scroll/cursor location.

`~/bob/dash.md` currently has three very small source `tasks` code fences under `## Tasks`:

- `### WIP Tasks`
- `### NEXT Tasks`
- `### READY Tasks`

Those source fences can render many virtual rows through the Obsidian Tasks plugin. Therefore, remembering only the
Markdown source cursor line is not enough; a user can be visually halfway through a rendered query while the source
cursor still lives near a tiny fenced block.

The existing `<Ctrl+d>/<Ctrl+u>` handling in `task-status-cycler` already accounts for this by measuring rendered Tasks
query DOM blocks (`ul.plugin-tasks-query-result` inside `.block-language-tasks`) and scrolling `editorView.scrollDOM`,
while keeping the source cursor outside query fences. The dashboard restore should use the same kind of rendered-scroll
awareness instead of pretending query output maps cleanly to physical source lines.

## Goal

Change `<Ctrl+0>` so it opens or activates `dash.md` and returns to the last meaningful dashboard location:

- If `dash.md` is already active, leave the current location alone.
- If `dash.md` is already open in another tab/leaf, activate that leaf without resetting it to `## Tasks`.
- If `dash.md` was visited earlier in the session, restore its remembered source cursor and scroll location.
- If the remembered location was inside or near a rendered Tasks query result, restore the rendered query viewport using
  query-relative scroll state.
- If no usable dashboard location has ever been captured, keep the old first-open fallback of jumping to `## Tasks`.

Keep this in-session and aligned with the plugin's existing `filePositions` map. Do not add persistent disk writes on
every scroll unless a later requirement explicitly asks for cross-restart persistence.

## Implementation Plan

1. Work in the linked `bob-plugins` repository, not the deployed vault plugin folder.
   - Edit `plugins/bob-navigation-hotkeys/main.js`.
   - Do not edit `~/bob/.obsidian/plugins/bob-navigation-hotkeys/` directly.
   - Deploy only after validation with `bob plugins sync -p bob-navigation-hotkeys -r <linked bob-plugins repo>`.

2. Add dashboard-specific location state to `BobNavigationHotkeysPlugin`.
   - Reuse the existing source cursor tracking where possible: `filePositions.get("dash.md")`.
   - Add a `dashLocation` object for scroll-specific data:
     - source cursor `{ line, ch }`
     - absolute `scrollTop` / `scrollLeft`
     - optional rendered Tasks query snapshot:
       - query index among rendered Tasks query blocks in document order
       - query-relative vertical offset from the query block's top
       - query height at capture time, used only for sanity/clamping
   - Track pending deferred restore handles separately from the existing dash scroll assertion, or rename the existing
     pending dash fields so the new intent is clear.

3. Capture dashboard location from both cursor updates and scroll changes.
   - Extend `trackSelectionUpdate()` so when the active markdown file is `dash.md`, it also refreshes `dashLocation`.
   - Capture source position through the existing `positionFromCodeMirrorUpdate()` / editor cursor path.
   - Capture rendered scroll through `view.editor.cm.scrollDOM` when available.
   - Add small DOM/geometry helpers modeled on `task-status-cycler`:
     - get a safe element rect
     - find rendered Tasks query contexts with `ul.plugin-tasks-query-result` and `.block-language-tasks`
     - choose the visible query with the largest viewport intersection, falling back to the nearest query
     - compute query-relative offset as `currentScrollTop - queryDocumentTop`
   - Add a throttled scroll capture path. Prefer a CodeMirror update signal if `viewportChanged` reliably fires;
     otherwise attach a passive `scroll` listener to the active dashboard editor's `scrollDOM` and schedule capture with
     `requestAnimationFrame`.

4. Replace the forced `## Tasks` jump with restore-first behavior.
   - In `openDashTasks()`, capture the current file position before leaving the active note as it does today.
   - If the active file is already `dash.md`, capture the current dashboard location and return without calling
     `jumpOrDeferDashTasks()`.
   - If an existing `dash.md` leaf is found, activate it and then run a best-effort dashboard restore. The activation
     itself may already preserve the leaf's real scroll; the restore should only correct it if remembered state exists.
   - If `dash.md` is newly opened, restore a remembered dashboard location if one exists.
   - Only call the old `## Tasks` jump path when there is no remembered dashboard location.

5. Implement deferred dashboard restore.
   - Add `restoreOrDeferDashLocation(location, retriesRemaining)` similar to `jumpOrDeferDashTasks()`.
   - Once `dash.md` is the active markdown view:
     - clamp and set the source cursor, if available
     - restore absolute scroll immediately as a low-cost first approximation
     - if a rendered query snapshot exists and rendered query DOM is available, compute the current query's document top
       and restore `queryTop + savedRelativeOffset`, clamped to the scroll container bounds
   - Retry for several animation frames because Tasks query rendering can lag behind file opening, just like the current
     `scheduleDashTasksScrollAssert()` assumes.
   - Do not repeatedly force the cursor back to `## Tasks` during restore.

6. Keep the old `## Tasks` behavior as the no-memory fallback only.
   - `getDashTasksHeaderLine()` can stay.
   - `jumpToActiveDashTasks()` and `scheduleDashTasksScrollAssert()` can remain for first-open/no-memory behavior, but
     they must not run after a valid dashboard location has been restored.
   - If the `## Tasks` header is missing, preserve the current notice behavior.

7. Account explicitly for rendered Tasks query virtual lines.
   - Do not try to map rendered Tasks rows back to Markdown source lines; the source fence is too small to represent the
     rendered list.
   - Treat the source cursor and rendered scroll as separate layers.
   - When the user is visually inside WIP/NEXT/READY query output, restore by query index plus relative scroll offset.
   - If query contents changed since capture, clamp to the nearest valid scroll position inside that query.
   - If the query DOM is unavailable after retries, fall back to the saved absolute scroll position and source cursor.

8. Preserve unrelated navigation behavior.
   - Do not change parent/child/alternate note opening semantics except for shared helpers if needed.
   - Do not change `<Ctrl+d>/<Ctrl+u>` behavior in `task-status-cycler`.
   - Avoid importing between plugins; these plain CommonJS plugins are deployed independently, so duplicate the small
     geometry helpers in `bob-navigation-hotkeys` if needed.

## Validation

1. Run plugin validation in `bob-plugins`:

   ```bash
   npm run validate
   ```

2. Optionally run a targeted syntax check while iterating:

   ```bash
   node --check plugins/bob-navigation-hotkeys/main.js
   ```

3. Deploy the plugin to the vault:

   ```bash
   bob plugins sync -p bob-navigation-hotkeys -r <linked bob-plugins repo>
   ```

4. Manually verify in Obsidian:
   - With no remembered dash location, `<Ctrl+0>` opens `dash.md` at `## Tasks`.
   - Scroll into the middle or bottom of a rendered WIP/NEXT/READY Tasks query, switch to another note, then press
     `<Ctrl+0>`; it returns to that rendered query location.
   - Open `dash.md` in another tab, scroll near `## Projects` or `## Reading List`, switch away, then press `<Ctrl+0>`;
     it activates the existing tab without jumping to the top.
   - Press `<Ctrl+0>` while already viewing `dash.md`; it does not reset the scroll.
   - Use `<Ctrl+d>/<Ctrl+u>` inside rendered query results before switching away; `<Ctrl+0>` restores the resulting
     rendered scroll position.
   - Change the query results enough that the old offset is no longer exact; restore clamps instead of failing or
     jumping to the top.

## Risks and Mitigations

- Rendered Tasks query DOM can appear after the markdown editor is active. Mitigation: restore over several animation
  frames, like the current dash scroll assertion.
- Absolute `scrollTop` can become stale when query results change. Mitigation: prefer query-relative restore when a
  rendered query snapshot is available.
- Scroll listeners can be noisy. Mitigation: capture only for active `dash.md`, throttle with `requestAnimationFrame`,
  and store only in memory.
- Multiple open `dash.md` leaves can have different positions. Initial implementation can keep one dashboard memory
  because the command's purpose is "last dashboard location"; activating an already-open leaf should also preserve that
  leaf's own live scroll when possible.
