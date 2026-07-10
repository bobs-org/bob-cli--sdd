---
create_time: 2026-07-10 16:23:17
status: wip
prompt: .sase/sdd/prompts/202607/hammerspoon_pomodoro_link_capture.md
---
# Plan: Add Pomodoro-linked capture flow to the Hammerspoon keymap

## Objective

Complete the missing Hammerspoon half of the approved Pomodoro-linked capture workflow in the source-of-truth chezmoi
repository. The task-capture panel opened by `cmd+shift+ctrl+i` should recognize trailing `@!` and `@!<route>`
shorthands, collect a valid block ID, and invoke the already-implemented `bob capture` special-route grammar without
regressing existing capture modes.

This correction is limited to the chezmoi-managed Hammerspoon configuration. The `bob-cli` capture implementation is
already present and is not part of this change.

## Product behavior

- Keep the existing `cmd+shift+ctrl+i` hotkey unchanged. Only extend the task-capture workflow reached through that
  binding.
- Treat a trailing, whitespace-delimited `@!` as an interactive special capture: remove the marker from the task body,
  open the existing area/project target picker, and then prompt for a block ID.
- Treat a trailing, whitespace-delimited `@!<route>` as the explicit-route form: normalize the route consistently with
  existing capture routing, skip the target picker, and prompt directly for a block ID.
- Preserve the current behavior of `@`, `@#`, `@#<prefix>`, `@<route>#`, ordinary `@<route>` input, non-terminal
  lookalikes, and unmarked inbox captures.
- Accept block IDs only when they are non-empty and contain `A-Z`, `a-z`, `0-9`, `_`, or `-`. Keep submission disabled
  for invalid values and retain the task, route, picked-target label, and entered ID when validation or the CLI fails.
- Submit the special capture by constructing a leading `@!<normalized-route>:<block-id>` marker followed by the original
  task body. Continue passing the complete request through positional shell arguments so user input is never
  interpolated into shell source.
- Reuse the existing asynchronous task guards, cancellation behavior, target chooser, and success/failure notification
  paths. A successful capture closes the panel; cancellation or a failed `bob capture` must not leak stale state into
  the next invocation.

## Implementation

1. **Add a testable request/state helper under `home/dot_hammerspoon/`.**
   - Move or wrap terminal-marker parsing in a small pure-Lua module that has no dependency on the Hammerspoon `hs`
     global.
   - Extend its request descriptor with picker-backed and explicit-route special-capture modes, while retaining the
     descriptors used by every existing marker form.
   - Add pure functions for block-ID validation and for advancing a special request from task entry through route
     selection to a block-ID-ready capture request. Keep synthesis of the native `@!route:id` token centralized so
     picker and explicit-route paths cannot drift.

2. **Turn the task-capture webview into an explicit task/block-ID state flow.**
   - Track the current prompt stage and staged special-capture values in Lua alongside the existing prompt, chooser, and
     task handles.
   - Let the webview update its title, accessible input label, input value, and submit-button validity when entering the
     block-ID stage, then return focus to the input.
   - Route `@!` through the existing target fetch/chooser and advance after a valid target is selected. Route
     `@!<route>` directly to the same block-ID stage.
   - On block-ID submission, call the existing final-capture runner with the synthesized special marker and original
     body. Clear staged state only when closing the panel; on CLI failure, leave the block-ID stage visible and
     editable.

3. **Integrate focused Hammerspoon tests into the chezmoi checks.**
   - Add pure-Lua tests covering `@!`, case-normalized `@!<route>`, invalid routes and block IDs, empty task bodies,
     non-terminal lookalikes, and regression cases for all existing marker modes.
   - Test that picker-backed and explicit-route requests converge on the same final request synthesis, and that invalid
     transitions retain staged task and route values.
   - Add a narrow Justfile recipe for the Hammerspoon tests if the repository has no existing entry point, without
     broadening the current Neovim-only Lua lint paths unintentionally.

## Verification

- Run the new pure-Lua Hammerspoon tests.
- Run `luac -p` over the complete `home/dot_hammerspoon/init.lua` and the new helper module.
- Run Stylua in check mode on the changed Lua files, using the repository configuration.
- Run the repository checks affected by any Justfile change and inspect the final chezmoi diff.
- Confirm in the diff that the `cmd+shift+ctrl+i` binding is byte-for-byte unchanged, existing marker branches remain
  covered, shell invocation still uses positional parameters, and no live vault or generated files were touched.
