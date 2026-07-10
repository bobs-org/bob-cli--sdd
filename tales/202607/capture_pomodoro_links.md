---
create_time: 2026-07-10 13:31:50
status: done
prompt: .sase/sdd/prompts/202607/capture_pomodoro_links.md
---
# Plan: Add Pomodoro-linked `bob capture` tasks

## Objective

Add an explicit capture mode that creates a routed Obsidian task with the custom "next" status and a caller-provided
block ID, then links that block from the current or next open Pomodoro in today's daily note. Extend the Hammerspoon
task capture panel so `@!` and `@!<route>` collect the missing block ID interactively before invoking the native CLI.

This work spans the `bob-cli` repository and the linked `chezmoi` repository. It must not edit the live vault while
being developed or tested.

## Product contract

- Recognize `@!<route>:<block-id>` as a special route marker in the same leading/trailing terminal positions as existing
  `@route` markers. Route names continue to use the current `A-Z`, `a-z`, `0-9`, `_`, and `-` grammar and are normalized
  to lowercase. Block IDs must be non-empty and use the block-ID characters already supported elsewhere in `bob-cli`
  (`A-Z`, `a-z`, `0-9`, `_`, and `-`). Malformed special markers should produce a usage error instead of silently
  creating an ordinary inbox task.
- Preserve ordinary capture behavior and metadata. A special capture changes the checkbox to `[*]` and appends
  `^<block-id>` after the existing task metadata:

  ```markdown
  - [*] #task Some foobar task. [created::2026-07-10] ^foobar
  ```

  This interprets the metadata-free line in the request as an abbreviated illustration of the new status and block ID;
  if the plan review requires that line literally, isolate that difference in the special-task formatter without
  changing normal captures.

- Continue to support the existing scheduled-offset grammar around the new route marker, with the block ID remaining the
  final task token. Forced-route and bullet captures retain their current semantics.
- Resolve today's daily note from `BOB_DAY_FILE` when set, otherwise from the capture request's Bob directory and
  `BOB_NOW`/the current local date. The special capture requires an existing daily note, a Pomodoros section, and an
  eligible open Pomodoro; failures are reported before either note is changed.
- Within the Pomodoros section, scan top-level Pomodoro tasks from top to bottom. Prefer the single open entry
  containing a recognized time range. When none is timed, select the first open entry. Ignore completed entries, nested
  tasks, and task-looking content outside the section; report an invariant error if multiple open timed entries make the
  target ambiguous.
- Add `[[<route>#^<block-id>]]` at the end of the selected Pomodoro's child block, after its existing sub-bullets. Reuse
  the existing child indentation style when present, otherwise infer the nearby list style and fall back to two spaces,
  so the link is always a true sub-bullet.
- Reject a block ID already present in the routed note. Dry-run must perform all parsing and validation and report both
  planned edits without writing either file.
- Keep the existing Hammerspoon hotkey binding unchanged. The source currently binds `cmd+shift+ctrl+i`; this plan
  changes the menu reached by that binding, not the binding itself.

## Implementation

1. **Extend capture parsing and result modeling in `bob-cli`.**
   - Give the capture parser a first-class special-route representation rather than overloading bullet mode, including
     clear validation errors and coverage for leading/trailing markers, schedule ordering, normalization, missing
     bodies, and malformed route/ID combinations.
   - Add a focused formatter for next-status tasks and block IDs while retaining the normal task/bullet formatters.
   - Extend human and JSON results with optional special-capture details such as the block ID, daily-note path, rendered
     block link, and Pomodoro-link placement. Existing fields and ordinary JSON behavior remain compatible.

2. **Share Pomodoro-ledger recognition and plan the two note mutations.**
   - Extract or expose the existing Pomodoros-heading, open-checkbox, and time- range recognition used by `bob pomodoro`
     so status display and capture linking cannot drift on bold/legacy time-range syntax.
   - Add a Markdown-aware selector/inserter that preserves line endings and surrounding content, locates the preferred
     open Pomodoro, and appends the routed block link after that Pomodoro's complete indented child block.
   - Refactor capture execution to read and validate the routed note and daily note, compute both final contents, and
     only then write. Use coordinated temporary writes/rollback handling so a second-file failure does not knowingly
     leave a task without its required Pomodoro link (or vice versa). New target-file creation must follow the same
     preflight rule.

3. **Add the interactive `@!` flow in the linked `chezmoi` Hammerspoon source.**
   - Extend the terminal-marker parser with `@!` (open the existing area/project target picker) and `@!<route>` (use
     that explicit route). Preserve all existing `@`, `@#`, and `@route#` paths and leave non-terminal lookalikes
     untouched.
   - Turn the capture webview into a small explicit state machine so, after the original task is submitted and any
     target is selected, it changes to a block-ID prompt. Retain the original task/route in Lua state, validate the ID
     before enabling submission, and preserve the staged values if the CLI reports a failure.
   - Invoke `bob capture` by synthesizing a validated leading `@!<route>:<block-id>` marker plus the original body.
     Continue passing user input only through positional shell parameters, and reuse the existing async cancellation and
     success/failure notification behavior.
   - Keep marker parsing/validation in a small pure Lua helper where practical so `@!`, `@!route`, invalid IDs, and
     regression cases for the existing marker modes can be tested without a running Hammerspoon process.

4. **Document the public workflow.**
   - Update `bob capture --help`, top-level examples where useful, and the README capture section with the new grammar,
     exact task/link output, selection priority, failure behavior, dry-run/JSON fields, and examples.
   - Update environment documentation so `BOB_DAY_FILE` clearly applies to both Pomodoro status and Pomodoro-linked
     capture.
   - Document the Hammerspoon-only shorthand: trailing `@!` chooses a note and then asks for an ID, while trailing
     `@!<route>` skips the note picker and asks directly for the ID.

## Verification

- Add Rust unit tests for the special marker grammar, formatter, duplicate-ID detection, Pomodoros section boundaries,
  open-status detection, timed-over- untimed priority, first-open fallback, ambiguity/no-target errors, indentation
  preservation, and insertion after existing children.
- Add CLI integration tests using disposable vaults and `BOB_NOW`/ `BOB_DAY_FILE` that verify the representative
  `dev`/`foobar` capture updates both files, JSON and human output describe both edits, dry-run changes neither file,
  and every preflight failure leaves both files untouched. Include legacy and bold time ranges and a no-current-Pomodoro
  fallback case.
- Add focused pure-Lua tests for the Hammerspoon request parser/state inputs and run a Lua syntax check on the complete
  Hammerspoon config. Exercise target picker and prompt transitions with mocked callbacks where the current test harness
  permits; otherwise record a Mac Hammerspoon smoke check without writing to the live vault.
- Run `cargo fmt --check`, `cargo clippy --all-targets --all-features`, and `cargo test` in `bob-cli`, plus the focused
  Lua tests and repository formatting or lint checks applicable to the new `chezmoi` helper. Finally inspect both
  repository diffs to ensure no generated/live-vault files were touched.
