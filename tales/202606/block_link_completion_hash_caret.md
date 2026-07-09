---
create_time: 2026-06-24 09:03:25
status: done
prompt: sdd/prompts/202606/block_link_completion_hash_caret.md
---
# Plan: Complete block-link task picker links as `[[foo#^id]]`, not `[[foo^id]]`

## Repository

This fix lives in the **`bob-plugins`** linked repo (source-of-truth monorepo for Bryan's Obsidian plugins; deployed to
`~/bob/` via `bob plugins sync`). All paths below are relative to the `bob-plugins` repo root. To read/edit
`bob-plugins` from a numbered workspace, open it with `sase workspace open -p bob-plugins -r "<reason>" <workspace_num>`
and use the printed path.

## Problem

When the `block-id-prompt` task picker completes a wiki block link, a link triggered by the **bare** double-caret marker
`[[foo^^]]` is completed to `[[foo^id]]`. That is **not** a valid Obsidian block reference — Obsidian block links must
use the `#^` form, i.e. `[[foo#^id]]`. As written, the produced link does not resolve to the task's block.

The canonical-marker path `[[foo#^^]]` already completes correctly to `[[foo#^id]]`; only the bare-caret path is wrong.

## Root cause

The completed link's block prefix is taken from `source.blockPrefix`, which `parseTrailingTaskPickerMarker`
(`plugins/block-id-prompt/main.js`) sets to **the marker style the user typed**:

- `[[foo#^^]]` → `blockPrefix = "#^"` → completes to `[[foo#^id]]` (correct), and
- `[[foo^^]]` → `blockPrefix = "^"` → completes to `[[foo^id]]` (the bug).

The completion string is built by the shared helper `sourceReplacement(source, id)`:

```
[[${source.targetText}${source.blockPrefix}${id}${source.aliasSuffix}]]
```

The bare-caret marker is the natural product of the existing file-link jump (`[[foo]]` +`^`→ `[[foo^]]` +`^`→
`[[foo^^]]`), so it is the common path, which is why the bug is easy to hit.

## Key constraint: the fix must be surgically scoped to the completion output

Two things make a blanket change to `blockPrefix` or to `sourceReplacement` unsafe:

1. **`sourceReplacement` is shared with the block-id _rename_ feature** (it rewrites the renamed link and every other
   wiki reference to the renamed block). Those callers must keep each reference's own existing prefix; they must not be
   forced to `#^`.
2. **`source.blockPrefix` is also consumed by the cancel/revert helpers** (`taskPickerRevertReplacement`,
   `taskPickerRevertCursorCh`). On dismiss, the picker reverts the transient second caret back to the **post-jump
   state** — `[[foo^]]` for a bare trigger, `[[foo#^]]` for a `#^^` trigger. Revert must therefore continue to use the
   user's original caret style; it must not be normalized to `#^`.

So the change must affect **only** the task-picker's _completion_ output, while leaving the rename path and the
cancel/revert path exactly as they are.

## Approach

Normalize the **completion** prefix to the canonical `#^` at the single point where the task link is completed, without
touching `source.blockPrefix` (which stays as the typed style for revert) and without changing the shared
`sourceReplacement` defaults used by the rename path.

Concretely:

- Allow `sourceReplacement(source, id, blockPrefix)` to accept an explicit prefix, defaulting to `source.blockPrefix`
  (so existing rename callers are unchanged and continue to preserve each reference's style).
- In `completeTaskSourceLink` (the one helper both task-completion branches funnel through — existing-id selection and
  newly-assigned-id selection), build the replacement with the canonical `#^` prefix.

This makes both completion branches emit `[[foo#^id]]` (and `[[foo#^id|Alias]]` for aliased links) regardless of whether
the user typed bare `^^` or `#^^`, while:

- the `#^^` path is unchanged (it was already `#^`),
- the rename path is unchanged (still preserves each reference's prefix),
- the cancel/revert path is unchanged (still restores `[[foo^]]` / `[[foo#^]]` per the typed style).

**Alternative considered — set `blockPrefix = "#^"` in the parser and add a separate `revertPrefix` field for the revert
helpers:** rejected. It spreads the change across the parser plus both revert helpers and makes `blockPrefix` no longer
mean "what the user typed," for no benefit over normalizing at the single completion site.

**Alternative considered — change the file-link jump to emit `[[foo#^]]`:** rejected as out of scope. The jump and the
transient revert state are existing, separate behavior the user did not ask to change; the only defect is the completed
link.

## Files to change

- `plugins/block-id-prompt/main.js`
  - `sourceReplacement` — accept an optional explicit block prefix (defaulting to `source.blockPrefix`).
  - `completeTaskSourceLink` — complete the source link with the canonical `#^` prefix.
- `plugins/block-id-prompt/manifest.json` — patch version bump `1.1.0 → 1.1.1` (bug fix).
- `README.md` — update the `block-id-prompt` row's version to `1.1.1` (description is still accurate).

## Validation & deployment

- `npm run validate` (manifest field checks + `node --check` on `main.js`).
- `git diff --check` (no whitespace errors).
- Deploy to the vault from the `bob-plugins` workspace: `bob plugins sync -p block-id-prompt -r "$PWD"` (the `-r "$PWD"`
  reason flag is required when syncing from a SASE workspace).

## Manual test matrix (in-vault)

Using a `foobar.md` with at least one open `#task` line that has an existing `^id` and one without, from another note:

1. `[[foobar]]` +`^`→ `[[foobar^]]` +`^`→ menu opens. Pick a task **with** an id → link completes to
   **`[[foobar#^<existingId>]]`** (previously `[[foobar^<existingId>]]`).
2. Pick a task **without** an id → enter `my-id` → `^my-id` appended in `foobar.md`, link completes to
   **`[[foobar#^my-id]]`**.
3. Canonical trigger: type `[[foobar#^^]]` directly → completion is still `[[foobar#^<id>]]` (unchanged).
4. Alias: `[[foobar^^|Title]]` → completes to **`[[foobar#^<id>|Title]]`**.
5. `Esc` from the menu → link reverts to `[[foobar^]]` (bare) / `[[foobar#^]]` (canonical), cursor after the caret —
   unchanged revert behavior.
6. Confirm a completed link actually resolves to the task's block on hover/click in Obsidian.
7. Block-id **rename** of an existing block still rewrites references preserving their prefixes (regression check that
   the shared `sourceReplacement` change did not alter rename output).
8. `npm run validate` passes.
