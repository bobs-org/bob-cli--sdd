---
plan: .sase/sdd/tales/202607/preserve_prj_hide_on_schedule.md
---
 Yesterday we added support to the `bob projects` command for a new property named `scheduled` that can be added to the frontmatter of a project note file. If the scheduled date is on today or before today, we remove the `#hide` tag from all Obsidian tasks in that project note file. This is correct but we made one mistake. Namely, we shouldn't remove the `#hide` tag from the `^prj` note file (that represents the definition of done for the project) unless it is the only Obsidian task in that project note file. Can you help me fix this? Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
 