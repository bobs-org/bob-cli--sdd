---
plan: sdd/tales/202606/snooze_task_property.md
---
 Can you help me add support for a new `snooze` Obsidian Task property?

- This property should accept a date value.
- The query in the daily template file (and today's daily file) should be updated to only include Tasks that either do not have the `snooze` property or have the `snooze` property and the date value is greater than or equal to the current date.
- A new `bob rm-snooze` command should be created that deletes the `snooze` property from any Task in my Obsidian vault that has a date value that is greater than or equal to the current date.
- This command should then stage and commit and changed files using git and then push the commit to GitHub.
- This new command should be run from the `bob cronjob` command. Make sure to run it before the other two commands.

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
