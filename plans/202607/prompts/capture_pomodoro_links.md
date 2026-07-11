---
plan: .sase/sdd/plans/202607/capture_pomodoro_links.md
---
 Can you help me improve the `bob capture` command? Namely:

- I want to add support for a new `@!<filename>:<id>` syntax that indicates that the task should be given a custom "next" Obsidian task status (i.e. use `[*]` instead of `[ ]`) and that a block link to that task (which should be given a block ID of `<id>`) should be added to the current / next scheduled pomodoro in today's daily file.
- By "current / next scheduled pomodoro", we mean to prefer an open pomodoro which has a time range assigned to it (there should be at most one of these). If no pomodoro is currently running though, we should add the block link as a sub-bullet of the next scheduled pomodoro (i.e. the first open pomodoro in the file when scanning from the top to the bottom).
- These block links should be added as sub-bullets.
- We should also add support to the menu triggered by the `<ctrl+shift+alt+i>` keymap (defined by Hammerspoon in my chezmoi repo I believe) for accepting a syntax of `@!` or `@!<filename>`. In this case, we should prompt the user for the block ID after they submit their capture input.
- For example, if a user were to submit `Some foobar task. @!dev` as the capture input right now, then they should be prompted for a block ID for the new note. If the user than submits `foobar` for the ID, then the `- [*] Some foobar task. ^foobar` Obsidian task should be added to the ~/bob/dev.md file and the `  - [[dev#^foobar]]` sub-bullet would be added below the `  - [[bob#^pom-capture]]` sub-bullet in the ~/bob/2026/20260710.md file.

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
 