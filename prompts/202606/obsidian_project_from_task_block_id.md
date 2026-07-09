---
plan: sdd/tales/202606/obsidian_project_from_task_block_id.md
---
 #fork:5o Can you now help me make it so, if the original task was in the `~/bob/fake_project.md` file and
had a `^foo-bar-baz` block ID (which shouldn't be copied to the new `^prj` task, since that would result in two block
IDs on a single task), that we automatically name the project file `~/bob/fake_project_foo_bar_baz.md` (note that we
merged the old filename with the block ID and replaced the dashes with underscores) and update any Obsidian block links
that targeted that task using that block ID to `[[fake_project_foo_bar_baz]]`?

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
 