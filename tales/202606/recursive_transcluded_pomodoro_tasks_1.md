---
create_time: 2026-06-20 13:31:16
status: proposed
prompt: sdd/prompts/202606/recursive_transcluded_pomodoro_tasks_1.md
---

# Plan: Recursive Transcluded Task Completion for Pomodoro `<Ctrl+Enter>`

## Goal

Extend the `task-status-cycler` Pomodoro completion flow so pressing `<Ctrl+Enter>` on an open Pomodoro task closes the
entire embedded transclusion task tree, not only the immediate embedded block links under the current Pomodoro.

The source of truth for this change is the `bob-plugins` repo:

`/home/bryan/.local/state/sase/workspaces/bobs-org/bob-plugins/bob-plugins_13/plugins/task-status-cycler/main.js`

Do not edit the deployed vault plugin files under `~/bob/.obsidian/plugins/`. Deployment to the vault, if needed after
implementation, should be done through `bob plugins sync`, not by treating `~/bob` as source.

## Context Reviewed

- Read long-term Obsidian memory with:
  `sase memory read obsidian.md --reason "Need Obsidian vault and plugin workflow context before planning recursive task closure behavior"`.
- Reviewed `bob-plugins` README, which confirms:
  - `bob-plugins` is the source-of-truth monorepo for Bryan-authored Obsidian plugins.
  - `plugins/<id>/main.js` is direct CommonJS source, not generated output.
  - vault copies under `~/bob/.obsidian/plugins/<id>/` are deploy targets.
- Inspected `task-status-cycler/main.js` in the clean `bob-plugins_13` checkout.
- `bob-plugins_10` has unrelated dirty Vim-surround changes, while `bob-plugins_12` and `_13` are clean and at the same
  commit. Use `_13` for this task unless SASE checkout ownership says otherwise.
- No `bob-cli` subcommands or options are being added, so `memory/cli_rules.md` is not required.

## Current State

The relevant flow is in `plugins/task-status-cycler/main.js`:

- Vim maps `<C-CR>` and `<C-Enter>` to `taskStatusCyclerToggleTaskOpenDone`.
- `handleVimTaskToggleOpenDone()` routes an open Pomodoro task to `completeActivePomodoroTask()`.
- `completeActivePomodoroTask()`:
  1. reads the current editor lines;
  2. finds the current Pomodoro's indented sub-bullet block;
  3. classifies embedded block transclusions with `classifyPomodoroSubBullets()`;
  4. calls `completePomodoroTranscludedTaskBullets()` for those embedded targets;
  5. rereads the editor;
  6. builds and applies the local Pomodoro completion plan.
- `completePomodoroTranscludedTaskBullets()` currently loops only immediate embedded targets.
- `completeTranscludedTaskTarget()` resolves one target and forces it to done only when the resolved source task is
  open.
- `resolveTranscludedBlockTarget()` already resolves a block target via metadata cache with source-text fallback.
- `replaceResolvedTranscludedTaskLine()` already revalidates the target line before writing and preserves the existing
  task completion-field semantics.

Important design hazard:

The current transclusion helpers pass one `sourcePath` through resolution, active-buffer reads, and write routing. That
works for first-level links from the active daily note. Recursion needs two distinct concepts:

- `originPath`: the note whose links should be used as the base for resolving `[[relative]]` and `[[#^same-file]]`.
- `activePath`: the currently open editor file, used only to decide whether to read/write through `editor` instead of
  vault I/O.

Without that split, a child link like `![[#^child]]` inside an external source note could resolve against the active
daily note instead of the external note, or an external note could be incorrectly treated as the active editor.

## Product Decisions

1. Recursion follows embedded block transclusions only.
   - Follow `![[note#^id]]` and `![[#^id]]`.
   - Do not follow plain `[[note#^id]]` links.
   - This preserves the current Pomodoro distinction: embedded links mean "close this source task now"; plain links are
     copyable carry-forward context.

2. Recursion is forced-done, not toggle.
   - Open source tasks become done.
   - Already-done source tasks stay done.
   - Other task statuses such as `[/]`, `[-]`, and non-task block targets are skipped.

3. Done parents should still be traversed.
   - If a target task is already done, do not rewrite it, but still inspect its child bullets for embedded transcluded
     task links.
   - This avoids an already-closed intermediate task hiding open descendant work.

4. Child discovery is limited to the resolved task's list-item block.
   - Start from the resolved task line in its source text.
   - Use the existing `getListItemBlockRange(lines, taskLine)` boundary, which stops at blanks, headings, and sibling or
     shallower indentation.
   - Scan only descendant list-item lines inside that block for embedded block transclusions.

5. The operation should be best-effort and cycle-safe.
   - A broken link, missing file, stale metadata cache, non-task target, or failed write should not block Pomodoro
     completion.
   - Track seen targets by resolved file path plus block ID, for example `path/to/file.md#^block-id`.
   - Add a conservative target/depth guard so cycles like A -> B -> A and large accidental graphs terminate.

6. Keep local Pomodoro restructuring unchanged.
   - The active Pomodoro line completion, placeholder creation, carry-forward copying, duplicate suppression, cursor
     placement, and centering should behave as they do today.
   - Recursive source closure should continue to happen before the active editor is reread and the Pomodoro completion
     plan is built.

7. Keep direct transcluded-line `<Ctrl+Enter>` non-recursive.
   - Pressing `<Ctrl+Enter>` directly on a single embedded line should continue to toggle only that source task.
   - The recursive behavior applies to the Pomodoro forced-done path only.

## Implementation Approach

1. Work in the clean `bob-plugins_13` checkout.
   - Re-check `git status` before editing.
   - Do not edit `~/bob/.obsidian/plugins/task-status-cycler/main.js`.

2. Split transclusion context.
   - Introduce a small context object or explicit parameters containing `editor`, `activePath`, and `originPath`.
   - Update `resolveTranscludedBlockTarget()` / `resolveTranscludedTargetFile()` to resolve links relative to
     `originPath`.
   - Update `readTranscludedTargetSourceText()` and `replaceResolvedTranscludedTaskLine()` so active-buffer reads/writes
     compare target files against `activePath`.
   - Preserve the existing direct toggle by passing the active file path as both `activePath` and `originPath` from
     `toggleActiveTranscludedTaskOpenDone()`.

3. Add a reusable child-transclusion collector.
   - Convert a resolved target's source text to line texts using `splitTextByLineEndings()`.
   - Get the resolved task's block with `getListItemBlockRange()`.
   - Scan descendant list-item lines for `parseEmbeddedBlockTransclusions()`.
   - Return target records compatible with the current Pomodoro target loop, or add a focused helper such as
     `collectEmbeddedTranscludedTaskTargetsInListItemBlock(sourceText, taskLine)`.
   - Export the pure helper through `module.exports.helpers` if useful for focused Node checks.

4. Add recursive forced-done orchestration.
   - Add a helper like `completeTranscludedTaskTargetTree(candidate, context)`.
   - Resolve the candidate relative to `context.originPath`.
   - Build a canonical seen key from `resolvedTarget.file.path` and `resolvedTarget.blockId`.
   - Read the current source text for the resolved target.
   - If the resolved target is an open or done task, collect child embedded transclusions from its descendant list-item
     block.
   - Recurse into each child with `originPath` set to the resolved target file path and the same `activePath`.
   - After child traversal, force the resolved target itself to done only if its current task status is open, using the
     existing replacement path and its final line revalidation.

5. Wire recursion into the Pomodoro path only.
   - Change `completePomodoroTranscludedTaskBullets()` to create one recursion context for the Pomodoro operation and
     call the recursive forced-done helper for each immediate embedded target.
   - Keep `completeActivePomodoroTask()` ordering the same: close source targets, reread the editor, build the local
     Pomodoro completion plan, apply it.
   - Leave `toggleActiveTranscludedTaskOpenDone()` as a single-target toggle.

6. Keep errors contained.
   - Catch errors per branch or per target and continue processing siblings.
   - Avoid user-facing notices unless the implementation finds an existing debug/reporting path that fits.

## Acceptance Criteria

- A Pomodoro with `- ![[project#^a]]`, where task `^a` has a child bullet `- ![[project#^b]]`, marks both `^a` and `^b`
  done when `<Ctrl+Enter>` is pressed on the Pomodoro.
- Multi-level chains such as A -> B -> C mark every open task in the chain done.
- An already-done parent with an open embedded child leaves the parent done and closes the child.
- Cycles and duplicate links terminate without repeated writes.
- Same-file child links inside external notes, such as `![[#^child]]`, resolve relative to the external note.
- Plain non-embedded block links such as `[[note#^id]]` are not recursively closed.
- Non-task blocks, unresolved links, and non-open/done statuses are skipped without aborting Pomodoro completion.
- Existing Pomodoro behavior is unchanged for active line completion, next placeholder creation, carry-forward bullets,
  deduping, cursor placement, and centering.
- Direct `<Ctrl+Enter>` on a transcluded line still toggles only that one source task.
- No source changes are made under `~/bob/.obsidian/plugins/`.

## Verification Plan

Static checks:

```bash
npm run validate
node --check plugins/task-status-cycler/main.js
git diff --check -- plugins/task-status-cycler/main.js
```

Focused Node checks using `module.exports.helpers` and a stubbed Obsidian module:

- Child collector finds embedded transclusions on direct and nested descendant bullet lines.
- Child collector stops at blank lines, headings, and sibling or shallower list items.
- Recursive completion closes A -> B -> C.
- Duplicate links to the same `file#^block-id` are processed once.
- A -> B -> A cycles terminate.
- Same-file child links inside an external source file resolve against that source file.
- Already-done parent with open child closes the child without rewriting the parent.
- Direct single-line transcluded toggle remains non-recursive.
- Existing `buildPomodoroCompletionPlan()` behavior remains stable.

Manual smoke test after deployment through `bob plugins sync -p task-status-cycler` and Obsidian plugin reload:

1. Create scratch daily-style and source notes.
2. Add a Pomodoro with an embedded source task whose child bullets embed one or more other task blocks.
3. Press `<Ctrl+Enter>` on the Pomodoro.
4. Confirm all open source tasks in the embedded tree are done with existing completion-field and block-ID semantics.
5. Confirm next Pomodoro/carry-forward/cursor behavior matches the current non-recursive flow.
6. Repeat with a same-file child link in an external source note and with a deliberate cycle.

## Risks and Mitigations

- Same-file link resolution is the most likely regression. Mitigate by separating `originPath` and `activePath` and
  testing external-note `![[#^child]]` links.
- Metadata cache positions can be stale. Preserve the existing source-text fallback and final line/block-ID revalidation
  before every write.
- Recursive writes could touch multiple files. Keep the algorithm best-effort, cycle-safe, and limited to embedded block
  transclusions under resolved task list-item blocks.
- The repo currently has no formal test runner for plugin behavior. Use `npm run validate`, `node --check`, and focused
  ad hoc Node checks with exported pure helpers.
