---
create_time: 2026-06-20 13:02:53
status: wip
prompt: sdd/prompts/202606/vim_surround_fixes.md
---
# Plan: Fix bob-vim-surround cursor jump and unsupported characters

## Context

The `bob-vim-surround` Obsidian plugin (in the `bob-plugins` sibling repo at `plugins/bob-vim-surround/main.js`) adds
vim-surround `ys`/`cs`/`ds` behavior to Obsidian's Vim mode. It is a plain CommonJS plugin — `main.js` is the source (no
TypeScript, no bundler, no build step), edited directly and deployed via `bob plugins sync`. Validation is a syntax-only
`node --check` via `npm run validate`.

Two user-reported bugs:

1. **`ys` jumps the cursor to the top of the file** after the text-object/motion (e.g. `ys2w`), so the current line can
   scroll out of view.
2. **Most characters are unsupported** — e.g. you cannot surround with `?` (`ys2w?`) or delete a surrounding `*`
   (`ds*`). Only a fixed set of bracket/quote pairs works.

## Root Cause Analysis

### Issue 1 — cursor jumps to top of file

`handleSurroundOperator` (main.js ~819-839) is registered as a CodeMirror Vim **operator** via `vim.defineOperator`.
CodeMirror's Vim engine, after running an operator, does roughly:

```js
var operatorMoveTo = operators[operator](cm, args, ranges, oldAnchor, newHead);
if (operatorMoveTo && !vim.visualMode) cm.setCursor(operatorMoveTo);
```

i.e. the operator's **return value is used as the new cursor position**. The success path returns `true`:

```js
this.pendingSurround = { cm, spans };
setCursor(cm, spans[0].start); // sets correct cursor...
return true; // ...then Vim runs cm.setCursor(true)
```

So Vim calls `cm.setCursor(true)`. Because `true` is not a number and has no `.line`/`.ch`, CodeMirror's `clipPos`
clamps it to the top of the document — overriding the correct `setCursor(cm, spans[0].start)` that ran moments earlier.
This is confirmed by the no-span branch, which already returns a real position object
(`return normalizePosition(oldAnchor) || false;`) — the author clearly knows a truthy **position** moves the cursor and
`false` is a no-op; the success path simply returns the wrong kind of truthy value.

The final cursor lands correctly only later (when `applySurround` runs on the pair keystroke), but the intermediate
`setCursor(true)` has already scrolled the viewport to the top, which is the visible symptom.

### Issue 2 — only bracket/quote pairs are supported

`SURROUND_PAIRS` (main.js 12-24) is the single source of truth for valid surround characters, containing only `" ' \` (
) [ ] { } < >`. Every add/change/delete path gates on `getSurroundPair(key)` returning non-null:

- Add: `handlePendingSurroundKeydown` → `getSurroundPair(key)`; if null, it cancels.
- Delete: `handlePendingDeleteSurroundKeydown` → `getSurroundPair(key)` guard, and `findEnclosingSurroundPair` →
  `getSurroundPair(targetKey)`.
- Change: target and replacement both go through `getSurroundPair`.

So `?`, `*`, `_`, `~`, `#`, `|`, `=`, etc. all resolve to `null` and are silently dropped. Key **detection** is not the
problem — `getSurroundKeyFromEvent` already accepts shifted single characters (it only blocks ctrl/alt/meta, not shift),
so `?` and `*` reach the handlers fine; they are rejected purely by the missing pair entry.

## Proposed Changes

All changes are confined to `plugins/bob-vim-surround/main.js` in the `bob-plugins` repo.

### Fix 1 — return a real cursor position from the operator

In `handleSurroundOperator`, replace the `setCursor(cm, spans[0].start)` + `return true;` with `return spans[0].start;`.
The pending state assignment stays. Vim will then call `cm.setCursor(spans[0].start)` — the correct position — and the
spurious top-of-file jump disappears. (The manual `setCursor` becomes redundant since Vim performs the move from the
return value; removing it avoids a double set.) The no-span early-return path is left unchanged.

### Fix 2 — support arbitrary punctuation as symmetric surround pairs

Generalize `getSurroundPair` so that, when a key is not one of the predefined special pairs, it falls back to a
**symmetric literal pair** (`{ open: key, close: key, padded: false }`) for any single printable, non-alphanumeric,
non-whitespace character. Keep the `SURROUND_PAIRS` map as-is for the characters that need special handling (padding on
`( [ { <`, and the open/close-alias distinction). Concretely:

- Add a small predicate (e.g. `isSymmetricSurroundChar(key)`) that accepts a length-1 string that is not a letter,
  digit, or whitespace.
- `getSurroundPair(key)` returns `SURROUND_PAIRS[key]` if present, else a symmetric pair when the predicate passes, else
  `null`.

This makes `ys2w?`, `ds*`, `cs*_`, and similar work via the existing add/delete/change machinery
(`findQuoteSurroundPair` already handles same-open/close characters by pairing occurrences on the cursor's line).
Letters and digits are intentionally excluded so Escape/cancel behavior is preserved and so letter-based vim-surround
targets (e.g. tag `t`) remain available for future work.

### Versioning

Bump `plugins/bob-vim-surround/manifest.json` from `1.2.0` → `1.3.0` (new character support is a feature plus a bugfix),
and update the version cells in `README.md` (the plugin table row and the line noting `bob-vim-surround` is ahead at
`1.2.0`).

## Out of Scope

- No new test framework. The repo intentionally has no test runner (only `node --check` via `npm run validate`); the
  unused `__test` export is left as-is.
- No new vim-surround features beyond literal-punctuation support (no tag `t`, function `f`, or `b`/`B`/`r`/`a`
  aliases).
- No changes to other plugins or to `bob plugins sync`.

## Verification

1. `npm run validate` (syntax check + manifest validation) passes.
2. Manual check in Obsidian Vim mode after `bob plugins sync`:
   - `ys2w)` on a line scrolled away from the top: cursor/viewport stays on the current line (no jump to top); text is
     wrapped correctly.
   - `ys2w?` wraps the two words in `?...?`.
   - `ds*` on `*bold*` removes the surrounding `*`.
   - `cs*_` changes `*x*` to `_x_`.
   - Existing pairs (`)`, `]`, `}`, `"`, `'`, `` ` ``) and Escape-to-cancel still behave as before.
