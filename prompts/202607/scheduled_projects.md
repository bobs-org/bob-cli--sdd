---
plan: .sase/sdd/tales/202607/scheduled_projects.md
---
 Can you help me improve the `bob projects` command?

- We should start checking for a new `scheduled` frontmatter property on project note files.
- If set, this property should use a date value of the form YYYY-mm-dd.
- When found, what the `bob projects` command does should depend on whether the date is in the future (i.e. tomorrow or later) or not. If so, we should add the `#hide` tag to every Obsidian task in that project file. Otherwise, we should remove the `#hide` tag from every Obsidian task in that file.
- When the `<ctrl+shift+opt+n>` keymap is used to create a new project note file from the currently selected Obsidian task, if the task has a `scheduled` dataview property, we should remove it from the ^prj note we create and instead use this value for the new project note file's `scheduled` frontmatter property.
- When the `<ctrl+=>` Obsidian keymap is used, we should start showing which project note files are scheduled for the future somehow using a visual indicator. I want you to lead the design on this one. Just make sure it looks beautiful!

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
 