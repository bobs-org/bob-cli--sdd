---
create_time: 2026-06-24 10:42:50
status: wip
prompt: sdd/prompts/202606/cancel_prompt_toast.md
---
# Plan: Smart "prompt cancelled" toast for the agent prompt input bar

> **Target repository:** `sase` (the ACE TUI). All paths below are relative to the `sase` repo root. This is **not** a
> `bob-cli` change.

## Problem & motivation

When the user cancels the agent prompt input bar (Esc-then-`Ctrl+C`, or `Ctrl+C`), the TUI always shows a
`Prompt input cancelled` toast — even when nothing meaningful happened:

- The prompt was empty.
- The prompt was a _trigger_, not a real prompt: `.` / `.x` (history pickers), or a VCS dot-prompt like `#gh:sase .`.
- The prompt was a single bare VCS xprompt workflow like `#gh:sase` (one token, dropped by the history word-count gate).

In all those cases the toast is pure noise: it interrupts, says nothing useful, and (in the bare-trigger cases) is
actively misleading because _nothing was saved_ — yet the toast implies something was discarded.

Conversely, when the user **does** cancel a real, multi-word prompt, that prompt **is** quietly preserved to prompt
history as `cancelled=True` (the "cancelled prompt preservation" safety net). But the toast says nothing about this, so
the user has no idea the text was saved or how to get it back.

This plan makes the toast _earn its place_:

1. **No toast** when the cancelled prompt was **not** stored to history.
2. **A useful toast** when it **was** stored — showing the (truncated) prompt and how to restore it via the `,>` keymap
   (`prompt_history (+cancelled)`).

This directly implements the user's standing TODO: _"Replace `Prompt input canceled` with no-op or message recommending
`,>` keymap."_

## Goals

- The toast appears **iff** the cancelled prompt was actually persisted to prompt history.
- When shown, the toast displays the cancelled prompt text (collapsed to one line, truncated with an ellipsis) and a
  hint pointing at the **actual configured** `,>` keymap to restore it.
- The decision is **reliable**: it is driven by the real storage outcome, not by a re-derived guess that could drift
  from the storage logic.
- The toast is **beautiful**: clean title, quoted preview, dimmed restore hint, robust against prompts that contain
  Rich-markup characters (`[`, `]`) or newlines.

## Non-goals

- Changing the _storage_ rules for cancelled prompts (what gets saved). Storage behavior is unchanged; we only stop
  lying about it and start surfacing it.
- Adding toasts to the other (silent) bar-dismissal paths — editor cancel (`Ctrl+G` → close empty), workflow-editor
  cancel (`Ctrl+Y`), and bar re-mount (selecting a different CL while the bar is open). Those intentionally stay quiet;
  re-mount especially must not toast. (Possible future follow-up, explicitly out of scope here.)
- The Plan-Feedback and Coder-Prompt (`approve_prompt`) cancel paths keep their existing behavior — they are handled
  before we reach the prompt-mode branch and are out of scope.

## Background: how cancellation works today

`PromptInputBar.action_cancel()` (`src/sase/ace/tui/widgets/prompt_input_bar.py`) posts a
`Cancelled(cancelled_text=<stripped>, mode="prompt")` message.

`PromptBarSubmitMixin.on_prompt_input_bar_cancelled` (`src/sase/ace/tui/actions/agent_workflow/_prompt_bar_submit.py`)
handles it. After routing `feedback` and `approve_prompt` modes away, the prompt-mode tail is:

```python
self.notify("Prompt input cancelled")   # always — the noise
self._unmount_prompt_bar()              # saves text automatically (as cancelled)
self._prompt_context = None
```

`_unmount_prompt_bar()` (`src/sase/ace/tui/actions/agent_workflow/_prompt_bar_mount.py`) is the **single choke point**
for every dismissal path. It calls `_save_bar_text_as_cancelled(bar)`, which:

1. Reads + strips the text area; returns early on empty.
2. Skips trivial triggers (`text in _TRIVIAL_PROMPT_PATTERNS` = `{".", ".x"}`).
3. Skips VCS dot-prompts (`text.startswith("#") and text.endswith((" .", " .x"))`).
4. Calls `add_or_update_prompt(text, ..., cancelled=True)`.

`add_or_update_prompt` (`src/sase/history/prompt.py`) has its **own** gate: it silently drops prompts shorter than
`_MIN_PROMPT_WORDS` (2 words) unless `allow_short=True`. This is exactly what drops a bare `#gh:sase` (one token) — and
it also returns nothing, so today the caller has no idea whether anything was saved.

**Key insight:** the set of "not stored to history" cases the user enumerated (empty, trigger-only, VCS-xprompt-only) is
_precisely_ the set of cases where `_save_bar_text_as_cancelled` short-circuits **or** `add_or_update_prompt` drops the
text. The most reliable way to gate the toast is therefore to **let the storage path report what it actually
persisted**, and drive the toast off that — rather than re-deriving the rules in the toast code (which would be a
correctness trap if the two ever diverge, e.g. if `_MIN_PROMPT_WORDS` changes).

## Design

### Decision 1 — Single source of truth: storage reports the outcome

Thread a return value up from the storage path so the cancel handler knows _exactly_ what was saved:

- `add_or_update_prompt(...) -> bool` — returns `True` iff the prompt was persisted (newly added or `last_used` updated
  and written to disk), `False` if it was skipped (too short) or the write failed. Today it returns `None`; this is a
  purely additive widening — every existing call site ignores the return value (verified: `launch_cwd.py`,
  `_launch_body.py`, `_prompt_bar_mount.py`, `_query.py`, and the new caller below).
- `_save_bar_text_as_cancelled(bar) -> str | None` — returns the text that was actually persisted (so the toast can
  display it), or `None` when nothing was stored (empty / trivial / VCS dot-prompt / too-short / write failed).
- `_unmount_prompt_bar() -> str | None` — returns `_save_bar_text_as_cancelled`'s result; `None` when the bar isn't
  present. All other callers ignore it.

This makes the toast a pure consequence of the real disk outcome — including the nice side effect that a disk-write
failure correctly yields **no** "saved" toast (we never claim to have saved something we didn't).

> Why not just inspect `event.cancelled_text` and re-apply the rules in the handler? Because that duplicates the storage
> gate (trivial patterns, VCS dot-prompt, the 2-word minimum, write success) in a second place. Two copies of a rule are
> one bug away from the toast lying. Driving off the actual outcome is the reliable choice the user asked for.

### Decision 2 — The cancel handler becomes outcome-driven

In `on_prompt_input_bar_cancelled`, the prompt-mode tail becomes:

```python
stored_text = self._unmount_prompt_bar()   # saves + reports what was persisted
if stored_text is not None:
    self._notify_cancelled_prompt_saved(stored_text)
self._prompt_context = None
```

No stored text → no toast (the user's "no-op"). Stored text → the new informative toast.

### Decision 3 — Toast content (intuitive + beautiful)

A new helper `_notify_cancelled_prompt_saved(text)` composes the toast:

- **Title:** `Cancelled prompt saved` — states what happened in three words.
- **Message:** the prompt **preview** on the first line (quoted), and a **dimmed restore hint** on the second:

  ```
  "refactor the launch_executor retry path so that…"
  ,> to restore
  ```

- **Severity:** `information` (default). **Timeout:** a touch longer than the default so the preview + hint are readable
  (≈5–6s).

Rendering rules that make it robust and pretty:

- **Preview** is built by a shared helper (Decision 4): newlines/CRs collapsed to spaces, trimmed, truncated to a max
  length with a trailing `…`.
- **Markup safety:** the toast uses Textual markup (so the hint can be dimmed), therefore the dynamic preview is passed
  through `rich.markup.escape(...)` — a prompt containing `[bold]` or `]` renders literally instead of corrupting the
  toast. (Matches the existing `escape(...)` pattern in `provider_styles.py`.)

### Decision 4 — Keymap-driven, customization-aware restore hint

The `,>` string is **not** hard-coded. It is rendered from the live keymap registry so it always reflects the user's
actual binding:

```python
from sase.ace.tui.keymaps import key_display_name
lm = self._keymap_registry.leader_mode
combo = key_display_name(lm.prefix) + key_display_name(lm.keys["prompt_history_cancelled"])
# default keymap → "," + ">" → ",>"
```

`prompt_history_cancelled` is the leader action that opens prompt history **including cancelled entries**
(`_leader_mode.py` → `_start_prompt_history_from_last_selection(show_cancelled=True)`), which is exactly where a
just-cancelled prompt is recoverable. (`,>` surfaces _all_ prompts including non-cancelled, so it is the correct hint
even for the edge case where the cancelled text already existed as a non-cancelled history entry.)

**Defensive fallback:** if the registry/key can't be resolved (e.g. unit-test apps without a wired registry), the helper
omits the restore hint and shows just the quoted preview — never crashes, never shows a stale/wrong key.

### Decision 5 — Shared preview/truncation helper (consistency + DRY)

`src/sase/history/prompt.py` already truncates prompt text for the fzf history view (`_format_prompt_for_display`:
collapse newlines → truncate at `_PROMPT_PREVIEW_LENGTH` (60) → `"..."`). Factor that into a small reusable
`format_prompt_preview(text, max_len=_PROMPT_PREVIEW_LENGTH) -> str` and use it both there and in the toast helper, so
the history picker and the toast truncate prompts identically. (Keeps "beautiful" consistent across surfaces; low-risk
pure function.)

## Implementation outline (by file)

1. **`src/sase/history/prompt.py`**
   - `add_or_update_prompt`: return `bool`. Short-circuit returns `False`; normal path returns the result of
     `_apply_prompt_mutations` (which already returns the disk-write success bool). Update the docstring to document the
     return contract.
   - Add `format_prompt_preview(text, max_len=_PROMPT_PREVIEW_LENGTH) -> str`; use it inside
     `_format_prompt_for_display`.

2. **`src/sase/ace/tui/actions/agent_workflow/_prompt_bar_mount.py`**
   - `_save_bar_text_as_cancelled` → return `str | None`: `None` on every skip branch; capture the `bool` from
     `add_or_update_prompt` (both the with-context and no-context branches) and `return text if stored else None`.
     (File-reference recording is unchanged.)
   - `_unmount_prompt_bar` → return `str | None`: propagate `_save_bar_text_as_cancelled`'s result; `None` when the bar
     is absent. `_unmount_prompt_bar_after_submit` is unchanged (still no save).

3. **`src/sase/ace/tui/actions/agent_workflow/_prompt_bar_submit.py`**
   - Rewrite the prompt-mode tail of `on_prompt_input_bar_cancelled` per Decision 2.
   - Add `_notify_cancelled_prompt_saved(self, text: str) -> None` (Decisions 3–4): compute the escaped preview via
     `format_prompt_preview`, compute `combo` from the keymap registry with a defensive fallback, and call
     `self.notify(message, title="Cancelled prompt saved", timeout=…)`.

## Behavior matrix (after the change)

| Cancelled bar text                      | Stored to history? | Toast                                            |
| --------------------------------------- | ------------------ | ------------------------------------------------ |
| `` (empty)                              | no                 | none                                             |
| `.` / `.x`                              | no                 | none                                             |
| `#gh:sase .` / `#gh:sase .x`            | no                 | none                                             |
| `#gh:sase` (bare VCS xprompt, 1 token)  | no (word-count)    | none                                             |
| `fix the retry path in launch …`        | yes (`cancelled`)  | `Cancelled prompt saved` + preview + `,>` hint   |
| text already in history (non-cancelled) | yes (`last_used`)  | toast (preview + `,>` hint; `,>` finds it)       |
| real text, but disk write fails         | no                 | none (we don't claim a save that didn't happen)  |
| long / multi-line / markup-y text       | yes                | toast with collapsed, truncated, escaped preview |

## Testing

- **`tests/history/test_prompt.py` / `test_prompt_cancelled.py`** — assert the new `add_or_update_prompt` return value:
  `False` for empty/single-word; `True` for a stored multi-word prompt (and the entry is present on disk); `False` when
  `_save_prompt_history` is patched to fail.
- **Unit test for `format_prompt_preview`** — newline collapse, truncation + `…`, short text untouched.
- **Unit test for `_save_bar_text_as_cancelled`** (fake bar/text-area, mirroring existing cancelled-save tests) —
  returns `None` for empty / `.` / `.x` / `#gh:sase .` / bare `#gh:sase`; returns the text for a real prompt.
- **Toast helper test** — feed a known leader keymap and assert the message contains the quoted, escaped, truncated
  preview and the rendered `,>`; assert the registry-missing path degrades to preview-only without raising.
- **Handler/integration test** (Textual `run_test()` pilot, following
  `tests/ace/tui/widgets/test_prompt_escape_cancel.py` and the `tests/ace/tui` harness): press `ctrl+c` and assert a
  notification is/ isn't emitted for the stored vs not-stored cases, by capturing `app.notify` (or inspecting the app's
  notification queue).

## Risks & mitigations

- **Return-type widening of a shared history API.** Mitigation: it's additive (`None` → `bool`); all existing call sites
  ignore the value (verified). No behavioral change for them.
- **Markup injection from arbitrary prompt text.** Mitigation: `rich.markup.escape` on the preview (Decision 3).
- **Keymap not resolvable in some contexts.** Mitigation: defensive fallback to preview-only (Decision 4).
- **Over-notifying.** Mitigation: scope strictly to the explicit prompt-mode cancel handler; the silent dismissal paths
  and feedback/approve_prompt modes are untouched (Non-goals).
