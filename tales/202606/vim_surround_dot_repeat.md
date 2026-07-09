---
create_time: 2026-06-24 10:29:03
status: wip
prompt: sdd/prompts/202606/vim_surround_dot_repeat.md
---
# Plan: Dot-repeat (`.`) support for `ys` / `ds` / `cs` in `bob-vim-surround`

## Goal / Product context

The `bob-vim-surround` Obsidian plugin (linked repo `bob-plugins`, plugin id `bob-vim-surround`, file
`plugins/bob-vim-surround/main.js`) brings vim-surround style editing to Obsidian's Vim mode:

- `ys{motion}{char}` — **add** a surround around a motion (e.g. `ysiw)` → wrap inner word in `()`).
- `cs{target}{replacement}` — **change** an existing surround (e.g. `cs)]` → turn `(…)` into `[…]`).
- `ds{target}` — **delete** an existing surround (e.g. `ds"` → strip the `"…"`).

In real Vim, `vim-surround` integrates with `repeat.vim` so the `.` command repeats the last surround edit at the
current cursor location. That integration is **missing** here: pressing `.` after a surround does nothing useful (or
worse — see "Why it's broken today"). This plan adds faithful dot-repeat for all three operators so the muscle-memory
workflow works:

- `ysiw)` then move to another word, `.` → wrap that word in `()` too.
- `ds"` then move into another quoted span, `.` → strip those quotes too.
- `cs)]` then move into another `(…)`, `.` → change those parens to `[]` too.

Scope is **normal-mode** `ys`/`cs`/`ds` only (the plugin does not implement visual-mode `S`, so that is out of scope).

## Background: how the plugin works today

The plugin is plain CommonJS (no build, no bundler — `main.js` is the source). It drives Obsidian's Vim mode
(`@replit/codemirror-vim`, exposed as `window.CodeMirrorAdapter.Vim`) two different ways:

1. **`ys` is a hidden Vim operator.** It registers `vim.defineOperator("bobVimSurroundAdd", …)` mapped to the private
   key sequence `<A-b>s` (`SURROUND_OPERATOR_KEYS`). A capture-phase `keydown` listener on `window`/`document` watches
   for a physical `y` followed by `s` in normal mode and, instead of letting Vim's built-in `y` win, injects `<Esc>`,
   `<A-b>`, `s` into Vim via `vim.handleKey(cm, key, "mapping")`. The user's subsequent motion flows to Vim normally;
   Vim runs the operator callback `handleSurroundOperator`, which only **computes the target spans** and stashes them in
   `this.pendingSurround`. The actual surround characters are inserted later by `handlePendingSurroundKeydown` →
   `applySurround`, which reads the next physical keystroke (the surround char) and edits the doc with `cm.replaceRange`
   inside `cm.operation(...)`.

2. **`cs` and `ds` are NOT Vim operators.** When the listener sees `c`/`d` then `s`, it injects only `<Esc>` (to
   guarantee normal mode) and sets `this.pendingChangeSurround` / `this.pendingDeleteSurround`. The target char (and,
   for `cs`, the replacement char) are then read directly from subsequent physical keydowns
   (`handlePendingChangeSurroundKeydown` / `handlePendingDeleteSurroundKeydown`) and applied via `applyChangeSurround` /
   `applyDeleteSurround`, which locate the enclosing pair at the cursor (`findEnclosingSurroundPair`) and rewrite it
   with `cm.replaceRange`.

Single keydown entry point: `handleSurroundKeydown(event)` dispatches to the pending handlers, else to
`handlePhysicalSurroundTriggerKeydown` (the `y`/`c`/`d` → `s` detector). A `handledSurroundEvents` WeakSet de-dupes the
double delivery from the window+document listeners.

## Why `.` is broken today (the crux)

I traced CodeMirror Vim's dot-repeat (`@replit/codemirror-vim` `src/vim.js`) to understand exactly what `.` does:

- `.` is bound to the action `repeatLastEdit` (`vim.js` keymap). It reads `vim.lastEditInputState`; if absent it no-ops.
  For an **operator** edit, `lastEditActionCommand` is left `undefined`, so `repeatLastEdit` re-runs
  `commandDispatcher.evalInput(cm, vim)` with the stored `inputState` — i.e. it **re-applies the operator + motion at
  the current cursor**.
- `evalInput` records the last edit for **any** operator (`if (operator) recordLastEdit(vim, inputState)`), storing
  `inputState.operator` (= `"bobVimSurroundAdd"` for our operator) and the motion/args.
- During the repeat, `macroModeState.isPlaying` is `true` and `recordLastEdit` early-returns, so the stored edit is
  preserved across repeated `.`.

Consequences for the current code:

- **`ys`**: Vim _does_ record our operator. But the surround **character** is captured outside Vim (by our keydown
  listener) and `consumeEvent`'d, so Vim never sees it. A native `.` would therefore re-run only `<A-b>s`+motion → set
  `pendingSurround` again → **leave it dangling** (the next physical key gets eaten). Broken.
- **`cs` / `ds`**: these never run a Vim edit command (they only inject `<Esc>`), so Vim's `lastEditInputState` is
  stale/unrelated. Native `.` repeats some _other_ old edit (or nothing). Broken.

So in all three cases we must take ownership of `.` after a surround. The clean, architecture-consistent approach is a
**custom dot-repeat**, mirroring how `repeat.vim` gates on "did anything change since": we intercept `.` ourselves and
replay the last surround **only when the surround was the most recent document change**; otherwise we let `.` fall
through to Vim's native repeat.

## Technical design

### 1. Record the "last surround action" + a change-detection signature

Add two pieces of plugin state (init in `onload`, clear in `onunload`):

- `this.lastSurroundAction` — `null` or one of:
  - `{ type: "ys", cm, pair }`
  - `{ type: "cs", cm, targetKey, pair }` (pair = the _replacement_ surround pair)
  - `{ type: "ds", cm, targetKey }`
- `this.surroundDocSig` — a cheap "document version" captured right after the surround edit.

Change detection ("tick"), via a small helper `getDocSignature(cm)`:

- Primary: `cm.cm6.state.doc` — the CM6 `Text` object. Verified: its **identity changes only when the text changes**
  (selection-only transactions reuse the same `doc`), and `replaceRange`/`operation` dispatch synchronously, so the
  signature taken right after an edit is fresh. O(1).
- Fallback (if `cm.cm6` is ever unavailable): `cm.getValue()` (a string). Comparison uses `===`, which is identity for
  the `Text` object and value-equality for the string — correct either way.

Helpers:

- `recordLastSurroundAction(cm, action)` → set `lastSurroundAction` and `surroundDocSig = getDocSignature(cm)`.
- `clearLastSurroundAction()` → null both.
- `isSurroundStillLastChange(cm)` → `surroundDocSig !== null && getDocSignature(cm) === surroundDocSig`.

Wire the recording into the **success path** (just before `return true`) of the three existing apply methods so both the
initial edit _and_ each replay refresh the action + signature:

- `applySurround(...)` → `recordLastSurroundAction(cm, { type: "ys", cm, pair })`.
- `applyChangeSurround(...)` →
  `recordLastSurroundAction(cm, { type: "cs", cm, targetKey: pendingChangeSurround.targetKey, pair: replacementPair })`.
- `applyDeleteSurround(...)` → `recordLastSurroundAction(cm, { type: "ds", cm, targetKey })`.

(Recording only on success means a failed `cs`/`ds`, e.g. cursor not inside a matching pair, does not arm `.`.)

### 2. Intercept `.` in `handleSurroundKeydown`

After the existing pending-state checks and before `handlePhysicalSurroundTriggerKeydown`, add: if
`this.lastSurroundAction` is set, there is no in-flight `surroundTriggerCandidate`, and the key is a plain `.`
(`getPlainLowercaseKeyFromEvent(event) === "."`), call a new `handleSurroundDotRepeat(event)`; if it returns true, stop.
Otherwise fall through to the normal path (so a non-handled `.` still reaches Vim's native repeat). De-dup is already
handled at the top of `handleSurroundKeydown`.

### 3. `handleSurroundDotRepeat(event)`

```
cm = resolveEventNormalModeVimCm(event)            // null unless focused editor is in normal mode
action = this.lastSurroundAction
if (!cm || !action || action.cm !== cm) return false        // different editor → let Vim handle
if (!isSurroundStillLastChange(cm)) {                        // doc changed since the surround
    clearLastSurroundAction(); return false                 //   → defer to Vim's native '.'
}
if (action.type === "ys") {
    lastEdit = cm.state?.vim?.lastEditInputState
    if (!lastEdit || lastEdit.operator !== SURROUND_OPERATOR_NAME) return false   // see safety note
    consumeEvent(event); replayAddSurround(cm, action); return true
}
consumeEvent(event)
action.type === "cs" ? replayChangeSurround(cm, action) : replayDeleteSurround(cm, action)
return true
```

The **doc-signature gate** gives correct Vim semantics: after a surround, motions (`j`, `w`, `0`, …) do not change the
doc, so `.` replays the surround at the new cursor; but if a real edit happened after the surround (`x`, `dd`, an
insert, …), the signature differs and we hand `.` back to Vim so it repeats _that_ edit.

### 4. Replays

- **`cs` / `ds`** are fully self-contained — they operate on whatever pair encloses the _current_ cursor:

  ```
  replayChangeSurround(cm, action): injectVimKey(cm,"<Esc>",vim); applyChangeSurround({cm, targetKey: action.targetKey}, action.pair)
  replayDeleteSurround(cm, action): injectVimKey(cm,"<Esc>",vim); applyDeleteSurround({cm}, action.targetKey)
  ```

  The `<Esc>` injection mirrors the original `cs`/`ds` entry and clears any pending Vim count so we leave Vim in a clean
  normal state. Each apply re-arms `lastSurroundAction`/`surroundDocSig`, so `...` chains work.

- **`ys`** reuses Vim's own operator+motion replay (so counts, text objects, and `f`/`t` targets are handled for free)
  and only re-supplies the stored surround char:

  ```
  replayAddSurround(cm, action):
      this.pendingSurround = null
      injectVimKey(cm, ".", vim)        // Vim repeatLastEdit re-runs <A-b>s + motion → handleSurroundOperator sets pendingSurround
      pending = this.pendingSurround; this.pendingSurround = null
      if (pending) applySurround(pending, action.pair)   // re-applies stored char; re-arms action + signature
  ```

  `vim.handleKey` is synchronous all the way through
  `repeatLastEdit → evalInput → operators["bobVimSurroundAdd"] (= handleSurroundOperator)`, so `pendingSurround` is set
  by the time the inject returns. Injecting `.` is a direct JS call (not a DOM event), so it does not re-enter our
  keydown listener.

  **Safety note (why the extra `lastEditInputState.operator` guard for `ys`):** a few Vim commands rewrite
  `lastEditInputState` _without_ changing the document — notably yank (`yiw`) and entering+leaving insert mode with no
  typing (`i<Esc>`). After such a no-op-on-text command the doc signature still matches, but Vim's recorded edit is no
  longer ours, so injecting `.` would repeat the wrong thing. Guarding on
  `lastEditInputState.operator === "bobVimSurroundAdd"` detects this; when it fails we return `false` (don't consume)
  and let Vim's native `.` run — defensible graceful degradation.

### 5. Lifecycle

- `onload`: initialize `this.lastSurroundAction = null; this.surroundDocSig = null;`.
- `onunload`: null both (alongside the existing pending-state cleanup).

## Files to change (all in linked repo `bob-plugins`)

- `plugins/bob-vim-surround/main.js` — all logic above (new state, `getDocSignature` + record/clear/is-still-last
  helpers, `.` routing in `handleSurroundKeydown`, `handleSurroundDotRepeat`, three `replay*` methods, recording calls
  in the three `apply*` methods, lifecycle init/cleanup).
- `plugins/bob-vim-surround/manifest.json` — bump `version` `1.3.0` → `1.4.0`; extend `description` to mention `.`
  dot-repeat.
- `README.md` — update the `bob-vim-surround` row (version `1.3.0` → `1.4.0`, refreshed description).

No new files, no test framework, no build step (consistent with the repo's "edit `main.js` directly" model).
`npm run validate` must still pass (`node --check` on `main.js` + manifest sanity).

## Edge cases & known limitations (document in code comments / commit message)

- **Motions between surround and `.`** (`ysiw)` → `j` → `.`): doc unchanged → replays correctly. ✔
- **Real edit between surround and `.`** (`ds"` → `x` → `.`): signature differs → Vim's native `.` repeats the edit. ✔
- **Editor switch**: `action.cm !== cm` → defer to Vim. ✔
- **`ys` then yank / bare insert then `.`**: `lastEditInputState.operator` guard fails → defer to native `.` (does not
  misfire). Acceptable.
- **Count-prefixed dot (`3.`)**: best-effort. For `cs`/`ds` we apply once (and `<Esc>` clears the stray count); for `ys`
  Vim's `repeatLastEdit` runs the operator once for non-insert edits, so `3.` effectively behaves like `.`. Not a
  regression vs. today (where `.` does nothing).
- **Failed replay** (cursor no longer inside a matching pair on a `cs`/`ds` repeat): apply returns false, doc unchanged,
  state preserved; `.` is a harmless no-op.

## Rejected alternatives

- **Make `cs`/`ds` real Vim operators so native `.` "just works."** Rejected: it fights Vim's built-in `c`/`d` operators
  (the same reason `ys` already uses the hidden `<A-b>s` bridge and a keydown shim) and is a large rewrite. The
  custom-`.` approach matches the existing architecture.
- **Capture and replay the raw motion keystrokes for `ys` ourselves** (instead of injecting `.`). Rejected as
  unnecessary complexity: it requires reconstructing Vim key names (counts, `f`/`t` targets, text objects) from DOM
  events and a fragile recording lifecycle. Injecting `.` reuses Vim's motion engine and is gated safely by the
  `lastEditInputState.operator` check.

## Verification / QA

This logic is stateful and depends on the live Vim + CM6 runtime, so QA is manual in Obsidian (no headless harness
exists in this repo). After implementing:

1. `npm run validate` (from the `bob-plugins` repo) — must pass.
2. Deploy to the vault from the `bob-plugins` checkout: `bob plugins sync -p bob-vim-surround -r "$PWD" --dry-run` then
   without `--dry-run`; reload the plugin in Obsidian (the `bob plugins sync` default source path does not exist in a
   SASE workspace, hence `-r "$PWD"`).
3. Manual matrix in a Vim-mode note, in **both** Live Preview and Source mode:
   - **ys**: `ysiw)` → `w`/`j` to a new word → `.` wraps it in `()`. Repeat `...`. Try a different motion/char
     (`ysiw"`), a bracket pair with padding (`ysiw{`), a count (`ys2w)`), and a `t`/`f` motion (`yst,)`).
   - **ds**: `ds"` → move into another quoted span → `.` strips it. Try brackets `ds)`, repeat `...`.
   - **cs**: `cs)]` → move into another `(…)` → `.` changes it. Try `cs"'`, repeat `...`.
   - **Fall-through correctness**: `ysiw)` then `x` then `.` repeats the `x` (not the surround); `dd` then `.` repeats
     `dd`.
   - **No misfire**: in a fresh note with no prior surround, `.` behaves as plain Vim. Insert-mode typing then `.` is
     unaffected.
   - **Multi-pane**: surround in one pane, focus another, `.` does not replay the surround in the wrong pane.

## Versioning

Per the repo's per-plugin versioning, bump only `bob-vim-surround` to **1.4.0** (new user-facing feature); no other
plugin changes. Update the README table to match.
