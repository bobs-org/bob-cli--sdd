---
create_time: 2026-07-10 16:11:12
status: wip
prompt: .sase/sdd/prompts/202607/hammerspoon_pomodoro_capture.md
---
# Plan: Complete the Hammerspoon Pomodoro-linked capture flow

## Objective

Implement the missing Hammerspoon side of Pomodoro-linked task capture in the source `chezmoi` repository. The task
capture panel must understand trailing `@!` and `@!<route>` shorthands, collect a valid Obsidian block ID after the task
and route are known, and invoke the already-supported native `bob capture @!<route>:<block-id> ...` workflow.

The existing Hammerspoon binding is `cmd+shift+ctrl+i`. Preserve that binding unchanged: this work changes the capture
flow opened by the keymap, not the key combination itself. Do not edit the live Obsidian vault while implementing or
testing this change.

## Current state

- `home/dot_hammerspoon/init.lua` currently recognizes only the trailing `@`, `@#`, `@#prefix`, and `@route#` UI
  markers. `@!` and `@!<route>` currently fall through to an immediate `bob capture` call.
- The capture webview has one fixed task-input state, and the chooser callbacks proceed directly to the final capture or
  section flow. There is no block-ID prompt or staged Pomodoro-link request state.
- The source repository contains no pure-Lua helper or focused tests for capture-marker parsing and state transitions.
- `bob capture` already accepts `@!<route>:<block-id>`, validates the marker, creates the next-status task, and links it
  from the eligible Pomodoro. Hammerspoon should compose and pass that public syntax rather than reproduce the vault
  mutation logic.

## Product behavior

- Submitting `<task> @!` opens the existing area/project target picker. After a target is selected, the same capture
  panel prompts for the block ID.
- Submitting `<task> @!<route>` skips the target picker and proceeds directly to the block-ID prompt, with route names
  normalized consistently with `bob capture`.
- The block ID is non-empty and contains only `A-Z`, `a-z`, `0-9`, `_`, or `-`. Invalid input keeps the user in the
  block-ID state and does not launch the CLI.
- A valid submission invokes `bob capture` with a synthesized leading `@!<route>:<block-id>` marker and the original
  task body. User-provided values continue to be passed only as positional shell parameters.
- Existing `@`, `@#`, `@#prefix`, `@route#`, ordinary capture, picker, notification, and cancellation behavior remains
  unchanged. Non-terminal and malformed lookalikes remain owned by the native CLI rather than being reinterpreted by the
  Hammerspoon UI.
- If target discovery, chooser selection, CLI launch, or final capture fails, preserve the staged task, route, and block
  ID as applicable so the user can retry or cancel without retyping the request.

## Implementation

1. **Extract capture request and transition logic into a pure Lua helper.**
   - Add a small module under `home/dot_hammerspoon/` that parses only terminal UI shorthand markers and validates
     route/block-ID tokens.
   - Represent the Pomodoro-linked path explicitly, distinguishing “choose target” from “known route, request block ID,”
     while retaining descriptors for every existing marker mode.
   - Provide pure transition/composition functions that carry the original task text and selected target metadata into
     the block-ID state and produce the final `@!<route>:<block-id>` capture request only after validation.

2. **Turn the capture panel into an explicit task/block-ID state machine.**
   - Replace the fixed title, label, and submit behavior with renderable prompt state so the webview can switch from
     task entry to block-ID entry without losing the original task.
   - Keep staged request data in Lua, not interpolated JavaScript or shell text. Reset it on a fresh panel open and
     successful close; preserve it through retryable failures and refocus paths.
   - Route trailing `@!` through the existing target-loading and chooser infrastructure, then transition the chosen
     route into the block-ID prompt. Route `@!<route>` directly to that prompt.
   - On valid block-ID submission, compose the native special marker and use the existing asynchronous final-capture
     path, guarded callbacks, cancellation, and success/failure notifications.

3. **Protect existing chooser and capture behavior.**
   - Thread the new request descriptor through target selection without changing section-picker semantics for `@#`
     modes.
   - Keep the shell command generic and positional; avoid adding special vault-editing behavior to Hammerspoon.
   - Update nearby comments and prompt copy so maintainers can see the two prompt states, supported shorthand, and the
     fact that `cmd+shift+ctrl+i` remains the registered hotkey.

4. **Add focused regression coverage in the `chezmoi` repository.**
   - Add a standalone Lua test file for the pure helper covering `@!`, case-normalized `@!route`, invalid routes and
     block IDs, empty task bodies, terminal-position rules, and non-terminal lookalikes.
   - Cover regression cases for `@`, `@#`, `@#prefix`, `@route#`, plain routes, and ordinary text.
   - Test that target-picker and explicit-route paths converge on the same block-ID state, that valid IDs synthesize the
     expected native marker, and that invalid/failure transitions retain staged values.

## Verification

- Run the focused pure-Lua tests outside Hammerspoon.
- Run `luac -p` against the helper and complete `home/dot_hammerspoon/init.lua` configuration.
- Run the repository's applicable Lua formatting checks on the changed files, extending the existing commands only as
  needed to include the Hammerspoon helper/tests.
- Review the source `chezmoi` diff and confirm the hotkey remains exactly
  `hs.hotkey.bind({ "cmd", "shift", "ctrl" }, "i", ...)`, existing marker modes still behave as before, and all
  shell-bound user input is positional.
- If a Mac/Hammerspoon runtime is available, smoke-test task-to-target-to-block-ID and explicit-route-to-block-ID
  transitions without submitting against the live vault. Otherwise record that the runtime smoke test was not performed;
  automated tests and syntax checks must not write to `~/bob/`.
