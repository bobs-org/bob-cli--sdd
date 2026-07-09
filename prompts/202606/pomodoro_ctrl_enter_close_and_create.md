---
plan: sdd/tales/202606/pomodoro_ctrl_enter_close_and_create.md
---
 I currently define a Pomodoro task in my Obsidian daily files for each time block where I intend to work on
something. Each of these tasks contains sub-bullets that are expected to be of one of the following forms:

- A note about a task that I am doing that is untracked elsewhere.
- A link to a block ID for an Obsidian task in another file
- A transcluded (i.e. a `!` is prepended) link to a block ID for an Obsidian task in another file.

Can you help me improve the existing `<ctrl+enter>` keymap by adding special support / functionality for Pomodoro
tasks?:

- Any transcluded task under the current Pomodoro task should be marked as done (as if the `<ctrl+enter>` keymap had
  been used on each of the transcluded task sub-bullet lines).
- The Pomodoro task should also be marked as complete (the normal behavior of `<ctrl+enter>`).
- If this is the last Pomodoro task in the file, then a new Pomodoro task line should be added below the current one
  with the following first line `- [ ] ()`.
- This new Pomodoro task (or the very next existing one, if some existed below the Pomodoro task we are marking as done)
  should have all of the non-transcluded task link bullets from the current Pomodoro task copied to it (as sub-bullets).
  If we had to create a new Pomodoro task and there are no such sub-bullets to copy over a single empty sub-bullet
  should be added below this new Pomodoro task (i.e. a line containing just ` -` should be added below the Pomodoro
  task).
- Any non-transcluded task link bullet
- This functionality will only apply to marking Pomodoro tasks as done (nothing special happens when re-opening them).

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
