---
create_time: 2026-06-19 10:14:25
status: proposed
prompt: sdd/prompts/202606/done_pomodoro_navigation.md
---

# Plan: Include Done Pomodoros in Ctrl+Shift+J/K Task Navigation

## Goal

Update the Bob vault `<Ctrl+Shift+J>` / `<Ctrl+Shift+K>` task navigation so Pomodoro ledger entries in a daily note's
`## Pomodoros` section are navigation targets when they are either open or done.

Ordinary Obsidian task navigation should remain open-only: done `#task` checkboxes outside the Pomodoro ledger should
still be skipped.

## Context Reviewed

- Required Obsidian long-term memory was read through:
  `sase memory read obsidian.md --reason "Need Obsidian vault/plugin workflow context before planning Pomodoro navigation changes"`.
- The prior approved plan is `sdd/tales/202606/ctrl_shift_jk_pomodoro_tasks.md`.
- Current implementation is in `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`, committed as
  `1d573cb feat(nav): include open Pomodoro lines in Ctrl+Shift+J/K navigation`.
- Current code already:
  - keeps ordinary `#task` matching in `isOpenObsidianTaskLine(...)`;
  - recognizes Pomodoro section state with `## Pomodoros`;
  - recognizes only top-level Pomodoro ledger lines, avoiding indented carried-forward child bullets;
  - skips leading frontmatter and fenced code blocks;
  - merges proper tasks and Pomodoro lines in file order with no duplicate for a line matching both;
  - keeps jump execution, wrapping, cursor movement, centering, command ids, and keymaps unchanged.
- The current Pomodoro filter is intentionally open-only: `OPEN_POMODORO_STATUSES = new Set([" ", "/"])`.
- `bob-ledger-tools` treats Pomodoro checkbox states as:
  - completed: `x` or `X`;
  - cancelled: `-`;
  - open: space or `/`.
- Recent daily notes contain completed Pomodoros such as `- [x] (**0705-0755** [t:: 50m])`, which are currently skipped
  by the navigation scanner.
- Current vault status has unrelated dirty files under `/home/bryan/bob`;
  `.obsidian/plugins/bob-navigation-hotkeys/main.js` is not dirty. Any implementation should touch and stage only that
  plugin file.
- No CLI subcommands or options are involved, so `memory/long/cli_rules.md` does not apply.

## Product Decisions

1. Broaden only Pomodoro ledger targets. Do not change ordinary `#task` semantics: regular done or cancelled tasks
   remain excluded from `<Ctrl+Shift+J/K>` open-task navigation.

2. A Pomodoro navigation target should be a top-level checkbox line inside an unfenced `## Pomodoros` section whose body
   carries a Pomodoro ledger shape: either an empty `()` placeholder or a recognized time range.

3. Pomodoro statuses included in the cycle should be:
   - open unchecked: `[ ]`;
   - open in-progress: `[/]`;
   - completed lowercase: `[x]`;
   - completed uppercase: `[X]`.

4. Cancelled Pomodoros (`[-]`) should stay excluded. The ledger plugin distinguishes completed from cancelled, and the
   user asked for done tasks rather than all historical Pomodoro entries.

5. Do not broaden matching to arbitrary top-level checkboxes in `## Pomodoros`. A line still needs a placeholder or a
   time range so section notes, accidental checklists, and malformed ledger rows are not added.

6. Preserve all navigation behavior after target collection:
   - next and previous use the same strict line ordering and circular wrap;
   - the cursor moves to column 0 of the target line;
   - centered scrolling and duplicate-dispatch dedupe remain untouched;
   - the existing no-target behavior remains for the case where the only matching target is already on the cursor line.

7. Update names and comments that currently say "open Pomodoro" where they would become misleading. Command-facing names
   such as `getOpenObsidianTaskJumpLine(...)` can remain stable because the user-facing command is still the open-task
   navigation command; the broadened Pomodoro subset should be documented at the helper/scanner level.

## Implementation Approach

If this plan is approved for implementation, edit only:

`/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`

### 1. Replace the Pomodoro status set

Change the Pomodoro-specific status constant from an open-only set to a navigation-target set, for example:

```js
const POMODORO_NAVIGATION_STATUSES = new Set([" ", "/", "x", "X"]);
```

Keep `OPEN_OBSIDIAN_TASK_STATUSES` unchanged for proper `#task` lines.

### 2. Rename or reshape the Pomodoro matcher

Rename `isOpenPomodoroTaskLine(...)` to a name that matches the new behavior, such as
`isPomodoroNavigationTaskLine(...)`.

The matcher should still:

- require `POMODORO_TOP_LEVEL_TASK_LINE_RE`;
- require a status from `POMODORO_NAVIGATION_STATUSES`;
- require `POMODORO_PLACEHOLDER_RE.test(body) || hasPomodoroTimeRange(body)`;
- leave `[-]`, `[B]`, malformed statuses, and indented child bullets unmatched.

Update the helper export list accordingly. A repository-wide search found no references outside
`bob-navigation-hotkeys/main.js`, so the old helper name does not appear to be consumed by another plugin.

### 3. Update the combined scanner and comments

Update `getOpenTaskNavigationLines(...)` to call the renamed Pomodoro matcher and revise comments from "open Pomodoro"
to "open or done Pomodoro" or "Pomodoro navigation target".

Keep the existing scan order and state machine:

- skip leading frontmatter;
- skip fenced code blocks;
- track `## Pomodoros` only on unfenced level-two headings;
- add normal `isOpenObsidianTaskLine(...)` matches first;
- otherwise add Pomodoro navigation matches only inside the Pomodoros section.

This preserves de-duplication: an open Pomodoro line that also has `#task` is still added once.

### 4. Leave command execution untouched

Do not change:

- keymaps or command ids;
- `.obsidian/hotkeys.json`;
- `obsidian_vimrc.md`;
- `jumpToOpenObsidianTask(...)`;
- `scheduleOpenTaskJumpCenter(...)`;
- Ctrl+Shift physical-key fallback;
- section-header navigation;
- dash-task navigation;
- project/task promotion helpers.

## Validation Plan

Run static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js
git -C /home/bryan/bob diff --check -- .obsidian/plugins/bob-navigation-hotkeys/main.js
```

Run focused throwaway Node tests with stubbed `obsidian` and `@codemirror/view`, then remove all temporary test files.

Parser and scanner cases:

- Existing proper-task true cases still pass: `- [ ] #task`, `- [/] #task`, `- [B] #task`, indented tasks, ordered
  tasks, and blockquoted tasks.
- Existing proper-task false cases still pass: done/cancelled proper tasks, missing `#task`, `#taskish`, prose,
  frontmatter examples, and fenced examples.
- Pomodoro true cases inside `## Pomodoros`:
  - `- [ ] ()`;
  - `- [/] (**0955-1020** [t:: 25m])`;
  - `- [x] (**0705-0755** [t:: 50m])`;
  - `- [X] (07:05-07:55)`;
  - a completed placeholder, if present, because `bob-ledger-tools` treats completed placeholder lines as valid jump
    candidates.
- Pomodoro false cases:
  - identical lines outside `## Pomodoros`;
  - indented carried-forward child bullets;
  - cancelled `[-]` Pomodoros;
  - blocked `[B]` Pomodoros without ordinary `#task` eligibility;
  - top-level open or done checkbox in `## Pomodoros` with neither time range nor `()`;
  - task-shaped lines in fenced blocks inside a daily note.
- Combined ordering:
  - regular open `#task`, open Pomodoro, done Pomodoro, and later open `#task` are returned in file order;
  - an open Pomodoro that also contains `#task` appears once;
  - a done Pomodoro containing `#task` is included by Pomodoro rules even though ordinary done tasks remain excluded.

Circular jump cases:

- From a normal open `#task`, next can land on a later completed Pomodoro.
- From a completed Pomodoro, next can land on a later open Pomodoro or open `#task`.
- Previous can land on completed Pomodoros.
- Next from the last target wraps to the first target, regardless of target kind.
- Previous from the first target wraps to the last target, regardless of target kind.
- A single completed Pomodoro on the current cursor line returns `null`, preserving the existing no-target path.

Manual smoke test after reloading or toggling `bob-navigation-hotkeys` in Obsidian:

1. Open a daily note such as `/home/bryan/bob/2026/20260619.md` that has both `[x]` and `[ ]` Pomodoros.
2. Use `<Ctrl+Shift+J>` and `<Ctrl+Shift+K>` to confirm the cycle visits completed and open Pomodoro lines in file
   order.
3. Confirm ordinary completed `#task` lines outside `## Pomodoros` are still skipped.
4. Confirm `[-]` Pomodoros and indented carried-forward child bullets are skipped.
5. Confirm centered scrolling still occurs after a jump.

Review final state:

```bash
git -C /home/bryan/bob diff -- .obsidian/plugins/bob-navigation-hotkeys/main.js
git -C /home/bryan/bob status --short
```

If implementation proceeds and is completed, commit only
`/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js` through the required SASE commit workflow, leaving
all pre-existing dirty vault files untouched.

## Risks And Mitigations

- **Accidentally including cancelled Pomodoros:** include only `x`/`X` in addition to the existing open statuses; keep
  `-` excluded and test it explicitly.
- **Misleading helper names after broadening behavior:** rename the Pomodoro-specific matcher and update comments around
  target collection.
- **Changing ordinary task semantics by accident:** leave `isOpenObsidianTaskLine(...)` and
  `OPEN_OBSIDIAN_TASK_STATUSES` unchanged and include regression tests for done `#task` exclusion.
- **Navigating non-ledger checkboxes in the Pomodoros section:** continue requiring `()` or a recognized time range.
- **Interfering with unrelated dirty vault files:** check vault status before and after implementation, and stage only
  the navigation plugin file if a later commit is requested or required.
