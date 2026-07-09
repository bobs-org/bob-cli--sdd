---
plan: sdd/tales/202606/hammerspoon_capture_trailing_at_picker.md
---
 #fork:8q.f1 This looks great! But can you now help me go back to the old behavior for the `foo bar baz` case and only show the new area/project file prompt when the user input ends in ` @`?

- So, for example, `foo bar baz @` would trigger the area/project file prompt, whereas `foo bar baz` would not.
- Make sure we strip the ` @` from the task that we create.
- This also means that we should stop showing `mac_inbox` in the area/project prompt. Users can just press `<enter>` instead of ` @<enter>` if they want to store the new task in the `~/bob/mac_inbox.md` file.

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
