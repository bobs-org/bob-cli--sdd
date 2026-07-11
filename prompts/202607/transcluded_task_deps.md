---
plan: .sase/sdd/plans/202607/transcluded_task_deps.md
---
 Can you help me change the way that the `!` and `<ctrl+shift+p>` keymaps work in Obsidian? In particular, I want to change the way that we handle the `dependsOn` Obsidian task property.

- We should stop adding the "DEPENDS ON" sub-bullet to tasks that have dependencies. Instead, we should add a transcluded block link to the task this task depends on. Each dependency task should have its own sub-bullet containing a transcluded block link.
- Make sure you update all of the Obsidian tasks in the ~/bob/ directory that have dependencies to use this new style.
- The `!` keymap, which toggles transclusion for block links, should be changed so when it is used on one of these lines (a sub-bullet beneith an Obsidian task that contains only a block link to another Obsidian task) it automatically adds/removes the corresponding `dependsOn` property to this task. Also, in the case the `!` keymap adds the `!` (transcludes the block link), we should set the `id` property on the linked to task if it does not already have that property (a block ID should already be defined).
- The `bob mark-next-tasks` command should be updated to search for transcluded block links to other tasks (recursively) and, when found, should give these tasks a "next" (i.e. `[*]`) status too (assuming the parent / dependent task is linked to by a pomodoro note in today's daily file--or that it has an ancestor/dependant that is).

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
 