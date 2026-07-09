---
create_time: 2026-06-11 12:38:22
status: done
prompt: sdd/prompts/202606/pomodoro_ctrl_enter_close_and_create.md
---
# Plan: Pomodoro "Close All and Create Next" Behavior for `<Ctrl+Enter>`

## Goal

Extend the existing Obsidian Vim normal-mode `<Ctrl+Enter>` task-completion keymap so that, when used to mark a
**Pomodoro task** as done, it additionally:

1. Marks every **transcluded** task sub-bullet (`- ![[note#^block-id]]`) under that Pomodoro as done in its source file
   — exactly as if `<Ctrl+Enter>` had been pressed on each of those sub-bullet lines.
2. Marks the Pomodoro task line itself as complete (the normal `<Ctrl+Enter>` behavior).
3. If this is the last Pomodoro task in the file, inserts a new placeholder Pomodoro line `- [ ] ()` below the current
   one.
4. Copies every **non-transcluded task-link** sub-bullet (`- [[note#^block-id]]`) from the current Pomodoro to the next
   Pomodoro (the newly created one, or the next pre-existing one) as sub-bullets. If a new Pomodoro had to be created
   and there are no such bullets to copy, a single empty sub-bullet is added under it instead.

Nothing special happens when re-opening a done Pomodoro task — that keeps the existing plain toggle behavior.

This implements the vault task `bob.md:38`:
`- [ ] #task Add "close all and create next pomodoro task” behavior to <ctrl+enter> behavior! ^close-and-create-pom-task`

## Context Reviewed

- Read `memory/short/sase.md` (ephemeral `bob-cli_<N>` workspace; no sibling repos).
- Long-term memory: only `memory/long/cli_rules.md` exists in this workspace, and it applies to new `bob-cli`
  subcommands/options. This task changes only a vault Obsidian plugin (no Rust CLI changes), so it is not required.
- Read `/home/bryan/bob/AGENTS.md`: inspect `git status` before editing, never touch unrelated pre-existing dirty files,
  commit only this task's vault changes via `/sase_git_commit` before finishing. The vault currently has many unrelated
  dirty files (including `bob.md`, `_templates/daily.md`, several `ref/chat/*` notes); the target plugin file
  `.obsidian/plugins/task-status-cycler/main.js` is currently **clean**.
- Inspected `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js` (the `<C-CR>`/`<C-Enter>` keymap owner) and
  `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js` (the Pomodoro/ledger conventions owner).
- Inspected real daily files (`/home/bryan/bob/2026/20260611.md`, `20260610.md`) for the exact Pomodoro section format.
- Reviewed the prior plans/tales for the existing `<Ctrl+Enter>` work (`sdd/tales/202606/ctrl_enter_task_completion.md`,
  `sdd/tales/202606/transcluded_ctrl_enter_tasks.md`).

## Current State

- `<C-CR>` / `<C-Enter>` (Vim normal mode) are registered by `task-status-cycler/main.js` and call
  `handleVimTaskToggleOpenDone()`, which:
  1. toggles the active line open/done when it is itself an open/done task (`toggleActiveCheckboxOpenDone()` →
     Tasks-plugin command for `#task` lines, local rewrite otherwise);
  2. otherwise attempts the transcluded-block toggle (`toggleActiveTranscludedTaskOpenDone()`), which resolves
     `![[note#^id]]` on the active line and rewrites the source task line in the other file (adding/removing
     `[completion:: YYYY-MM-DD]` for `#task` lines, keeping a trailing `^block-id` final).
- Pomodoro tasks live in daily notes under a `## Pomodoros (...)` heading as **top-level, unindented** task lines with
  **tab-indented** sub-bullets:

  ```md
  - [x] (**0655-0715** [t:: 20m])
    - [[gtd_daily]]
    - ![[bob#^delete-file-keymap]]
  - [ ] (**1205-1230** [t:: 25m])
    - [[bob#^close-and-create-pom-task]]
    - [[bob_projects#^review-gtd-projects-ref]]
  ```

  Sub-bullets are free-text notes, non-transcluded block-ID task links, or transcluded (`!`-prefixed) block-ID task
  links. Pomodoro lines do **not** carry the `#task` global filter tag.

- `bob-ledger-tools/main.js` already defines the vault's Pomodoro conventions this plan reuses:
  `POMODOROS_HEADING_RE = /^##\s+Pomodoros(?:\s.*)?$/`, section bounds ending at the next `## ` heading or EOF, and the
  `- [ ] ()` "placeholder" Pomodoro shape (`PLACEHOLDER_RE = /\(\s*\)/`), which its active-Pomodoro detection and the
  `se` time-range snippet already treat as a fillable Pomodoro line.
- `task-status-cycler` has no Pomodoro awareness today; toggling a Pomodoro line just flips `[ ]`/`[x]` locally.

## Product Decisions

1. **Scope the new behavior to the Vim `<Ctrl+Enter>` keymap, completion direction only.**
   - The special path triggers only inside `handleVimTaskToggleOpenDone()` when the active line is an **open** (`[ ]`)
     Pomodoro task, i.e. the toggle is about to mark it done.
   - Re-opening a done Pomodoro (`[x]` → `[ ]`) keeps the existing plain toggle: no sub-bullet edits, no copying, no new
     Pomodoro line.
   - The `toggle-task-open-done` command-palette command and all other keymaps stay unchanged.

2. **Pomodoro task detection mirrors `bob-ledger-tools` conventions, implemented locally.**
   - A line is a Pomodoro task when it is (a) inside the `## Pomodoros` section of the active file (heading matched with
     the same regex as `bob-ledger-tools`, section ending at the next `## ` heading or EOF), and (b) a top-level
     (unindented) task line.
   - The small heading/section helpers are duplicated into `task-status-cycler/main.js` rather than reaching into the
     other plugin's exports at runtime — consistent with how this plugin already keeps its line-parsing helpers
     self-contained, and avoids a fragile cross-plugin coupling for ~20 lines of code.
   - Placeholder Pomodoros (`- [ ] ()`) are Pomodoro tasks too: completing one runs the same flow.

3. **Sub-bullet classification (direct children of the Pomodoro line).**
   - The Pomodoro's sub-bullet block is the contiguous run of indented list lines immediately below it, ending at the
     first unindented line, blank line, or section end.
   - **Transcluded task-link bullet**: contains at least one embedded block link `![[...#^id]]` (reusing the existing
     `parseEmbeddedBlockTransclusions()` parser).
   - **Non-transcluded task-link bullet**: contains at least one plain (non-`!`) wikilink with a `#^block-id` subpath
     and no embedded block links. A new parser mirrors the embed parser minus the `!` prefix (and ignores `[[...]]`
     matches that are part of a `![[...]]`).
   - **Note bullet**: everything else — including plain-text notes (`- Plan [[bob_projects]]!`) and note links without a
     block ID (`- [[gtd_daily]]`). Note bullets are left in place and never copied.

4. **Transcluded sub-bullets are completed, never reopened, best-effort each.**
   - For each transcluded task-link bullet, resolve every embedded block link through the existing
     `resolveTranscludedBlockTarget()` machinery and rewrite the source line with the existing
     `rewriteTaskLineForTranscludedSource()` semantics, forcing the next symbol to `x` (done): `#task` sources gain
     `[completion:: YYYY-MM-DD]` before the trailing block ID; plain checklists only flip the checkbox.
   - A source task that is **already done is skipped** (not toggled back open). Sources with other statuses (`[/]`,
     `[-]`), non-task block targets, and unresolvable links are skipped silently.
   - One failing bullet never aborts the rest of the flow.

5. **The Pomodoro line completes through the existing toggle path.**
   - Pomodoro lines lack `#task`, so this is the plain local `[ ]` → `[x]` symbol swap (no completion metadata), same as
     today.

6. **"Next Pomodoro" selection and creation.**
   - The next Pomodoro is the first top-level task line after the current one within the Pomodoros section, regardless
     of its status.
   - If none exists, insert a new line containing exactly `- [ ] ()` immediately after the current Pomodoro's sub-bullet
     block.

7. **Copy semantics for non-transcluded task-link bullets.**
   - Matching sub-bullet lines are copied **verbatim** (preserving their tab indentation) and appended after the target
     Pomodoro's existing sub-bullets (for a new placeholder, they simply become its sub-bullets).
   - **Deduplication**: a bullet is not copied when the target Pomodoro already has a sub-bullet linking to the same
     resolved `(path, block-id)` target. Daily files show the same link carried across consecutive Pomodoros by hand
     today, so this prevents doubling up — and makes the whole operation idempotent if `<Ctrl+Enter>` is pressed, undone
     via reopen, and pressed again.
   - If a **new** Pomodoro was created and zero bullets were copied, add one empty sub-bullet under it instead, using
     the vault's sub-bullet convention: a tab-indented `- ` (tab, dash, space) so the cursor can drop straight into it.
     (The prompt wrote this as a line containing just ` -`; daily files indent sub-bullets with a tab, so the tab form
     is assumed to be the intent — flagged under Open Questions.)

8. **Edit ordering and safety.**
   - First await all transcluded-source completions (cross-file edits via the existing `vault.process()` path,
     active-editor `replaceRange` for same-file embeds), then recompute the daily-file restructuring from the
     now-current buffer and apply it bottom-up with editor `replaceRange` calls so line numbers stay stable.
   - The cursor stays on the current (now completed) Pomodoro line.
   - If the active line is an open task but **not** a Pomodoro task (no Pomodoros section, indented line, outside the
     section), behavior is exactly today's.

## Open Questions / Assumptions (for plan review)

- **Truncated requirement**: the prompt's second-to-last bullet reads only "Any non-transcluded task link bullet" and
  appears to be an abandoned fragment of the copy requirement already stated above it. This plan assumes it adds no
  extra behavior. If it was meant to say something else (e.g. "…should also be marked done" or "…should be removed from
  the completed Pomodoro"), say so on review and the plan will be adjusted.
- The empty sub-bullet is written as `<tab>- ` rather than the literal two characters ` -`, to match how every other
  sub-bullet in the daily files is indented.
- Copied bullets are **kept** on the completed Pomodoro (copied, not moved) — the done Pomodoro remains a faithful
  record of what was worked on.

## Implementation Scope

Expected vault file to edit:

- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js` (currently clean in `git status`)

No expected edits to:

- `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`, `bob-navigation-hotkeys/main.js`
- `/home/bryan/bob/.obsidian/hotkeys.json`, `/home/bryan/bob/.obsidian.vimrc`
- `bob-cli` Rust source, scripts, tests, README, or memory files
- vault notes, except optional scratch-note manual smoke testing after implementation

## Implementation Approach

1. **Pure helpers** (added near the existing line helpers in `task-status-cycler/main.js`, exported on
   `module.exports.helpers` for focused Node checks):
   - `findPomodorosSectionInLines(lines)` — heading + start/end bounds (mirrors `bob-ledger-tools`).
   - `isTopLevelTaskLine(lineText)` / Pomodoro-line predicate.
   - `getSubBulletBlockRange(lines, pomodoroLine)` — contiguous indented run below the Pomodoro line.
   - `parseNonEmbeddedBlockLinks(lineText)` — plain `[[...#^id]]` parser that skips embeds.
   - `classifyPomodoroSubBullets(lines, range)` — returns transcluded candidates, copyable bullet lines (verbatim text +
     parsed targets), and note bullets.
   - `findNextPomodoroLine(lines, section, afterLine)`.
   - `buildPomodoroCompletionPlan(lines, section, pomodoroLine)` — pure function returning the local edits to apply
     (status swap, optional placeholder insertion, copied bullet insertion with dedupe, optional empty sub-bullet) so
     the whole restructure is unit-testable without an editor.
2. **Plugin methods**:
   - `getActivePomodoroTaskContext(editor)` — detect the open Pomodoro line under the cursor.
   - `completeActivePomodoroTask(editor, activeFile)` — async orchestration: resolve + complete each transcluded target
     (reusing `resolveTranscludedBlockTarget` / `replaceResolvedTranscludedTaskLine` with a forced `x` symbol — refactor
     the small "next symbol" decision so it can be forced rather than toggled), then recompute and apply the local
     buffer edits bottom-up.
3. **Wire-up**: in `handleVimTaskToggleOpenDone()`, before the existing direct-task toggle, check for the open-Pomodoro
   context and route to `completeActivePomodoroTask()`; all other cases fall through to today's behavior unchanged.

## Acceptance Criteria

Given today's daily file shape, with the cursor on the last (open) Pomodoro:

```md
- [ ] (**1205-1230** [t:: 25m])
  - [[bob#^close-and-create-pom-task]]
  - [[bob_projects#^review-gtd-projects-ref]]
```

pressing `<Ctrl+Enter>` produces:

```md
- [x] (**1205-1230** [t:: 25m])
  - [[bob#^close-and-create-pom-task]]
  - [[bob_projects#^review-gtd-projects-ref]]
- [ ] ()
  - [[bob#^close-and-create-pom-task]]
  - [[bob_projects#^review-gtd-projects-ref]]
```

Additionally:

- A Pomodoro with transcluded sub-bullets (`- ![[bob#^id]]`) marks each resolvable open source task done in its source
  file with the same rewrite semantics as the existing single-line transcluded `<Ctrl+Enter>` path (completion field for
  `#task` lines, trailing block ID kept final); already-done, `[/]`/`[-]`, non-task, and unresolvable targets are
  skipped without aborting the rest.
- When another Pomodoro task already exists below, no `- [ ] ()` line is created and the non-transcluded task-link
  bullets are appended to that next Pomodoro's sub-bullets, skipping links it already contains.
- When a new `- [ ] ()` is created and there were no copyable bullets, it gets exactly one empty tab-indented `- `
  sub-bullet.
- Note bullets and transcluded bullets are never copied; all original sub-bullets remain under the completed Pomodoro.
- `<Ctrl+Enter>` on a **done** Pomodoro line just reopens it (no special behavior).
- `<Ctrl+Enter>` on non-Pomodoro task lines, on transcluded sub-bullet lines, and in files without a `## Pomodoros`
  section behaves exactly as today; `<CR>`, `<BS>`, `<C-]>`, `<C-S-]>`, `o`, `O`, `<C-d>`, `<C-u>` are untouched.

## Verification Plan

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js
git -C /home/bryan/bob diff --check -- .obsidian/plugins/task-status-cycler/main.js
```

Focused Node checks (same approach as the prior `<Ctrl+Enter>` work: stub `obsidian`, fake editor/vault/metadata cache,
drive the exported helpers):

- Pomodoros section detection, top-level Pomodoro line detection (timed and placeholder), sub-bullet block bounds.
- Non-embedded block-link parser: matches `[[bob#^id]]`, `[[folder/note#^id|alias]]`; ignores `![[bob#^id]]`,
  `[[gtd_daily]]`, `[[note#Heading]]`, malformed links.
- `buildPomodoroCompletionPlan`: last-Pomodoro → placeholder + copied bullets; existing next Pomodoro → append with
  dedupe; new placeholder with no copyable bullets → single empty sub-bullet; note/transcluded bullets never copied.
- Orchestration: transcluded sub-bullets each resolved and forced to done (open → done; done/other statuses skipped);
  one unresolvable bullet does not abort the others; reopen path takes the plain toggle.

Manual smoke test in the vault after a plugin reload (scratch daily-style note plus a scratch source note with `#task`
block-ID lines): complete a Pomodoro with mixed sub-bullet types as the last Pomodoro, again with a following Pomodoro
present, and reopen a done Pomodoro to confirm plain toggling.

Vault hygiene before finishing:

```bash
git -C /home/bryan/bob status --short
git -C /home/bryan/bob diff -- .obsidian/plugins/task-status-cycler/main.js
```

Commit only `.obsidian/plugins/task-status-cycler/main.js` (plus any scratch-note cleanup) via the `/sase_git_commit`
workflow, leaving the many unrelated pre-existing dirty vault files alone.

## Risks

- **Multi-file async edits**: completing several transcluded sources touches several files; each uses the existing
  serialized `vault.process()` path and re-validates the block line inside the write callback, so a stale metadata cache
  cannot rewrite the wrong line. Local daily-file edits are computed only after those writes settle.
- **Same-file embeds**: a transcluded sub-bullet pointing into the daily file itself would shift line numbers if handled
  carelessly; ordering external completions before recomputing the local restructure handles this.
- **Format drift**: Pomodoro detection deliberately keys off the section heading + top-level task shape (not the
  time-range ledger format), so placeholder Pomodoros and future ledger tweaks keep working; the regexes mirror
  `bob-ledger-tools` to stay aligned with the `se` snippet and `\p`/`\P` keymaps.
- **Obsidian Tasks recurrence**: as with the existing transcluded path, source-file rewrites use the local fallback
  semantics, not Tasks-plugin commands (which only act on the active editor). Recurring-task edge cases are out of
  scope, matching current behavior.
