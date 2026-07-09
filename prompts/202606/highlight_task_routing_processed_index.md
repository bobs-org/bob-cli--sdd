---
plan: sdd/tales/202606/highlight_task_routing_processed_index.md
---
 #fork:3p.f1 Can you now help me improve this functionality a bit? Namely:

- When a task line / bullet in a PDF file (that triggers a new Obsidian task creation) ends with a token (last word) that looks like `@<name>`, we should create the new Obsidian task in the `~/bob/<name>.md` file instead of in the reference note file.
- To make sure that no duplicate Obsidian tasks ever get created, we should only ever check PDFs with a corresponding status of "wip" for tasks. Also, we need to make sure that if the Obsidian tasks is later completed / canceled / moved (e.g. by the `bob move-done-tasks` command) that the `bob highlights` command still recognizes the task as processed (i.e. knows that we've already created an Obsidian task for this at some point). We should try to accomplish this without modifying the PDF in any way (e.g. don't try to edit the note to mark the `#task` line as processed).

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
