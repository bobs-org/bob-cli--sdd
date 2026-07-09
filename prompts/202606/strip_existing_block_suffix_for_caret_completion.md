---
plan: sdd/tales/202606/strip_existing_block_suffix_for_caret_completion.md
---
 #fork:01p Make sure that when the `^` character is used (behavior #2) that we now also delete any existing `^foobar` suffix before inserting the `^` character (otherwise we wind up with something like `[[some_file^foobar^]]`. Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
