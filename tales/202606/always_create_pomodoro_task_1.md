---
create_time: 2026-06-14 10:45:53
status: wip
prompt: sdd/prompts/202606/always_create_pomodoro_task_1.md
---
# Plan: Always Create a Fresh Pomodoro Task on Completion

## Goal

Change the Obsidian Pomodoro task completion behavior so completing an open Pomodoro task always inserts a fresh
placeholder Pomodoro task directly below the completed Pomodoro's own sub-bullet block.

Today the helper reuses the first existing Pomodoro task below the current one: it only creates `- [ ] ()` when there is
no next Pomodoro in the `## Pomodoros` section. After this change, the next Pomodoro will always be a newly inserted
`- [ ] ()`, even when another Pomodoro already exists farther below.

Any non-transcluded task-link sub-bullets copied forward from the completed Pomodoro must be copied under this newly
created Pomodoro task, never under a pre-existing lower Pomodoro.

## Context Reviewed

- Read `memory/short/sase.md`: this is an ephemeral `bob-cli_<N>` workspace; be careful with commands outside the
  workspace.
- Read long-term Obsidian memory through the required audited command:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault/keymap workflow context before changing Pomodoro task behavior"`.
- Read `/home/bryan/bob/AGENTS.md`: the live vault may already be dirty; inspect status before editing; do not
  overwrite, revert, stage, or commit unrelated changes; after changing files under `~/bob`, commit only this task's
  changes via the SASE commit workflow.
- Inspected the live vault implementation: `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`.
- Reviewed the prior SASE plans:
  - `sdd/tales/202606/pomodoro_ctrl_enter_close_and_create.md`
  - `sdd/tales/202606/pomodoro_next_cursor_jump.md`
- Checked current vault status. Before this task's implementation, `.obsidian/plugins/task-status-cycler/main.js` is
  already modified with unrelated work in the task-routing helpers, and several notes/plugins are also dirty. This plan
  treats those as pre-existing changes and works on top of the current file without reverting them.

## Current Behavior

The Pomodoro completion path lives in `task-status-cycler/main.js`:

- Vim normal-mode `<C-CR>` / `<C-Enter>` are mapped to `taskStatusCyclerToggleTaskOpenDone`.
- `handleVimTaskToggleOpenDone()` detects an open Pomodoro task and routes it to `completeActivePomodoroTask()`.
- `completeActivePomodoroTask()` completes transcluded sub-bullet source tasks, recomputes the editor lines, builds a
  local edit plan with `buildPomodoroCompletionPlan()`, then applies it with `applyPomodoroCompletionPlan()`.
- `buildPomodoroCompletionPlan()` currently branches on `findNextPomodoroLine(...)`:
  - no next Pomodoro: create `- [ ] ()` after the completed Pomodoro's sub-bullets and copy eligible bullets under it;
  - existing next Pomodoro: do not create a placeholder; append non-duplicate copyable bullets under that existing next
    Pomodoro.
- `applyPomodoroCompletionPlan()` already knows how to place the cursor on `plan.cursorTargetLine`, with placeholder
  cursor placement between the parens.

The user's request changes the second branch: existing lower Pomodoros should no longer be reused as the carry-forward
target.

Note: the current live code exposes the behavior through the plugin's Vim `<C-CR>` / `<C-Enter>` mapping. The prompt
calls the user-facing keymap `<shift+enter>`; this plan changes the shared Pomodoro completion behavior and does not
need a hotkey or vimrc change unless review reveals a separate Shift+Enter binding outside the inspected plugin path.

## Product Decisions

1. The special behavior still only applies when completing an open top-level Pomodoro task inside the `## Pomodoros`
   section.
2. Reopening a done Pomodoro remains plain `[x]` to `[ ]` toggling: no new Pomodoro, no copied bullets, no transcluded
   task completion.
3. Transcluded sub-bullets keep existing behavior: resolvable open embedded task links under the completed Pomodoro are
   marked done in their source file before the local Pomodoro restructuring runs.
4. A new placeholder Pomodoro is always inserted at `sourceRange.endLine`, immediately after the current Pomodoro's
   direct indented sub-bullet block.
5. Existing Pomodoros below the current one are left untouched and pushed down by the insertion when necessary.
6. Copyable non-transcluded block-link bullets from the completed Pomodoro are copied verbatim under the newly inserted
   placeholder.
7. Because the target Pomodoro is always new and empty, the old dedupe-against-existing-next-Pomodoro behavior is not
   used for the copied bullets. This preserves the prior "created placeholder" branch semantics.
8. If there are no copyable non-transcluded task-link bullets, keep the existing created-placeholder behavior by adding
   one empty tab-indented sub-bullet line (`\t- `) under the new `- [ ] ()`.
9. After completion, the cursor should land on the newly created placeholder line, between the parens, regardless of
   whether another Pomodoro already existed below.

## Implementation Scope

Expected implementation file:

- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`

No expected edits:

- `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`
- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
- `/home/bryan/bob/.obsidian/hotkeys.json`
- `/home/bryan/bob/obsidian_vimrc.md`
- any vault notes, templates, memory files, or `bob-cli` Rust/script files

Because `task-status-cycler/main.js` is already dirty before this implementation, the edit should be minimal and should
not disturb the pre-existing task-routing diff.

## Implementation Approach

1. Update `buildPomodoroCompletionPlan(lines, section, pomodoroLine)`:
   - keep validating that the active line is an open Pomodoro task;
   - keep computing `sourceRange`, `sourceBullets`, and optionally `nextPomodoroLine` for returned metadata/debugging;
   - remove the branch that appends copied bullets to `targetRange` under `nextPomodoroLine`;
   - always set `createdPomodoro` to `true`;
   - always set `copiedBulletLines` from `sourceBullets.copyableTaskLinkBullets.map((bullet) => bullet.lineText)`;
   - always push a single `insertLines` edit at `sourceRange.endLine` containing:
     - `POMODORO_PLACEHOLDER_LINE`;
     - copied bullet lines when present, otherwise `EMPTY_POMODORO_SUB_BULLET_LINE`;
   - always set `cursorTargetLine` to `sourceRange.endLine`.
2. Leave `completeActivePomodoroTask()` and `applyPomodoroCompletionPlan()` structure intact unless a small defensive
   adjustment is needed after changing the plan shape.
3. Leave `findNextPomodoroLine()`, `getPomodoroSubBulletTargetKeys()`, and `getNonDuplicateCopyablePomodoroBullets()` in
   place unless cleanup is clearly safe; preserving exported helper shape reduces risk while this file already has
   unrelated dirty work.
4. Do not change keymap registration or command IDs; the behavior change belongs in the Pomodoro completion plan
   builder.

## Acceptance Criteria

Given:

```md
## Pomodoros

- [ ] (**0900-0925** [t:: 25m])
  - [[bob#^task-a]]
- [ ] (**0930-0955** [t:: 25m])
  - [[bob#^task-b]]
```

Completing the first Pomodoro produces:

```md
## Pomodoros

- [x] (**0900-0925** [t:: 25m])
  - [[bob#^task-a]]
- [ ] ()
  - [[bob#^task-a]]
- [ ] (**0930-0955** [t:: 25m])
  - [[bob#^task-b]]
```

Additional expected behavior:

- If the completed Pomodoro was already the last one, the output remains the same as today's created-placeholder path.
- If the completed Pomodoro has no copyable non-transcluded task-link bullets, the new placeholder gets one empty
  tab-indented `- ` sub-bullet.
- Existing lower Pomodoros do not receive copied bullets and are otherwise unchanged.
- Transcluded embedded task sub-bullets are completed in source files as before, but are not copied under the new
  Pomodoro.
- Note-only bullets are left under the completed Pomodoro and are not copied.
- The cursor lands on the newly inserted `- [ ] ()` line, between the parens.
- Non-Pomodoro task toggles, done-Pomodoro reopen toggles, transcluded sub-bullet toggles, and files without a
  `## Pomodoros` section keep current behavior.

## Verification Plan

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js
git -C /home/bryan/bob diff --check -- .obsidian/plugins/task-status-cycler/main.js
```

Focused Node helper checks with a stubbed `obsidian` module, using `module.exports.helpers`:

- `buildPomodoroCompletionPlan()` with an existing next Pomodoro returns an `insertLines` edit at the completed
  Pomodoro's `sourceRange.endLine`, with `POMODORO_PLACEHOLDER_LINE` followed by copied bullets.
- The same plan has `createdPomodoro === true` and `cursorTargetLine === sourceRange.endLine`.
- Existing lower Pomodoro lines are not used as insertion targets and receive no copied bullets.
- Last-Pomodoro behavior still creates the placeholder and copied/empty sub-bullet as before.
- `applyPomodoroCompletionPlan()` places the cursor on the inserted placeholder line between the parens.

Optional manual smoke test after plugin reload:

- In a scratch daily-style note, complete a Pomodoro that already has another Pomodoro below it and confirm a new
  placeholder is inserted between them with carried-forward bullets under the new placeholder.
- Complete a last Pomodoro and confirm unchanged placeholder creation.
- Reopen a done Pomodoro and confirm no placeholder is created.

Vault hygiene before finishing implementation:

```bash
git -C /home/bryan/bob status --short
git -C /home/bryan/bob diff -- .obsidian/plugins/task-status-cycler/main.js
```

If implementation is approved and file changes are made under `~/bob`, commit only this task's changes with the
`/sase_git_commit` workflow, leaving all unrelated dirty vault files untouched.

## Risks

- The target file is already dirty. The implementation should be a small edit inside `buildPomodoroCompletionPlan()` to
  avoid entangling this change with the pre-existing task-routing work.
- Some helper metadata currently differentiates created vs reused Pomodoros. Setting `createdPomodoro` true for every
  Pomodoro completion is intentional for the new behavior; focused helper checks should catch any stale assumption.
- If there is an uninspected separate Shift+Enter binding that bypasses the Vim `<C-CR>/<C-Enter>` path, this plan will
  need a small follow-up wiring check. The inspected live plugin path owns the current Pomodoro completion logic.
