---
create_time: 2026-06-15 16:50:29
status: done
prompt: sdd/prompts/202606/hammerspoon_capture_delegation.md
---
# Plan: Delegate Hammerspoon Task Capture to `bob capture`

## Finding

The chezmoi Hammerspoon config has **not** been updated for the `bob capture` migration.

Evidence:

- `/home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua` still contains the old capture implementation:
  `normalizeTaskText`, `parseCapturedTaskTarget`, `insertTaskAfterLastOpenTask`, and direct `io.open` writes to `~/bob`.
- The file does not call `bob capture --format json`.
- `bob capture --help` works from the current environment via `/home/bryan/.cargo/bin/bob`, so the CLI dependency is
  available.
- The chezmoi source and applied target are currently identical (`~/.hammerspoon/init.lua` matches the source), and
  `chezmoi status` reports no drift. Updating the source and applying it is therefore the right path.

## Goal

Complete Phase 2 of the approved `bob capture` migration by thinning the Hammerspoon keymap:

- Keep the global hotkey, existing webview prompt, one-line paste normalization, focus save/restore, and notifications.
- Remove Markdown parsing, task formatting, route-file placement, and direct vault writes from Lua.
- Delegate capture asynchronously to `bob capture --format json -- <text>`.
- Preserve the current user-facing notification contract: title `Captured task`, subtitle route label when routed, and
  body text from the normalized capture result.

## Implementation Approach

1. Update `/home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua`.

2. Delete the old capture data-path helpers that now belong to Rust:
   - `normalizeTaskText`
   - `capturedTaskCreatedProperty`
   - `capturedTaskLine`
   - `routedCapturedTask`
   - `parseCapturedTaskTarget`
   - `readFile`
   - `writeFile`
   - `ensureFile`
   - `isIndentedTaskContinuation`
   - `isBlankMarkdownLine`
   - `nextNonBlankLineIsIndented`
   - `taskBlockInsertionPoint`
   - `insertTaskAfterLastOpenTask`
   - `appendCapturedTask`

3. Add a small async capture runner near the task-capture UI code:
   - Reuse the proven Bob Pomodoro launch pattern: `/bin/zsh -lc`, login shell, prepend
     `$HOME/bin:/opt/homebrew/bin:/usr/local/bin` to `PATH`, and set `DATE=gdate` when available.
   - Avoid shell interpolation of task text. Pass the raw prompt text as a positional argument after the `-c` command
     and call `exec bob capture --format json -- "$1"` inside the shell snippet.
   - Track the current `hs.task` in `taskCaptureTask` to avoid duplicate submissions while one capture is in flight.

4. Add robust callback handling:
   - Trim stdout/stderr for display.
   - On exit code `0`, decode stdout with `hs.json.decode`; if it is valid and `ok == true`, notify with
     `result.route_label` and `result.text`, then close the prompt and restore the previous app.
   - On non-zero exit, invalid JSON, or an `ok == false` JSON result, keep the prompt open and notify
     `Task capture failed` with the best available detail from JSON error, stderr, or stdout.
   - If the prompt is closed while a task is in flight, clear or terminate the tracked task so later callbacks cannot
     operate on stale prompt state.

5. Keep the existing webview behavior unchanged except for replacing the submit branch:
   - `cancel` still closes the prompt.
   - `submit` calls the async capture runner.
   - The prompt closes only after the CLI reports success.

## Verification

Automated/read-only checks available on this host:

- `luac -p /home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua`
- `chezmoi --source /home/bryan/.local/share/chezmoi diff`
- `chezmoi --source /home/bryan/.local/share/chezmoi status`
- `git -C /home/bryan/.local/share/chezmoi diff -- home/dot_hammerspoon/init.lua`
- A scratch-vault CLI smoke with `BOB_DIR=<tmp> bob capture --format json -- ...` to confirm the delegated command is
  still behaving before relying on it from Hammerspoon.

Manual checks that require the macOS Hammerspoon runtime:

- Apply the source (`chezmoi apply`) and let Hammerspoon reload.
- Exercise the hotkey for unrouted inbox capture, prefix route, suffix route, brand-new route file, and an existing
  route file with nested continuation lines.
- Confirm capture still works when GUI Obsidian is closed.

## Risks and Mitigations

- **Shell quoting**: arbitrary task text must not be evaluated by the shell. Mitigation: pass text as `$1`, not string
  interpolation.
- **Duplicate submissions**: async capture makes double-clicks possible. Mitigation: track `taskCaptureTask` and ignore
  new submissions while one is running.
- **JSON contract drift**: Hammerspoon depends on `route_label` and `text`. Mitigation: parse `ok`, `route_label`,
  `text`, and `error` defensively and report malformed output instead of closing the prompt silently.
- **Hammerspoon-only runtime APIs**: the local environment can syntax-check Lua but cannot fully exercise `hs.task` and
  `hs.webview`. Mitigation: keep the change small, reuse existing `hs.task` patterns, and leave explicit manual
  verification steps.
