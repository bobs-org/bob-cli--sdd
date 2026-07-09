---
title: Obsidian Task Toggle Promotion Routing to Tasks
status: done
create_time: 2026-06-19 08:16:37
prompt: sdd/prompts/202606/obsidian_task_toggle_tasks_promotion.md
---

# Plan: Move Promoted Bullets Back to Tasks

## Context

The affected behavior lives in Bryan's live Obsidian vault plugin, not in the Rust CLI workspace:

- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`
- `/home/bryan/bob/.obsidian/hotkeys.json`

The `<Ctrl+Shift+]>` command is already registered as `task-status-cycler:toggle-obsidian-task`; this change should not
modify hotkeys or command registration.

The current command path is:

1. `handleToggleObsidianTaskCommand()` calls `getActiveObsidianTaskToggle()`.
2. `getActiveObsidianTaskToggle()` calls `getObsidianTaskToggleDocumentPlan()`.
3. The planner converts the active line through `getObsidianTaskToggle()`.
4. If the active source line is a routing-eligible top-level dash item, the planner may return a move plan.
5. The editor path applies either an in-place replacement or the move plan, then follows the cursor to the converted
   line.

The prior change updated demotion routing:

- Demoting a proper Obsidian task now converts it to a normal bullet and moves that bullet to the next Markdown section
  in document order.
- If there is no next section, demotion falls back to the existing in-place rewrite.

The promotion side is still carrying old assumptions:

- It currently requires both `Tasks` and `Future Work` to exist before moving a promoted bullet into `Tasks`.
- It targets `Tasks`, but does not explicitly distinguish a bullet already in the direct `Tasks` body from a bullet in
  some other section.

The requested reverse behavior is: converting a bullet to an Obsidian task from any other section should move that task
to the `Tasks` section, if one exists.

## Goal

When `<Ctrl+Shift+]>` is used on a routing-eligible top-level dash bullet or checklist item that is outside the direct
body of the `Tasks` section:

1. Convert the line to a proper Obsidian task using the existing promotion helper.
2. Preserve the whole list-item block, including child lines.
3. Move the converted block into the `Tasks` section if a `Tasks` heading exists.
4. Insert it using the existing `Tasks` insertion policy.
5. If no `Tasks` section exists, keep the current in-place promotion fallback.

Do not change demotion-to-next-section behavior, hotkey registration, Vim mappings, task syntax rules, cursor following,
or unrelated vault files.

## Behavior Specification

### Routing Eligibility

Keep the same movement guard that the planner already uses:

- Only top-level dash list lines route between sections.
- Plain top-level dash bullets and top-level dash checklist items can route.
- Indented items, blockquoted items, ordered items, and alternate bullet markers (`+` and `*`) still convert in place.
- Non-list/non-task lines remain no-ops.

This matches the previous safety rule and the shape of bullets produced by demotion, which are top-level dash bullets.
If broader marker routing is desired later, it should be a separate behavior change because it increases the blast
radius for nested and nonstandard list layouts.

### Source Section Rule

Treat the `Tasks` section's direct body as the active task list:

- The direct body starts after the `Tasks` heading.
- It ends at the next Markdown heading of any depth, or EOF.
- A bullet already in that direct body should promote in place and should not be moved to the end of `Tasks`.
- A bullet under a child heading below `Tasks`, such as `### Future Work`, is considered to be in another section and
  should move up into the direct `Tasks` body.
- A bullet before the `Tasks` heading, after the `Tasks` section, or under any other heading should move into `Tasks`.

This makes the reverse workflow match the previous demotion workflow: a task demoted from the direct `Tasks` body into
the next section can later be promoted from that other section and return to the direct `Tasks` body.

### Target Section Rule

Use the first exact Markdown section named `Tasks`, matching the existing `findNamedMarkdownSection()` behavior.

If no `Tasks` heading exists:

- Convert the bullet in place.
- Do not create a `Tasks` heading.
- Do not move the item to a guessed location.

The existing `Future Work` heading should not be required for promotion routing anymore.

### Target Insertion Point

Keep the current task insertion behavior:

- After removing the source block from a copy of the document, find the `Tasks` section again in the remaining lines so
  insert positions are correct whether the source block was before or after `Tasks`.
- Insert into the direct `Tasks` body by calling `getSectionInsertionLine()` with `stopAtChildHeadings: true`.
- If `Tasks` already has direct-body content, append after the last nonblank direct-body line.
- If `Tasks` has no direct-body content, use the helper's existing blank-line policy.

Do not switch promotion insertion to the demotion-specific "after last bullet block" helper. That helper was built for
normal bullets in arbitrary next sections; the established `Tasks` insertion policy should remain stable.

### Conversion Rules

Do not change task syntax conversion:

- Promotion still adds `- [ ] #task` and `[created::YYYY-MM-DD]` when applicable.
- Promotion still preserves existing inline properties, links, normal text, child bullets, and trailing block IDs.
- Existing checklist items that lack `#task` still normalize into proper Obsidian tasks.
- Demotion still removes the checkbox marker and standalone `#task`, preserves allowed metadata, and routes to the next
  section as implemented by the previous change.

### Cursor Behavior

Keep existing cursor behavior:

- In-place fallback returns the current replacement plan.
- Move plans put the cursor on the moved converted first line.
- The column is clamped to the final line length.
- Existing post-move centering/following behavior remains unchanged.

## Implementation Design

Edit only:

- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`

Planned changes:

1. Add a small pure helper near the Markdown section helpers:
   - `isLineInMarkdownSectionDirectBody(section, line)`
   - It should return true only when `line > section.headingLine` and `line < section.nextHeadingLine`.
   - Use `section.nextHeadingLine` rather than `section.endLine` so child headings under `Tasks` count as other
     sections.

2. Refactor the promotion branch in `getObsidianTaskToggleDocumentPlan()`:
   - Keep the early invalid-line and in-place plan logic.
   - Keep `isTopLevelDashListToggleLine(sourceLineText)` as the movement eligibility check.
   - Keep the demotion branch exactly on the current next-section path.
   - For promotion, find the original `Tasks` section with
     `findNamedMarkdownSection(lines, TASK_ROUTING_SECTION_TITLES.tasks)`.
   - If there is no `Tasks` section, return the in-place plan.
   - If the active source line is already in the direct body of `Tasks`, return the in-place plan.
   - Otherwise, continue into the existing block-removal and move-plan construction path.

3. Adjust the post-removal promotion target lookup:
   - Re-find `Tasks` in `remaining` lines with `findNamedMarkdownSection(remaining, TASK_ROUTING_SECTION_TITLES.tasks)`.
   - Use `getSectionInsertionLine(remaining, postTarget, { stopAtChildHeadings: true })`.
   - Keep `targetSection: "tasks"` metadata.

4. Leave compatibility helpers alone unless a focused cleanup is necessary:
   - `findTaskRoutingSections()` can remain exported even if promotion no longer uses its `futureWork` half.
   - `TASK_ROUTING_SECTION_TITLES.futureWork` can remain to avoid unnecessary churn.

5. Export `isLineInMarkdownSectionDirectBody` through `module.exports.helpers` if it is useful for the focused Node
   assertions.

## Validation

1. Static and diff checks:
   - `node -c /home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`
   - `git -C /home/bryan/bob diff --check -- .obsidian/plugins/task-status-cycler/main.js`
   - `git -C /home/bryan/bob status --short -- .obsidian/plugins/task-status-cycler/main.js .obsidian/hotkeys.json obsidian_vimrc.md`

2. Focused Node helper assertions with mocked Obsidian modules:
   - A top-level dash bullet under `## Future Work` promotes and moves into `## Tasks`.
   - A top-level dash bullet under an arbitrary section, with no `Future Work` heading anywhere in the note, still moves
     into `## Tasks`.
   - A top-level dash bullet before `## Tasks` moves downward into `Tasks`.
   - A top-level dash bullet after `## Tasks` moves upward into `Tasks`.
   - A top-level dash bullet under `### Future Work` nested below `## Tasks` moves into the direct `Tasks` body.
   - A top-level dash bullet already in the direct `Tasks` body promotes in place.
   - A top-level dash bullet in a note with no `Tasks` heading promotes in place.
   - Child lines remain attached to the promoted parent block after movement.
   - Existing inline properties and trailing block IDs remain preserved, and `[created::YYYY-MM-DD]` is added only when
     absent.
   - Indented, blockquoted, ordered, `+`, and `*` list items still promote in place.
   - Demotion still moves a top-level Obsidian task to the next section, preserving the previous change.

3. Manual smoke test after reloading Obsidian or toggling `task-status-cycler`:
   - In a scratch note with `## Tasks` and another section, promote a normal top-level dash bullet from the other
     section and confirm it lands in `Tasks`.
   - Repeat with no `Future Work` heading to confirm the old dependency is gone.
   - Promote a bullet already in the direct `Tasks` body and confirm it stays in place.
   - Promote a bullet under a child heading below `Tasks` and confirm it moves to the direct `Tasks` body.
   - Demote a task from `Tasks` and confirm it still moves to the next section by document order.
   - Confirm the existing `<Ctrl+Shift+]>` hotkey and Vim-normal-mode path still invoke the command.

## Risks

- The phrase "any other section" could be read as the entire subtree under a `Tasks` heading. This plan intentionally
  uses the direct `Tasks` body because the current insertion helper already treats child headings as outside the active
  task list, and because demotion can move tasks into child sections like `### Future Work`.
- The first exact `Tasks` heading remains the target. Duplicate `Tasks` headings are not given new semantics.
- Promotion insertion remains append-after-direct-content rather than append-after-last-task. That preserves existing
  behavior, but a future cleanup could make `Tasks` insertion more task-aware if the note structure demands it.
- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js` is already dirty from the previous approved
  implementation. The implementation should layer on top of those changes and avoid touching unrelated vault files.
