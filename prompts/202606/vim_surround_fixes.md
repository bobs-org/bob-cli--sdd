---
plan: sdd/tales/202606/vim_surround_fixes.md
---
 The vim-surround keymaps in the bob-plugins repo have some problems:

- The `ys` keymap always moves the cursor to the top of the file after the text operator (e.g. `2w`) is used. This causes the current line to not be visible sometimes.
- None of the vim-surround keymaps seem to support most characters (e.g. I can't surround by `?` using `ys2w?` and can't delete surrounding `*` using `ds*`).

Can you help me diagnose the root cause of and fix these issues? Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
  