---
create_time: 2026-07-10 15:41:17
status: wip
prompt: .sase/sdd/prompts/202607/restore_hammerspoon_pomodoro_capture.md
tier: tale
---
# Plan: Restore the Hammerspoon Pomodoro-linked capture flow

## Context

The native `bob capture` implementation and its public documentation already support Pomodoro-linked captures through
the terminal marker `@!<route>:<block-id>`. The linked `chezmoi` source has not been updated to provide the documented
interactive shorthand: its Hammerspoon panel currently understands `@`, `@#`, `@#<prefix>`, and `@<route>#`, but has no
`@!` parser mode, block-ID prompt, staged capture state, or focused tests. The existing `cmd+shift+ctrl+i` binding is
correct and must remain unchanged.

## Objective

Extend the Hammerspoon task-capture panel in the linked `chezmoi` repository so a trailing `@!` chooses an area or
project and then requests a block ID, while a trailing `@!<route>` skips the target picker and requests the block ID
directly. Final submission must call the existing native CLI contract safely and preserve the user's staged input when
capture fails.

## Product contract

- Recognize only terminal, whitespace-delimited Hammerspoon shorthand markers:
  - `<task> @!` strips the marker, opens the existing area/project chooser, and advances to the block-ID prompt after a
    target is selected.
  - `<task> @!<route>` strips the marker, normalizes the explicit route to lowercase, and advances directly to the
    block-ID prompt.
- Route and block-ID values use the CLI's existing `A-Z`, `a-z`, `0-9`, `_`, and `-` grammar. The block-ID prompt cannot
  submit an empty or malformed value.
- Preserve existing `@`, `@#`, `@#<prefix>`, `@<route>#`, ordinary capture, and non-terminal lookalike behavior.
- Keep the `cmd+shift+ctrl+i` hotkey unchanged. The work changes the state flow inside the panel reached by that
  binding.
- Retain the original task body and selected route in Lua-owned state while the block-ID prompt is active. Dismissing a
  chooser returns focus without losing the original task, and a CLI error leaves the staged task, route, and entered ID
  available for correction or retry.
- Build the final request as a validated leading `@!<route>:<block-id>` marker followed by the original task body, and
  pass the complete request only through the shell command's positional parameter. Do not also pass `--route`: native
  capture intentionally treats special markers literally when a forced route is supplied.
- Preserve the current async task identity guards, cancellation behavior, destination notifications, and
  close-on-success behavior.

## Implementation

1. **Extract pure request and state logic.**
   - Add a small Lua module beside the Hammerspoon config for terminal-marker parsing, route/block-ID validation,
     Pomodoro request staging, and final CLI-text construction.
   - Represent task entry, optional target selection, and block-ID entry as explicit states so the UI integration does
     not depend on parsing or reconstructing display text.
   - Return structured request descriptors compatible with the current capture modes, adding distinct picker-backed and
     explicit-route Pomodoro modes without changing the established modes.

2. **Integrate the staged flow into the capture panel.**
   - Require the pure helper from `init.lua` and keep the current target-fetch and chooser machinery for `@!` requests.
     Selecting a target should stage its route/name/kind and transition to block-ID entry instead of running capture.
   - Extend the webview with a controlled prompt update for the title, input value/label, primary-button label, and
     validation state. Task submission stages the request; block-ID submission validates and finalizes it.
   - Keep the staged state in Lua, reset it only on a new/closed prompt or successful capture, and restore the block-ID
     prompt after native failures. Ensure chooser cancellation and late async callbacks cannot advance stale state.
   - Invoke the existing final-capture path with the synthesized special marker embedded in the positional task text,
     while retaining picked target metadata for the success notification.

3. **Add focused regression coverage and repository checks.**
   - Add pure-Lua tests for `@!`, mixed-case explicit `@!route`, valid and invalid block IDs, final marker construction,
     task-to-target-to-ID state transitions, failure retention, and reset/success behavior.
   - Cover the existing marker modes and representative mid-text/non-terminal lookalikes to ensure the extraction does
     not change their semantics.
   - Exercise the chooser-backed and explicit-route paths against the same state transition with mocks where needed;
     keep tests independent of a live Hammerspoon process and the live Obsidian vault.
   - Wire the focused test into the repository's test entry point if necessary, format the new Lua source consistently,
     and run a Lua syntax check over both the helper and complete Hammerspoon config. Run the applicable repository
     checks and inspect the diff to confirm the hotkey and unrelated keymaps remain untouched.

## Verification scenarios

- `Plan release @!` opens the target chooser; selecting `Dev` opens the block-ID prompt; entering `release-plan` invokes
  `bob capture` with positional text `@!dev:release-plan Plan release`.
- `Plan release @!Dev` skips the chooser and reaches the same block-ID state and final request.
- Invalid values such as an empty ID, `bad.id`, or `bad/id` cannot submit; a native failure keeps `Plan release`, `dev`,
  and the entered ID staged.
- Existing `Plan release @`, `Plan release @#`, `Plan release @#Ideas`, `Plan release @Dev#`, ordinary task text, and
  non-final `@!` lookalikes follow their prior paths.
- The config still binds `showTaskCapturePrompt()` to `{ "cmd", "shift", "ctrl" } + i`, all pure-Lua tests pass, and
  `luac -p` succeeds without reading or writing the live vault.
