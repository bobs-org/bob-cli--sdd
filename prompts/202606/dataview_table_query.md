---
plan: sdd/tales/202606/dataview_table_query.md
---
 It doesn't seem like the TABLE query type is working with the `bob dataview` command (see below). Can you help me diagnose the root cause of this issue and fix it? Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.

```
❯ bob dataview --query '
TABLE status, parent, source_path
FROM "ref"
WHERE source_pdf
  AND (
    parent = [[ai_ref]]
    OR parent.parent = [[ai_ref]]
    OR parent.parent.parent = [[ai_ref]]
    OR parent.parent.parent.parent = [[ai_ref]]
    OR parent.parent.parent.parent.parent = [[ai_ref]]
  )
'
ref/papers/log_is_the_agent.md
ref/papers/memory_os.md
```