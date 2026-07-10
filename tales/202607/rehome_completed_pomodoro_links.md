---
create_time: 2026-07-10 18:18:50
status: done
prompt: .sase/sdd/prompts/202607/rehome_completed_pomodoro_links.md
---
# Plan: Rehome Completed Pomodoro Task Links

## Goal

Extend `bob mark-next-tasks` so that block links found beneath open Pomodoros in today's daily note are also checked
against their resolved Obsidian Tasks task. When a link points to a completed task, normalize that daily-note reference
into an embed and place its containing sub-bullet beneath the most appropriate Pomodoro, while preserving the command's
existing Next-status synchronization, guard rails, dry-run semantics, output contracts, and idempotence.

## Behavioral contract

- Continue using the daily note's `## Pomodoros` section and the existing vault-relative/unique-basename block-link
  resolution rules.
- Treat a resolved task as complete when its checkbox is the conventional `[x]`/`[X]` status or a status configured by
  Obsidian Tasks with type `DONE`. Do not treat canceled, non-task, unknown, or merely in-progress statuses as complete.
- For every link-bearing sub-bullet beneath an open Pomodoro that resolves to at least one completed task:
  - Make each completed-task block link an embed by inserting `!` immediately before `[[...]]` when it is not already
    embedded, preserving aliases and all other link text.
  - Select the single top-level open Pomodoro with a valid time range as the current Pomodoro. If the completed link is
    beneath another open/future Pomodoro, move its containing bullet beneath the current Pomodoro.
  - If there is no current Pomodoro, use the last completed top-level Pomodoro in document order as the relocation
    target.
  - If neither target exists, leave the bullet where it is and only normalize the link to an embed.
  - Move the containing Markdown bullet together with any nested descendants, preserve the relative order of multiple
    moved bullets, and normalize it to the target's child indentation. A mixed-content bullet moves as one unit, while
    only links proven to target completed tasks gain `!`.
- Leave already embedded, correctly placed references unchanged. Keep unresolved or ambiguous references in place and
  report them through the existing warning path rather than guessing.
- Reject a daily note with multiple timed open Pomodoros before writing anything, matching the invariant already
  enforced by Pomodoro-linked capture.
- Preserve CRLF/LF style, surrounding text, section boundaries, and unrelated indentation. Repeated runs must be no-ops.

## Implementation approach

1. **Model Pomodoro entries and source link occurrences in `src/native/mark_next.rs`.** Replace the current set-only
   extraction with a section scan that retains each top-level Pomodoro's line/subtree range, open/completed state,
   optional time range, child indentation, and each block-link occurrence's owning bullet. Continue deriving the
   deduplicated raw-reference set from this richer model for the existing Next-status resolution logic. Reuse the shared
   Pomodoro heading, open-task, and time-range helpers; add or expose a narrowly scoped completed-entry parser in
   `src/native/pomodoro.rs` if needed so capture, status display, and mark-next agree on ledger syntax.

2. **Extend the existing Tasks settings and task scan used by mark-next.** Read the current `globalFilter` together with
   DONE status symbols from `.obsidian/plugins/obsidian-tasks-plugin/data.json`, retaining the command's current safe
   defaults when settings are absent or malformed. Record matched task statuses by resolved `(note path, block ID)` so
   link resolution can distinguish completed tasks from todo/Next/in-progress/canceled tasks while preserving
   duplicate-block warnings. Only perform daily-note normalization when the resolved match is unambiguously complete;
   conflicting duplicate statuses remain warned and unchanged.

3. **Plan a structural daily-note rewrite after reference resolution.** Determine the current timed open entry, the last
   completed fallback, and the completed-link bullets requiring embedding and/or relocation. Rewrite link tokens without
   disturbing aliases or neighboring text; remove moved bullet subtrees from their source entries and insert them at the
   end of the selected target's child block using existing/nearby indentation conventions. Apply edits from stable
   source spans or reconstruct the Pomodoros section so source deletion and destination insertion cannot invalidate
   later edits.

4. **Compose all mutations before writing.** Merge the structural daily-note result with the existing checkbox status
   replacements, including the case where today's daily note itself contains synchronized Tasks tasks. Refactor the
   write stage to produce one final buffer per changed file and atomically write each file only after every resolution
   and Pomodoro invariant has passed. `--dry-run` must execute the identical planning path without writes.

5. **Make the new work observable without breaking existing consumers.** Add additive JSON fields describing embedded
   and moved completed references (including source/destination Pomodoro context and block-link identity), include these
   operations in human dry-run/apply output and summary counts, and ensure the human `already in sync` message appears
   only when neither task statuses nor daily-note links need changes. Update `src/native/mark_next.rs` help text and the
   concise command description in `src/runner.rs` to mention completed-link normalization.

6. **Document the expanded command contract.** Update `docs/mark-next-tasks.md` with DONE classification,
   current/fallback target selection, relocation-at-bullet granularity, multiple-current guard behavior, dry-run/JSON
   additions, and examples for future, completed-fallback, and no-target cases. Refresh the README summary so it no
   longer describes the command as only a `[*]` status synchronizer.

## Tests and verification

- Add focused unit tests in `src/native/mark_next.rs` (and `src/native/pomodoro.rs` if its parser changes) for:
  - plain versus already embedded block links, aliases, multiple/mixed links on one bullet, and invalid/unresolved
    links;
  - conventional and custom DONE statuses versus canceled, non-task, unknown, Next, and in-progress statuses;
  - current timed-open selection, last-completed fallback, no-target in-place behavior, and multiple-current rejection;
  - subtree moves, stable ordering, indentation reuse, fenced/other-section lookalikes, and LF/CRLF preservation;
  - composition of daily-note structural edits with checkbox-status edits and idempotent second runs.
- Expand `tests/fixtures/mark_next/` and the CLI integration test in `tests/cli.rs` to cover a completed task linked
  from a future Pomodoro, an already embedded completed link, fallback to the last completed Pomodoro, dry-run leaving
  every file byte-for-byte unchanged, additive JSON/human reporting, and successful idempotent apply.
- Add guard-focused integration cases for no current/no completed Pomodoro, multiple timed open Pomodoros,
  unresolved/duplicate block IDs, and custom DONE status settings, verifying failures or warnings never cause partial
  writes.
- Run targeted tests for mark-next and shared Pomodoro/capture behavior, then the repository's full formatting, lint,
  and test checks (using the existing `just`/Cargo workflows) to catch parser or output regressions.

## Expected files

- `src/native/mark_next.rs`
- `src/native/pomodoro.rs` (only for a shared completed-ledger parser/helper)
- `src/runner.rs`
- `tests/cli.rs`
- `tests/fixtures/mark_next/...`
- `docs/mark-next-tasks.md`
- `README.md`
