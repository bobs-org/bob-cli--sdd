---
create_time: 2026-06-07 06:15:47
status: done
prompt: sdd/prompts/202606/obsidian_backslash_daily_open_tab.md
---
# Plan: Reuse Open Daily Tab For Obsidian `\\`

## Goal

Change the Bob Obsidian Vim normal-mode `\\` mapping so the existing local Pomodoro jump behavior remains first, but the
daily-note fallback reuses an already-open daily note tab before opening today's daily file in the current leaf.

Desired behavior:

- If the current file has an active or completed Pomodoro target, `\\` jumps locally and keeps the existing centered
  scroll behavior.
- If the current file has no local Pomodoro target and today's daily note is already open in another Obsidian tab/leaf,
  `\\` activates that existing tab, then jumps to the Pomodoro target in that daily note if one exists.
- If the current file has no local target and today's daily note is not already open, keep the existing fallback
  behavior: use the Daily Notes command when available, then the path-based open/create fallback.
- If the current file already is today's daily note and has no target, keep the current no-target notice and avoid a
  self-reopen loop.

## Context Reviewed

- Project short memory: this is an ephemeral `bob-cli_<N>` workspace, so repo commands should stay anchored in the
  workspace clone.
- Obsidian long memory was read through the required audited command:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault and tab workflow context before planning changes to the backslash Obsidian keymap behavior"`.
- Vault instructions in `/home/bryan/bob/AGENTS.md`: inspect vault git status before edits, preserve unrelated dirty
  Obsidian Sync/user changes, and commit only task-related vault edits before terminating after file changes under
  `~/bob`.
- The relevant implementation is `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`, not `bob-cli` Rust code.
- The relevant vault paths are currently clean: `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`,
  `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/manifest.json`, and `/home/bryan/bob/.obsidian/daily-notes.json`.
- The vault has unrelated dirty files such as `.obsidian/hotkeys.json`, `task-status-cycler`, notes, and an untracked
  daily file. These should not be touched.
- Current `\\` mapping: `vim.mapCommand("\\\\", "action", "bobLedgerJumpToCurrentPomodoro", {}, { context: "normal" })`.
- Current fallback path: `jumpToCurrentPomodoro(cm)` calls `openDailyFallbackAndJump(error)` when
  `getJumpPomodoroTarget(lines)` returns no target.
- Current `openDailyFallbackAndJump(error)`:
  - suppresses fallback if the active file already is today's daily note;
  - calls `openTodayDailyNote(this.app)`;
  - reads the active daily editor;
  - reuses `getJumpPomodoroTarget` and `jumpToPomodoroTarget`.
- Current `openTodayDailyNote(app)`:
  - computes today's path with `todayDailyPath(...)`;
  - executes the Daily Notes command first;
  - waits for the active Markdown view at the daily path;
  - falls back to resolve/create plus `workspace.getLeaf(false).openFile(file)`.
- Existing helpers already cover most of the contract: `todayDailyPath`, `getDailyNotesOptions`, `sameVaultPath`,
  `getActiveMarkdownView`, `waitForActiveMarkdownView`, `getJumpPomodoroTarget`, `jumpToPomodoroTarget`, and
  `scheduleCenterOnLine`.

## Design

1. Preserve the current local-first control flow.
   - Do not change `getJumpPomodoroTarget` semantics.
   - Do not leave the current file when it has a valid local target.

2. Add a small workspace-leaf lookup helper.
   - Compute the expected daily path using the same `todayDailyPath(...getDailyNotesOptions(app))` logic as the current
     fallback.
   - Search all open Obsidian leaves before opening anything new.
   - Prefer `workspace.iterateAllLeaves((leaf) => ...)` because it can inspect existing tabs across panes.
   - Accept only Markdown leaves whose `leaf.view.file.path` matches the normalized daily path.
   - Ignore non-Markdown leaves, unloaded leaves without a file, and mismatched paths.
   - Keep the helper pure-ish and export it under `module.exports.helpers` for focused Node checks.

3. Add an activation helper for an existing leaf.
   - Prefer `workspace.revealLeaf(leaf)` if available, because it is intended to reveal an existing leaf.
   - Fall back to `workspace.setActiveLeaf(leaf, { focus: true })` when `revealLeaf` is unavailable.
   - If activation succeeds, wait with `waitForActiveMarkdownView(app, { path: dailyPath, attempts, delayMs })` before
     reading the editor, matching the current command/open timing guard.
   - Do not call `openFile` or the Daily Notes command when an existing leaf is found.

4. Integrate leaf reuse into the daily fallback.
   - Either update `openTodayDailyNote(app, options)` to check for and activate an existing daily leaf before executing
     the Daily Notes command, or add a new helper such as `openOrActivateTodayDailyNote`.
   - Keep a single public helper path so tests and `openDailyFallbackAndJump` exercise the same behavior.
   - Preserve the existing fallback sequence when no open daily leaf exists: Daily Notes command,
     `waitForActiveMarkdownView`, resolve/create, `getLeaf(false).openFile(file)`.

5. Keep notices and jump behavior unchanged.
   - Active file is today's daily note with no target: show the existing no-target message.
   - Daily tab activation/open fails: `Could not open daily note`.
   - Daily opens/activates but has no target: existing no-target message from `getJumpPomodoroTarget`.
   - Successful daily tab activation should still call `jumpToPomodoroTarget(view.editor, target)`, so cursor placement
     and centered-scroll scheduling remain unchanged.

## Implementation Scope

Expected file change:

- `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`

No expected changes:

- `bob-cli` Rust code or scripts.
- `.obsidian/hotkeys.json`, `.obsidian.vimrc`, plugin manifests, daily-note config, templates, or notes.
- Memory files.

## Verification

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js
jq '.' /home/bryan/bob/.obsidian/plugins/bob-ledger-tools/manifest.json
jq '.' /home/bryan/bob/.obsidian/daily-notes.json
```

Focused Node helper checks with stubbed Obsidian objects:

- Finds an open Markdown leaf whose `view.file.path` matches today's normalized daily path.
- Ignores non-Markdown leaves, leaves without files, and path mismatches.
- Activates an existing daily leaf via `revealLeaf` or `setActiveLeaf` and does not call the Daily Notes command.
- Falls back to the existing Daily Notes command/open-file path when no matching leaf exists.
- Keeps the active-daily/no-target guard in `openDailyFallbackAndJump`.
- After activating an existing daily tab, reads that tab's editor, finds the Pomodoro target, sets the cursor, and
  schedules the existing center behavior.

Manual live-vault acceptance checks:

- Open today's daily note in one tab, focus another non-daily note with no Pomodoro target, press `\\`, and confirm
  Obsidian switches to the existing daily tab rather than opening the daily note in the current tab too.
- Confirm the daily Pomodoro line is selected and centered after tab activation when a daily target exists.
- From a non-daily note that has its own Pomodoro target, press `\\` and confirm it jumps locally.
- With today's daily note not open, press `\\` from a non-daily note with no target and confirm the existing Daily Notes
  fallback still opens/creates today's daily note.
- From today's daily note with no target, confirm there is no self-reopen loop.

Status checks:

```bash
git status --short
git -C /home/bryan/bob status --short -- .obsidian/plugins/bob-ledger-tools/main.js
git -C /home/bryan/bob status --short
```

## Finalization

- Re-check vault status before and after editing.
- Leave unrelated dirty vault files untouched.
- If implementation changes `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`, commit only that task-related
  vault file with the required `/sase_git_commit` workflow before terminating after implementation.
- Report any validation that could not be run, especially live Obsidian checks if no GUI session is available.

## Risks

- Obsidian leaf activation may complete before the Markdown editor is attached. Mitigation: reuse
  `waitForActiveMarkdownView` after activation.
- Some open tabs may be unloaded or not expose `view.file`. Mitigation: treat them as non-matches and fall back to the
  existing open path.
- `revealLeaf` may not exist in some Obsidian versions. Mitigation: fall back to `setActiveLeaf`.
- Popout/window behavior may vary by Obsidian version. Mitigation: use `iterateAllLeaves` as the broadest available
  local workspace leaf scan, and keep manual acceptance focused on the user's real tab layout.
