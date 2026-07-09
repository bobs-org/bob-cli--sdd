---
plan: sdd/tales/202606/reopen_prj_ref_status.md
---
 Can you help me fix the `bob projects sync` and `bob highlights scan` commands so they change the `status` frontmatter field (and corresponding PDF marker note, in the case of ref notes) of project/ref notes to “wip” when their corresponding main task (the ^prj task for projects and the ^ref task for refs) is opened back up by the user?

- We already support automatically marking projects/refs as done/canceled.
- This request is about going in the opposite direction (e.g. when a user un-cancels/un-abandons a project/ref).

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
