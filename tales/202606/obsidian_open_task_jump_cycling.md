---
create_time: 2026-06-19 07:59:01
status: proposed
prompt: sdd/prompts/202606/obsidian_open_task_jump_cycling.md
---

# Plan: Cycle Ctrl+Shift+J/K Open-Task Navigation

## Goal

Update Bryan's Bob vault open-task navigation so the existing `<Ctrl+Shift+J>` and `<Ctrl+Shift+K>` keymaps cycle
through open Obsidian tasks in the current note instead of stopping at the file boundaries.

The intended behavior:

- `<Ctrl+Shift+J>` jumps to the next open Obsidian task below the cursor.
- If there is no lower open task, `<Ctrl+Shift+J>` wraps to the first open Obsidian task in the file.
- `<Ctrl+Shift+K>` jumps to the previous open Obsidian task above the cursor.
- If there is no higher open task, `<Ctrl+Shift+K>` wraps to the last open Obsidian task in the file.
- A `No next open task` or `No previous open task` notice is shown only when there are no matching open tasks, or when
  the only matching open task is already on the current cursor line.

## Context Reviewed

- Required Obsidian long-term memory was read through:
  `sase memory read obsidian.md --reason "Need Obsidian vault workflow context before planning navigation hotkey behavior changes"`.
- This changes the live Obsidian vault at `/home/bryan/bob`, not the Rust `bob-cli` implementation. No new CLI
  subcommands or options are planned, so `memory/long/cli_rules.md` does not apply.
- Vault rules from `/home/bryan/bob/AGENTS.md`: inspect vault git status before editing, preserve unrelated dirty files,
  and commit only task-related vault changes with `/sase_git_commit` before terminating after implementation edits under
  `~/bob`.
- Current vault status contains unrelated dirty note files and an unrelated `obsidian_vimrc.md` change. The plugin and
  hotkeys files are clean relative to the previous open-task-navigation commit.
- The existing open-task implementation lives in `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`.
- Existing task matching should remain unchanged: only Markdown checkbox list items with standalone `#task` and open
  status `[ ]`, `[/]`, or `[B]` are targets; done/canceled tasks, plain checklists, frontmatter, and fenced examples are
  ignored.
- Existing normal-mode fallback and hotkey bindings should remain unchanged. The change is behavioral, not a keybinding
  or command-registration change.

## Product Decisions

1. "Obsidian task" continues to mean the same open `#task` line recognized by the current helper. This plan does not
   broaden navigation to done tasks, canceled tasks, or ordinary checklists.

2. Cycling is circular across the complete filtered task list for the current file:
   - next from the last task goes to the first task;
   - previous from the first task goes to the last task;
   - next or previous from outside the task range chooses the wrapped boundary task rather than showing a no-target
     notice.

3. A cursor is considered to have the only task "already selected" when `cursor.line` equals that task line, regardless
   of cursor column. In that case the command should not reset the cursor to column 0 and should show the existing
   direction-specific no-target notice.

4. With exactly one matching task and the cursor on any other line, both next and previous should jump to that one task.
   This is the natural circular-list behavior and satisfies the rule that the toast is only for zero tasks or the
   one-task/current-line case.

5. The command notice text can remain exactly as today: `No next open task` and `No previous open task`. The difference
   is that these notices become rarer because file-boundary cases now wrap.

6. Section-header navigation remains strict and non-wrapping. This change is only for open-task navigation.

## Implementation Approach

### 1. Change the pure jump helper to be circular

Edit `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`.

Update `getOpenObsidianTaskJumpLine(lines, cursorLine, direction)` while preserving its public signature and exported
helper name:

- Normalize and validate `cursorLine` as it does today.
- Reuse `getOpenObsidianTaskLines(lines)` unchanged so frontmatter/fence skipping and task matching remain centralized.
- Return `null` when the cursor line is invalid or there are no matching open tasks.
- For `direction < 0`, first look for the nearest task line strictly less than `cursorLine`; if none exists, use the
  last task line as the wrap target.
- For forward direction, first look for the nearest task line strictly greater than `cursorLine`; if none exists, use
  the first task line as the wrap target.
- If there is exactly one task and the wrap or direct target equals `cursorLine`, return `null` so the caller shows the
  existing notice and leaves the editor untouched.
- Otherwise return the selected target line.

This keeps `jumpToOpenObsidianTask(editor, direction)` mostly unchanged: because the helper now only returns `null` for
the allowed no-target cases, the existing notice branch already matches the new behavior.

### 2. Keep command and keybinding surfaces stable

Do not change:

- `.obsidian/hotkeys.json`;
- `obsidian_vimrc.md`;
- command ids `jump-to-next-open-task` and `jump-to-prev-open-task`;
- the capture-phase Ctrl+Shift+J/K normal-mode fallback;
- `jumpToSectionHeader` or `getSectionHeaderJumpLine`.

If implementation review reveals a bug in the current keydown fallback that directly prevents cycling from working, fix
it only if required, and document it separately in the final summary. The expected change is a helper-only behavior
update.

### 3. Update focused helper and method tests

Use the same throwaway Node test strategy as the previous task: stub `obsidian` and `@codemirror/view` from `/tmp`, load
`bob-navigation-hotkeys/main.js`, exercise exported helpers and the method, then remove the temporary test files.

Cover these cases for `getOpenObsidianTaskJumpLine`:

- Zero matching tasks: next and previous return `null`.
- One matching task:
  - cursor before it: next and previous both return that task;
  - cursor after it: next and previous both return that task;
  - cursor on it: next and previous return `null`.
- Multiple matching tasks:
  - cursor before first: next returns first, previous wraps to last;
  - cursor on first: next returns second, previous wraps to last;
  - cursor between tasks: next and previous choose nearest strict targets;
  - cursor on middle task: next and previous skip the current line and choose neighboring tasks;
  - cursor on last: next wraps to first, previous returns the prior task;
  - cursor after last: next wraps to first, previous returns last.

Keep existing parser coverage:

- `isOpenObsidianTaskLine` truthy cases for `[ ]`, `[/]`, `[B]`, ordered lists, indentation, and blockquotes.
- False cases for `[x]`, `[X]`, `[-]`, missing `#task`, non-standalone `#taskish`, and non-list prose.
- `getOpenObsidianTaskLines` ignores leading frontmatter and backtick/tilde fenced blocks.

Cover `jumpToOpenObsidianTask` behavior:

- Successful wrap next from the last task moves the cursor to `{ line: firstTaskLine, ch: 0 }` and invokes
  `scrollEditorLineToTop`.
- Successful wrap previous from the first task moves to the last task and scrolls.
- One-task/current-line and zero-task cases leave the cursor unchanged and emit the existing direction-specific notice.
- One-task/not-current-line moves to the only task and does not emit a notice.

### 4. Validation

Run static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js
git -C /home/bryan/bob diff --check -- .obsidian/plugins/bob-navigation-hotkeys/main.js
```

Run the focused temporary Node test described above and report assertion counts.

Review the final task-related diff:

```bash
git -C /home/bryan/bob diff -- .obsidian/plugins/bob-navigation-hotkeys/main.js
git -C /home/bryan/bob status --short
```

Manual Obsidian smoke test, after reloading Obsidian or toggling the plugin:

1. In a scratch note with at least three open `#task` lines, place the cursor on the last matching task and press
   `<Ctrl+Shift+J>`; it should jump to the first matching task.
2. Place the cursor on the first matching task and press `<Ctrl+Shift+K>`; it should jump to the last matching task.
3. In a note with one open `#task`, verify pressing either key from another line jumps to it, while pressing either key
   while already on that task shows the no-target notice and does not move.
4. In a note with no open `#task` lines, verify the existing no-target notices still appear.
5. Confirm `<Ctrl+J>` and `<Ctrl+K>` still navigate section headers.

### 5. Vault hygiene and commit

Before implementation edits, re-check:

```bash
git -C /home/bryan/bob status --short
```

Expected implementation file changed:

- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`

No expected changes:

- `/home/bryan/bob/.obsidian/hotkeys.json`
- `/home/bryan/bob/obsidian_vimrc.md`
- vault notes
- memory files
- Rust `bob-cli` files

After implementation, commit only the task-related vault file with `/sase_git_commit`, per `/home/bryan/bob/AGENTS.md`,
leaving unrelated dirty notes and the unrelated vimrc hunk untouched.

## Risks And Mitigations

- **Accidentally jumping to the same line:** The one-task/current-line case must return `null`; tests should assert that
  the cursor and scroll are untouched.
- **Changing task recognition unintentionally:** Reuse `getOpenObsidianTaskLines` and avoid touching task regexes unless
  a test reveals a regression.
- **Expanding scope into keybindings:** The keymaps already exist and work through the current command path. Keep the
  change focused on jump target selection.
- **User/sync changes in the vault:** Inspect status before editing, review only the relevant plugin diff, and stage
  only the implementation file if a later implementation step is approved.
