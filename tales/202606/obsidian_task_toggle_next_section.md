---
title: Obsidian Task Toggle Next-Section Routing
create_time: 2026-06-19 07:51:28
status: done
prompt: sdd/prompts/202606/obsidian_task_toggle_next_section.md
---

# Plan: Move Demoted Obsidian Tasks to the Next Section

## Context

The existing `<Ctrl+Shift+]>` behavior lives in Bryan's live Obsidian vault plugin, not in the Rust CLI workspace:

- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`
- `/home/bryan/bob/.obsidian/hotkeys.json`

The hotkey is already registered as `task-status-cycler:toggle-obsidian-task` with `Ctrl+Shift+]`, so this change should
not touch key registration. The active command path is:

1. `handleToggleObsidianTaskCommand()` calls `getActiveObsidianTaskToggle()`.
2. `getActiveObsidianTaskToggle()` calls `getObsidianTaskToggleDocumentPlan()`.
3. The planner converts the active line through `getObsidianTaskToggle()`.
4. If the active source line is a routing-eligible top-level dash item and both `Tasks` and `Future Work` sections are
   present, the planner returns a move plan.
5. The editor path applies either an in-place replacement or the move plan, then follows the cursor to the moved line.

The current move logic is name-based:

- demoting a proper Obsidian task into a normal bullet targets `Future Work`;
- promoting a bullet/checklist item into a proper Obsidian task targets `Tasks`;
- if the named sections are missing, the conversion falls back to the existing in-place rewrite.

The requested change is specifically about the demotion side: after converting an Obsidian task to a normal bullet, move
that bullet to the next section in the file instead of looking for a section named `Future Work`.

Assumption for this plan: the bullet-to-task promotion behavior is out of scope and should remain as close as possible
to today's behavior. The implementation should change the demoted-task routing target without changing hotkeys, command
IDs, Vim mappings, promotion syntax, property preservation, cursor following, or the top-level dash routing guard.

## Goal

When `<Ctrl+Shift+]>` is used on a routing-eligible top-level Obsidian task:

1. Convert the task line to a normal bullet using the existing demotion helper.
2. Move the converted bullet block to the next Markdown section after the source item.
3. Insert it after the last existing top-level bullet in that target section.
4. If the target section has no bullets yet, insert it as the first bullet after one blank line below the heading.
5. If there is no next section, keep the current in-place demotion fallback.

This is same-file routing only. It should not create headings, rename headings, modify other notes, or alter any hotkey
configuration.

## Behavior Specification

### Routing Eligibility

Keep the existing movement guard:

- Only top-level dash list lines route between sections.
- Indented tasks, blockquoted tasks, alternate bullet markers, and ordered-list items still convert in place.
- Non-list/non-task lines remain no-ops.

This preserves the previous safety rule that prevents nested child tasks from being pulled out of their local context.

### Next Section Detection

Use Markdown ATX headings outside YAML frontmatter and fenced code blocks, reusing the current heading parser behavior.

For a demoted source item:

- First determine the source list-item block with the existing `getListItemBlockRange()` behavior.
- Remove that block from a copy of the document.
- Starting at the removal position, find the first heading that follows the source block in document order.
- That heading is the target section.
- If no heading follows the source block, return the existing in-place replacement plan.

This treats any following heading level as the next section. For example, from a task under `## Tasks`, the next section
could be `### Future Work`, `## Project Notes`, or any other heading that appears next in the file.

### Target Section Boundaries

For insertion purposes, the target section's direct body runs from the target heading to the next Markdown heading of
any depth, or EOF.

This keeps the moved bullet in the selected section itself rather than appending it into a nested subsection that
appears later.

### Target Insertion Point

Within the target section's direct body:

- Find the last top-level bullet/checklist block.
- Insert the moved bullet after that whole block, including any child lines that belong to that bullet.
- If there are no top-level bullets/checklist items in the section, insert the moved bullet as the first bullet:
  - ensure exactly one blank line between the heading and the inserted bullet;
  - avoid creating duplicate blank lines when the heading already has one.

The moved block should preserve its existing child/continuation lines and relative indentation. Only the first line is
rewritten from task syntax to bullet syntax by the existing demotion helper.

### Conversion Rules

Do not change the task syntax rules:

- Demotion still removes the checkbox marker and standalone `#task`.
- Demotion still preserves inline properties, links, normal text, child bullets, and trailing block IDs according to the
  current plugin behavior.
- Promotion still adds `- [ ] #task` and `[created::YYYY-MM-DD]` when applicable.
- Cursor column calculation still uses `getObsidianTaskToggleCursorCh()`.

### Cursor Behavior

For in-place fallback, keep today's cursor behavior.

For a move plan:

- Put the cursor on the moved converted first line.
- Clamp the column to the final line length.
- Keep the existing post-move centering/following behavior.

## Implementation Design

Edit only:

- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`

1. Add small generic section helpers near the existing heading and insertion helpers:
   - `findNextMarkdownSection(lines, startLine)`
   - `getDirectMarkdownSection(lines, headingLine)` or equivalent section-boundary helper
   - `isTopLevelBulletLikeLine(lineText)` for target-section bullet detection
   - `getTopLevelListItemBlockEnd(lines, startLine, sectionEndLine)` for inserting after a whole existing bullet block

2. Add a target insertion helper for the new rule:
   - `getNextSectionBulletInsertion(lines, section)`
   - It returns `{ insertLine, leadingBlank }` or a richer equivalent.
   - It should append after the last top-level bullet block when one exists.
   - It should insert one blank line after the heading when this will be the section's first bullet.

3. Refactor `getObsidianTaskToggleDocumentPlan()` conservatively:
   - Keep the early invalid-line and in-place plan logic.
   - Keep `isTopLevelDashListToggleLine(sourceLineText)` as the movement eligibility check.
   - If the source line is a proper Obsidian task, build a next-section move plan instead of targeting
     `sections.futureWork`.
   - If no next section exists, return the in-place plan.
   - Leave the promotion path behavior unchanged unless the existing code shape makes a tiny extraction necessary.

4. Keep `applyObsidianTaskReplacePlan()`, `applyObsidianTaskMovePlan()`, command registration, `manifest.json`,
   `.obsidian/hotkeys.json`, and `obsidian_vimrc.md` unchanged.

5. Export new pure helpers through `module.exports.helpers` only when useful for focused Node assertions.

## Validation

1. Static and diff checks:
   - `node -c /home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`
   - `git -C /home/bryan/bob diff --check -- .obsidian/plugins/task-status-cycler/main.js`
   - `git -C /home/bryan/bob status --short -- .obsidian/plugins/task-status-cycler/main.js .obsidian/hotkeys.json obsidian_vimrc.md`

2. Focused Node helper assertions with mocked Obsidian modules:
   - A top-level task under `## Tasks` demotes and moves to the first following heading, regardless of that heading's
     title.
   - A task before `### Follow Up` moves into `### Follow Up`, proving the target is the next heading by document order.
   - A task before `## Notes` moves into `## Notes` when that is the next heading.
   - A task with no following heading demotes in place.
   - A target section with existing bullets receives the moved bullet after the last bullet block.
   - A target section with no bullets receives the moved bullet after exactly one blank line below the heading.
   - Existing child bullets move with the demoted parent task.
   - Indented tasks, blockquoted tasks, alternate bullets, and ordered-list tasks still demote in place.
   - Demotion still preserves inline properties and trailing block IDs.
   - Existing bullet-to-task promotion behavior still passes at least one representative helper check.

3. Manual smoke test after reloading Obsidian or toggling `task-status-cycler`:
   - In a scratch note, demote a top-level task in one section and confirm the resulting bullet appears in the next
     section by document order.
   - Repeat where the next section has no bullets yet; confirm the inserted bullet is separated from the heading by one
     blank line.
   - Repeat where the next section has existing bullets and child bullets; confirm insertion lands after the last bullet
     block.
   - Repeat at the end of a file with no following heading; confirm only in-place conversion happens.
   - Confirm the existing `<Ctrl+Shift+]>` hotkey and Vim-normal-mode path still invoke the command.

## Risks

- "Next section" can mean different heading-level policies. This plan uses the next heading in document order, any
  depth, because that matches the wording and handles the current nested `### Future Work` layout naturally.
- Inserting the first bullet near the heading can place it before existing prose in a section that has prose but no
  bullets. That is intentional under the requested "first bullet in that section" rule, but it should be covered in
  manual review.
- The old `Future Work` logic was symmetric with promotion-to-`Tasks`; this plan changes only demotion routing. If the
  desired behavior is to remove promotion routing too, that should be a separate explicit adjustment before
  implementation.
- The vault currently has an unrelated dirty `obsidian_vimrc.md` change. The implementation should ignore it and keep
  the final plugin diff scoped to `task-status-cycler/main.js`.
