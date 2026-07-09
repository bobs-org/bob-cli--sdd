---
plan: sdd/tales/202606/move_done_tasks_dirty_git.md
---
 It seems like the `bob move-done-tasks` command refuses to edit files when they have existing git changes
(see the /var/tmp/bob_nightly.log file for context). This is not correct (uncommitted git changes should not even be
checked by this command). Can you help me fix this? Run the `bob move-done-tasks` command when you are done to verify
your fix. Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
