---
create_time: 2026-07-11 08:00:44
status: done
prompt: .sase/sdd/plans/202607/prompts/ctrl_enter_next_status.md
tier: tale
---
# Fix Ctrl+Enter completion for Next tasks

## Context and root cause

The `task-status-cycler` plugin owns the Vim-normal-mode `<C-CR>` / `<C-Enter>` mappings. Both mappings dispatch to the
plugin's direct open/done toggle. That path parses `[*]` correctly, but its eligibility predicate only accepts Todo
(`[ ]`) and Done (`[x]`), and its transition helper only knows how to switch those two symbols. As a result, a Next task
falls through to unrelated transclusion/Pomodoro handling and an ordinary local `[*]` task is left unchanged.

This is a regression gap from the recent migration of the custom Blocked status to the Next status. The migration added
`*` to the general cycle, and a later fix taught one Pomodoro start path about Next tasks, but the direct Ctrl+Enter
open/done path was not updated. The live Obsidian Tasks configuration defines `[*]` as `Next` and its next status as
`x`, confirming that Ctrl+Enter should complete it as `[x]`.

## Implementation

1. Update the direct open/done status policy in `plugins/task-status-cycler/main.js` so Todo and Next are both treated
   as open states for this command: `[ ] -> [x]`, `[*] -> [x]`, and `[x] -> [ ]`. Keep In Progress (`[/]`) and Canceled
   (`[-]`) outside this direct toggle so their existing Pomodoro-specific and cancellation behavior does not broaden
   accidentally.
2. Exercise the existing Tasks-command/local-fallback write path rather than introducing a special-case edit. This
   preserves Tasks-managed completion metadata for `#task` lines and keeps the same behavior for local and transcluded
   direct toggles.
3. Add focused regression coverage for the `task-status-cycler` plugin, including the status transition truth table and
   the actual Vim Ctrl+Enter handler dispatching a Next task to the Tasks `set-status-symbol-to-x` command. Wire the new
   test file into the repository's test script without disturbing the existing navigation-hotkeys tests.
4. Run the complete plugin unit test suite and manifest validation. Confirm the existing Todo/Done behavior remains
   intact and the new Next case passes.
5. Deploy the source-of-truth plugin changes to the Obsidian vault with `bob plugins sync`, as required by the linked
   repository, and verify the deployed `task-status-cycler` source matches the tested source.

## Expected outcome

In Vim normal mode, pressing Ctrl+Enter on an ordinary `[*] #task ...` line marks it Done (`[x]`) through the same
metadata-aware path already used for Todo tasks. Pressing Ctrl+Enter on Done still reopens it as Todo, while In
Progress, Canceled, task cycling, and specialized Pomodoro completion/start flows retain their current semantics.
