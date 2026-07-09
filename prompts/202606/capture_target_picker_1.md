---
plan: sdd/tales/202606/capture_target_picker_1.md
---
 I want to start showing a filterable prompt for area / active project Obsidian note files when the `Capture Task` capture panel is submitted by the user without an explicit `@` file target (e.g. `@foo` at the end of the prompt causes the captured task to be added to the `~/bob/foo.md` file). This panel is triggered via a Hammerspoon keymap that is configured in my chezmoi repo. Can you help me make this change? I want you to lead the design on this one. Just make sure it looks beautiful! Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
 

### Additional Requirements

- Make sure the first and default (i.e. the file that gets chosen if the user just presses `<enter>` without typing any text or pressing `<ctrl+n>` or `<ctrl+p>` to navigate the list of files) option in this filterable list is the `~/bob/mac_inbox.md` file (which should be shown as `mac_inbox`). Also, make sure that it is clear which files are area note files compared to project note files and give the `mac_inbox` option a visual indicator / icon of some sort to mark it as the default.