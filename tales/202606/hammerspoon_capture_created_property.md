---
create_time: 2026-06-04 18:04:09
status: done
prompt: sdd/prompts/202606/hammerspoon_capture_created_property.md
---
# Hammerspoon Capture Created Property Plan

## Context

The `cmd+ctrl+shift+i` Hammerspoon capture binding is defined in
`/home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua`. The live `/home/bryan/.hammerspoon/init.lua` currently
matches the managed chezmoi file, but the managed chezmoi source should remain the primary edit target.

The existing capture workflow normalizes the prompt text, optionally strips an `@route` prefix or suffix, then builds
task lines with:

```text
- [ ] #task <captured text>
```

The recently-added Obsidian `ta` snippet expands to a task carrying the created Dataview inline field:

```text
#task  [created::YYYY-MM-DD]
```

For Hammerspoon captures, the equivalent completed line should put the same property at the end of the generated task
line:

```text
- [ ] #task <captured text> [created::YYYY-MM-DD]
```

The date should be computed from the local date at capture time, matching the Obsidian snippet's local-date behavior.

## Goal

Make every task created by the Hammerspoon capture key map include the same `[created::YYYY-MM-DD]` property at the end
of the task line, without changing the capture UI, routing syntax, insertion behavior, or notification text.

## Implementation Plan

1. Keep the edit scoped to the Hammerspoon task-capture code in
   `/home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua`.
   - Do not modify Bob vault notes.
   - Do not modify the Obsidian plugin again.
   - Do not modify memory files.

2. Add a small date/property formatting helper near the capture helpers.
   - Use local time via Lua/Hammerspoon date facilities, effectively `YYYY-MM-DD`.
   - Format the field exactly as `[created::YYYY-MM-DD]`, with no space after `::`, matching the implemented `ta`
     snippet.
   - Prefer a helper that can accept an optional timestamp so a Lua harness can test the formatting deterministically.

3. Centralize generated task-line construction.
   - Replace the inline string concatenation in `appendCapturedTask()` with a helper such as
     `capturedTaskLine(taskText, now)`.
   - Have that helper produce: `- [ ] #task <taskText> [created::YYYY-MM-DD]`.
   - Place the created property after the parsed capture text, not before it, so `@work call Alice` and
     `call Alice @work` both generate the same task body: `#task call Alice [created::YYYY-MM-DD]`.

4. Preserve existing behavior around storage and insertion.
   - Routed captures should continue to call `insertTaskAfterLastOpenTask()`.
   - Unrouted captures should continue to append to `~/bob/mac_inbox.md`.
   - The existing Markdown block insertion logic should not need changes, because generated lines still contain `#task`
     and remain top-level task list items.
   - Notifications should continue to show only the human capture text, not the appended metadata.

5. Verification.
   - Run `luac -p /home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua` if `luac` is available, or the closest
     available Lua parse check.
   - Run a focused Lua 5.1 harness around the capture helpers to verify:
     - a fixed local date formats as `[created::2026-06-04]`;
     - `capturedTaskLine("call Alice", fixedTime)` returns `- [ ] #task call Alice [created::2026-06-04]`;
     - `@work call Alice` routes to `work.md` while keeping the generated task body as
       `call Alice [created::2026-06-04]`;
     - `call Alice @work` behaves the same as the prefix route;
     - an unrouted capture appends the same created property to the inbox line;
     - routed insertion still inserts after the previous task block and keeps nested content attached to the previous
       task.
   - Review `git -C /home/bryan/.local/share/chezmoi diff -- home/dot_hammerspoon/init.lua`.

6. Deployment handling after implementation.
   - If the managed source and live `~/.hammerspoon/init.lua` are still in sync apart from this intended change, apply
     through chezmoi so the live Hammerspoon config receives the same update.
   - Do not directly hand-edit `~/.hammerspoon/init.lua`.
   - Do not reload Hammerspoon automatically unless explicitly requested; report whether a reload is needed for the
     running key map to pick up the change.
