---
plan: sdd/tales/202606/highlights_cancelled_task_abandoned.md
---
 I believe the `bob highlights` command already checks for the reference note's task line to see if it's
complete and if so it updates the PDF file marker note status and the reference note's `status` frontmatter property to
"read". Can you help me start also checking for the cancelled status? If the cancelled status is found, the marker note
and the `status` frontmatter property should be set to "abandoned". Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
