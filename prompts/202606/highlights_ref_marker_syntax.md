---
plan: sdd/tales/202606/highlights_ref_marker_syntax.md
---
 The `bob highlights-ref scan` command currently updates the marker note on PDF files in cases where it
shouldn't. For example, consider the below marker note:

```
- status: wip
- parent: memory_ref
- title: The Log is the Agent
```

This was just updated (on another machine) to the following:

```
- status: wip
- parent: [[memory_ref]]
- title: "The Log is the Agent"
```

Can you help me diagnose the root cause of this issue and fix it? Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.


### Additional Requirements

- Also, make sure that the marker file only supports the former syntax (the latter should result in an error).