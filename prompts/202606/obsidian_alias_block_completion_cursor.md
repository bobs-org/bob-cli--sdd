---
plan: sdd/tales/202606/obsidian_alias_block_completion_cursor.md
---
 Obsidian currently always auto-converts `[[path/to/foobar]]` to `[[path/to/foobar|foobar]]` when I accept a
completion (e.g. I pressed `<enter>` when the path/to/foobar.md file was selected after typing `[[` to trigger the
completion menu). This makes it more keypresses than I'd like to get my cursor back to the column before the `|`
character (e.g. in order to press `^` to trigger completion for blocks in the path/to/foobar.md file). We already
trigger a popup to change the block name when the user presses `^` after the last `]` character if the link targets a
block. Can you help me add a new behavior to this functionality that jumps the cursor (after deleting the `^`) to before
the `|` character? This way I would just have the hit `^` again to trigger the block completion menu.

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
