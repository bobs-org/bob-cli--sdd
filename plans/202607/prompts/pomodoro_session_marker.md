---
plan: .sase/sdd/plans/202607/pomodoro_session_marker.md
---
 Yesterday, we made it so the `<ctrl+enter>` keymap and the `bob mark-next-tasks` command untransclude Obsidian block links to tasks which are contained in sub-bullets under pomodoros (in daily files) or Obsidian tasks and then strikes them out when the corresponding task is completed (for the `<ctrl+enter>` keymap) or has been found to be completed (by the `bob mark-next-tasks` command). Can you help me make it so, for the block links to tasks contained in pomodoro sub-bullets, that we always add a nice icon / emoji to the left of block links to tasks that belong to done pomodoros (we should continue to strike these out and untransclude them)?

- Also, when the `<ctrl+enter>` keymap is used to complete a pomodoro, the non-transcluded block links to tasks that get copied to the next pomodoro we create should have this icon added to the original sub-bullets (not the new ones that we create on the new pomodoro).
- Make sure that the `<ctrl+enter>` keymap and the `bob mark-next-tasks` command respect this icon and still strike out these block links once their corresponding task has been completed (leave the icon when we do this).
- I want you to lead the design on this one. Make sure you design this feature so it is intuitive, reliable, and (last but not least) beautiful!

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
  