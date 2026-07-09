---
create_time: 2026-06-03 11:33:25
status: done
prompt: sdd/prompts/202606/hammerspoon_task_capture.md
---
# Fix Hammerspoon Task Capture Nested-Content Insertion

## Context

The `cmd+ctrl+shift+i` Hammerspoon binding in `/home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua` opens a
task capture prompt. Routed captures such as `@work ...` are written to `~/bob/<route>.md`, where `~/bob` is the
Obsidian vault.

The bug is in `insertTaskAfterLastOpenTask()`. It scans the target Markdown file and remembers the insertion point as
the byte immediately after the last top-level open `#task` line. If that task has nested Markdown content below it, the
new task is inserted between the task line and its indented children. Markdown then associates those children with the
new task rather than with the original task.

## Goal

When inserting a routed captured task after the last open task in a target file, keep any nested or continuation content
attached to the original task. The new task should be inserted after the previous task's full Markdown list-item block.

## Plan

1. Preserve the existing capture UI, routing syntax, notification behavior, file creation behavior, and default
   `mac_inbox.md` append behavior.

2. Replace the current "insert after matching line" behavior in `insertTaskAfterLastOpenTask()` with a small Markdown
   block scan:
   - Continue to identify candidate routed-task anchors as top-level lines matching the existing open-task `#task`
     pattern.
   - For each candidate, compute the end of that task's block by consuming following lines that are indented relative to
     the top-level task line.
   - Treat those indented lines as belonging to the original task, including nested unordered lists and continuation
     text.
   - Stop the block before the next non-indented top-level line, so the insertion point remains before unrelated
     following content.

3. Keep newline handling stable:
   - If the target task is already followed by a newline, insert at the start of the next top-level block.
   - If the file does not end with a newline, add the needed separator so the new task starts on its own line.
   - Preserve the existing fallback behavior for files with no matching open task: append to the end.

4. Add focused verification around the insertion algorithm. Since the Hammerspoon file is not structured as a Lua module
   and Hammerspoon is not installed in this environment, use a local Lua 5.1 harness or temporary extracted snippet to
   validate the behavior without executing Hammerspoon APIs.

5. Verify at least these cases:
   - Empty target file appends the new task.
   - Target with no matching open task appends the new task.
   - Last matching task with no nested content inserts immediately after that task.
   - Last matching task with an indented unordered list inserts after the nested list.
   - Last matching task without a trailing newline still produces valid line separation.
   - Earlier matching task with nested content is ignored when a later matching task exists.

6. After implementation, review the diff in the chezmoi repo and avoid modifying the live `~/.hammerspoon/init.lua`
   directly unless explicitly requested. The managed chezmoi source should be the source of truth.
