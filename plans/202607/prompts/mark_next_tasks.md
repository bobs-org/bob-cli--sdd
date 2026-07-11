---
plan: .sase/sdd/plans/202607/mark_next_tasks.md
---
 Can you help me create a new `bob mark-next-tasks` command?

- A "next" task is an Obsidian task with the custom "next" status. These use `[*]` instead of `[ ]`.
- This command will parese today's daily file for any block links in sub-bullets of open pomodoros that point to tasks. These tasks should be given the next status marker (i.e. convert `[ ]` to `[*]`). Any tasks which are already marked as next but are not linked to via an open pomodoro sub-bullet block link in the current daily file should have their "next" status cleared (i.e. convert `[*]` back to `[ ]`).
- Any tasks that already have an in-progress status (i.e. `[/]`) should not be changed.
- Make sure this command produces excellent, concise, and human-readable output.
- I want you to lead the design on this one. Make sure you design this feature so it is intuitive, reliable, and (last but not least) beautiful!

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
  