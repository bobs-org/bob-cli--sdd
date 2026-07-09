---
plan: sdd/epics/202606/bob_projects_command.md
---
 #fork:bob-cli-6  Can you now help me create a new `bob projects` command?

- To support this new command, the `~/bob/_templates/new_project.md` template should be updated to included a task at
  the top of the file that looks like this:

  ```
  - [ ] #task <short_project_completion_criteria_goes_here> [p::2] ^prj
  ```

- This task should be used by the `bob projects` command in the same way that the `^task` task currently is in `[[ref]]`
  note files (i.e. note files with the `type: [[ref]]` frohtmatter property) by the `bob highlihgts` command. Namely, if
  the user marks this task as done, the project's `status` frontmatter property should be updated to `done` / `canceled`
  (depending on whether the task was marked done or canceled).
- This command should also look for any project note files that do not contain any tasks that do NOT have the `p`
  property (this indicates that the task should be treated as having P0 priority). For these projects, the `^prj` task
  should have the `[scheduled::YYYY-mm-dd]` property added to it (where `YYYY-mm-dd` should be replaced with the current
  date in that format).
- To limit the number of project files that we need to migrate (see the next bullet), we should delete the `type`
  property of any project note file that seems to be obsolete / legacy. This should be any project note file that does
  not have any open Obsidian tasks in it.
- You should add one of these tasks to the top of every existing project file (if necessary--which it should be for most
  of them I think).
- Make sure this command has great, informative, and concise output. I want you to lead the design on this one. Just make sure it looks beautiful!

This is a large piece of work that should be split into phases. I'll let you decide how many phases to create, but
keep in mind that each phase will be completed by a distinct agent instance (i.e. a distinct `claude` / `gemini` /
`codex` / `qwen` / `opencode` command). Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.

