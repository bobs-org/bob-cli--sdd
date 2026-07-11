---
create_time: 2026-07-10 15:55:28
status: wip
prompt: .sase/sdd/plans/202607/prompts/colon_pomodoro_capture.md
tier: tale
---
# Plan: Make colon the Pomodoro capture marker

## Context

`bob capture` currently uses a complete `@!<route>:<block-id>` marker for Pomodoro-linked tasks. The approved
Hammerspoon follow-up builds that native marker after interpreting trailing `@!` as “pick a note, then ask for a block
ID” and trailing `@!<route>` as “use this note, then ask for a block ID.” The `!` is redundant: ordinary route markers
cannot contain `:`, section selectors use `#`, and both route names and block IDs already use the restricted `A-Z`,
`a-z`, `0-9`, `_`, and `-` grammar.

The canonical complete marker can therefore become `@<route>:<block-id>`. In the Hammerspoon panel, an omitted value
after the colon naturally represents the staged variants: `@<route>:` requests only a block ID, while `@:` requests a
note first and then a block ID. The native CLI remains non-interactive and must reject these incomplete forms with a
clear usage error.

The native Pomodoro implementation is already present in `bob-cli`. The approved Hammerspoon staged-flow changes are
currently preserved as unfinished linked-repository work rather than part of the linked repository's base branch; this
follow-up must build on that work and retain its state, retry, and async-safety behavior.

## Objective

Make colon—not `!`—the canonical signal for Pomodoro-linked capture across the native CLI, documentation, examples, and
Hammerspoon panel. Support `@<route>:<block-id>` for complete requests, `@<route>:` for direct block-ID prompting, and
`@:` for note selection followed by block-ID prompting, without changing ordinary route, bullet-section, schedule, or
forced-route behavior.

## Product contract

- Canonical native syntax is a whitespace-delimited `@<route>:<block-id>` token in the same leading or trailing terminal
  positions supported by the existing Pomodoro marker. Routes are normalized to lowercase; block-ID case is preserved.
- The complete marker composes with terminal scheduling exactly as before: both `<task> s:2 @dev:id` and
  `<task> @dev:id s:2` produce a scheduled Pomodoro-linked task.
- The Hammerspoon task panel recognizes only these incomplete terminal shorthands, preceded by whitespace:
  - `<task> @dev:` strips the marker, normalizes `dev`, and opens the block-ID prompt directly.
  - `<task> @:` strips the marker, opens the existing area/project chooser, and then opens the block-ID prompt.
- A complete `<task> @dev:id` entered in Hammerspoon is not staged; it passes through to `bob capture`, which owns the
  native parsing and capture transaction.
- Direct native CLI use of incomplete or malformed terminal colon markers—such as `@dev:`, `@:`, `@:id`, `@dev:bad.id`,
  or `@dev:id:extra`—fails with a usage error and performs no writes. Mid-text lookalikes remain literal.
- Preserve the existing `@!<route>:<block-id>` native form and Hammerspoon `@!` / `@!<route>` shorthands as
  compatibility aliases for existing callers, but make colon forms canonical in generated requests, help text,
  documentation, and new examples. Compatibility behavior should be covered by regression tests rather than promoted as
  the primary syntax.
- Preserve ordinary `@route` task routing, `@route#prefix` bullet routing, Hammerspoon `@`, `@#`, `@#prefix`, and
  `@route#` picker modes. Preserve leading-route precedence, terminal-marker whitespace requirements, schedule parsing,
  and literal `@` text outside recognized terminal positions.
- `--route` and `--route --section` continue to bypass automatic special-marker parsing and keep colon and legacy `@!`
  tokens literal, matching the current forced-route contract.
- Final Hammerspoon submission embeds `@<route>:<block-id>` in the positional task text and does not pass `--route`, so
  the native parser selects Pomodoro mode and retains its coordinated two-note validation/write behavior.
- Keep the existing Hammerspoon hotkey, chooser contents, prompt validation, staged-value retention after native
  failures, close-on-success behavior, cancellation behavior, and stale async callback guards unchanged.

## Implementation

1. **Generalize native special-route parsing around the colon form.**
   - Update the capture parser to recognize a terminal `@<route>:<block-id>` token before ordinary `@route` parsing,
     returning the existing Pomodoro capture kind and normalized route.
   - Treat terminal `@` tokens containing `:` as attempted Pomodoro markers so malformed forms fail explicitly instead
     of silently becoming literal inbox text. Keep middle tokens literal and retain the forced-route bypass.
   - Include valid canonical colon markers in terminal schedule detection, while retaining the legacy `@!` parser as a
     compatibility path into the same parsed representation and validation messages.
   - Keep all downstream formatting, duplicate-ID checks, daily-note selection, coordinated writes, JSON fields, and
     rollback behavior shared and unchanged; this is a marker-contract change, not a second Pomodoro implementation.

2. **Adopt incomplete colon shorthands in the Hammerspoon staged flow.**
   - Restore/build on the approved pure `task_capture_flow` module and staged UI integration in the linked `chezmoi`
     repository rather than reimplementing the flow in `init.lua`.
   - Extend terminal shorthand parsing so `@:` enters the target-selection state and `@<route>:` enters the existing
     block-ID state. Parse these before ordinary `@` and route/section forms so their intent is unambiguous.
   - Leave complete `@<route>:<block-id>` requests in the normal pass-through mode, and keep malformed or non-terminal
     lookalikes available to the native parser or literal capture according to the native contract.
   - Change the pure final-text builder to synthesize canonical `@<route>:<block-id> <task>` text. Continue passing a
     nil route argument to the final native capture and preserving picked target metadata only for notifications.
   - Retain the legacy Hammerspoon `@!` and `@!<route>` descriptors as aliases into the same target/block-ID states,
     with no duplicated UI or state-transition path.

3. **Update public contract and regression coverage in both repositories.**
   - Replace canonical `@!` syntax in `bob capture --help`, top-level command examples, and the README with colon-only
     examples. Document the Hammerspoon `@:` and `@route:` prompt forms and distinguish them from the complete native
     marker.
   - Expand Rust parser tests across leading/trailing canonical markers, case normalization/preservation, schedule
     ordering, missing bodies, malformed terminal forms, mid-text literals, forced routes, and legacy compatibility.
   - Update CLI integration tests and help assertions to exercise canonical `@dev:id` end to end, including successful
     two-note writes, dry-run behavior, preflight atomicity, missing daily notes, malformed input, and stable JSON.
   - Expand the pure Lua suite for `@:`, mixed-case `@route:`, complete-marker pass-through, legacy aliases, established
     picker syntax, malformed/non-terminal lookalikes, convergent picked/explicit state transitions, validation, final
     marker construction, failure retention, and success reset.
   - Run focused Rust capture tests and the full `bob-cli` checks; in `chezmoi`, run the Hammerspoon pure-Lua tests,
     `luac -p` over the helper and full config, Lua formatting/linting, and the applicable repository test/check
     recipes. Inspect both diffs to confirm no unrelated keymaps or capture modes changed.

## Verification scenarios

- `bob capture '@Dev:Foo_Bar' 'Do thing'` and `bob capture 'Do thing @Dev:Foo_Bar'` both capture a `[*]` task in
  `dev.md`, preserve `Foo_Bar` as the block ID, and add `[[dev#^Foo_Bar]]` beneath the selected open Pomodoro.
- `bob capture 'Do thing s:2 @dev:id'` and `bob capture 'Do thing @dev:id s:2'` produce the same scheduled linked task.
- Entering `Do thing @dev:` in Hammerspoon goes directly to block-ID entry; submitting `work-1` invokes native capture
  with positional text `@dev:work-1 Do thing` and no forced route.
- Entering `Do thing @:` in Hammerspoon opens the note chooser and then the same block-ID state; chooser cancellation
  preserves the original task, and a native failure preserves the selected route and entered ID for retry.
- Entering complete `Do thing @dev:work-1` in Hammerspoon captures immediately without either picker.
- Native `@dev:`, `@:`, `@:id`, `@dev:bad.id`, and `@dev:id:extra` requests fail before writes; `Discuss @dev:id later`
  remains ordinary task text; forced-route capture keeps `@dev:id` literal.
- Existing `@!dev:id`, Hammerspoon `@!dev`, and Hammerspoon `@!` behavior remains functional as a compatibility layer,
  while all generated text and documentation use the colon-only forms.
- Existing `@dev`, `@dev#Ideas`, Hammerspoon `@`, `@#`, `@#Ideas`, and `@dev#` behavior remains unchanged, and the
  Hammerspoon capture hotkey remains exactly as currently configured.
