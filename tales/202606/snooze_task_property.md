---
create_time: 2026-06-02 20:20:12
status: wip
prompt: sdd/prompts/202606/snooze_task_property.md
---
# Plan: `snooze` Task Property Support

## Goal

Add support for a Dataview-style Obsidian Tasks inline field:

```markdown
[snooze:: YYYY-MM-DD]
```

The daily Tasks query should include tasks that either have no valid `snooze` date or have a `snooze` date greater than
or equal to the relevant daily-note date. Add a native `bob rm-snooze` command that removes qualifying `snooze` fields
from task lines in the Bob vault, commits and pushes those removals, and runs first in `bob cronjob`.

Important semantic assumption: this plan implements the comparison exactly as requested: `snooze_date >= current_date`.
That means a task snoozed to today or the future is included by the query and has its `snooze` field removed by
`bob rm-snooze`; a task with a past `snooze` date is left alone. If the intended meaning is the more common "hide until
date" behavior, the comparison should be flipped to `snooze_date <= current_date` before implementation.

## Context Reviewed

- Project memory was read through:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault and task workflow context before planning snooze task property support"`.
- The Bob vault is `/home/bryan/bob`. Its `AGENTS.md` says the vault is actively synced, to inspect `git status` before
  edits, to avoid staging/committing unrelated changes, and to commit vault edits via `/sase_git_commit` before
  terminating after vault file changes.
- `git -C /home/bryan/bob status --short` was clean at plan time.
- The live daily template is `/home/bryan/bob/_templates/daily.md`.
- Today's daily file for 2026-06-02 is `/home/bryan/bob/2026/20260602_day.md`.
- Both files currently have the same `tasks` query, including existing JavaScript filters over `task.originalMarkdown`,
  `task.scheduled`, and `query.file.filenameWithoutExtension`.
- The installed Tasks plugin is `obsidian-tasks-plugin` version `8.0.0`, with `taskFormat: "dataview"` and
  `globalFilter: "#task"`.
- Official Tasks documentation confirms Dataview task format supports inline fields like `[scheduled:: YYYY-MM-DD]`, and
  custom filters can use `task.originalMarkdown` when Tasks does not parse a value as a built-in property.

## Query Changes

Update the `tasks` code block in both:

- `/home/bryan/bob/_templates/daily.md`
- `/home/bryan/bob/2026/20260602_day.md`

Add a `filter by function` line after the existing scheduled-date filter and before the `[p:: N]` suppression filter.

The filter should:

1. Look for a bracketed Dataview inline field with an ISO date: `[snooze:: YYYY-MM-DD]`.
2. Treat missing or malformed `snooze` fields as absent and include the task.
3. Compare the parsed date against the note date derived the same way the current scheduled-date filter does:
   `moment(query.file.filenameWithoutExtension, "YYYYMMDD[_day]")`.
4. Include the task only when no valid snooze exists or when the snooze date is greater than or equal to the query date.

Implementation shape:

```tasks
filter by function (() => { const snooze = task.originalMarkdown.match(/\[snooze::\s*(\d{4}-\d{2}-\d{2})\]/); return !snooze || moment(snooze[1], "YYYY-MM-DD", true).isSameOrAfter(moment(query.file.filenameWithoutExtension, "YYYYMMDD[_day]"), "day"); })()
```

Use the query file date rather than wall-clock `moment()` so the template works for any daily note, while today's file
naturally evaluates against 2026-06-02.

## New Native Command

Add a new native-only subcommand:

```bash
bob rm-snooze
```

Wire it through the same command surfaces as existing native commands:

- Add `mod rm_snooze;` and `NativeCommand::RmSnooze` in `src/native.rs`.
- Add a `rm-snooze` entry to `SUBCOMMANDS` in `src/runner.rs`. Alphabetical position: after `pomodoro` and before
  `sync`.
- Add a top-level help example and README command documentation.
- Implement `src/native/rm_snooze.rs`.

Standalone command behavior:

1. Resolve the vault with `bob_env::bob_dir()`.
2. Use `bob_env::current_datetime().date()` as the current date, so tests can use `BOB_NOW` and runtime behavior matches
   other date-aware commands.
3. Recursively scan markdown files in the vault, skipping `.git/` and `.obsidian/`. Include `done/` unless
   implementation review reveals a strong reason to exclude it, because the user asked for any Task in the vault.
4. Only edit Markdown task lines, identified with the existing broad task-line shape: list marker, checkbox, then task
   text. Do not remove inline fields from ordinary prose, code blocks, or non-task list items.
5. On each task line, find bracketed fields matching `[snooze:: YYYY-MM-DD]` with optional whitespace after `::`.
6. Remove every valid `snooze` field whose date is greater than or equal to the current date. Leave malformed dates and
   past-date fields unchanged.
7. Preserve line endings and other task properties. Trim only the local spacing made awkward by deleting the field.
8. Build a plan first, then check candidate-file git status before writing. If any candidate file is already dirty,
   refuse to modify it and print the candidate paths, matching the safety model used by `collect-done`.
9. Atomically write changed files.
10. If no files need changes, print a no-op summary and skip git work.
11. If files changed, require a Git worktree, stage only the changed files, commit with `bob rm-snooze YYYY-MM-DD`, and
    push using `ob::git_command(...)` with the shared `ChildEnv`.

I will keep the first implementation local to `rm_snooze.rs` and reuse only the shared `ob::git_command`,
`ob::child_env`, and date/environment helpers. I will avoid refactoring `collect_done.rs` unless the new code needs a
helper that is clearly worth extracting.

## Cronjob Integration

Update the step registry in `src/native/cronjob.rs` so the nightly order is:

1. `rm-snooze` - remove current/future snooze fields.
2. `collect-done` - archive done and canceled tasks.
3. `sync` - commit and push any remaining vault changes.

The shared `ob sync` gate remains first, before all wrapped steps. Wrapped step failure behavior stays unchanged: later
steps still run, and `cronjob` exits non-zero if any step failed. The step count and summary should naturally update
from 2 to 3.

## Tests

Add focused unit tests in `src/native/rm_snooze.rs` for:

- missing `snooze` field leaves the task unchanged;
- `snooze` equal to current date is removed;
- future `snooze` is removed;
- past `snooze` is retained, per the requested `>=` semantics;
- malformed `snooze` values are retained/ignored;
- non-task lines are unchanged;
- multiple `snooze` fields on one task line are handled independently;
- other inline fields such as `[scheduled:: ...]`, `[p:: 1]`, and block ids are preserved;
- CRLF line endings are preserved.

Add integration coverage in `tests/cli.rs` for:

- `bob rm-snooze --help` is native-only and does not extract fallback scripts.
- `bob rm-snooze` removes only qualifying `snooze` fields, commits only touched vault files with subject
  `bob rm-snooze YYYY-MM-DD`, and pushes to the bare remote.
- unrelated dirty files remain dirty and are not included in the `rm-snooze` commit.
- dirty candidate files cause refusal before mutation.
- no qualifying snooze fields produces a successful no-op with no new commit.
- top-level help remains alphabetically sorted and includes `rm-snooze`.
- `cronjob` happy path runs shared sync once, then `rm-snooze`, `collect-done`, and `sync` in that order; expected
  commit order is newest `sync`, then `collect-done`, then `rm-snooze`.
- existing cronjob failure tests are updated for three steps, including the guarantee that a failing wrapped step still
  allows later steps to run.

## Documentation

Update `README.md` to document:

- `bob rm-snooze`;
- accepted field syntax: `[snooze:: YYYY-MM-DD]`;
- literal cleanup semantics: removes fields whose date is greater than or equal to the command's current date;
- Git behavior: path-specific stage, commit, push; no-op when there are no qualifying fields; refusal on dirty candidate
  files;
- `bob cronjob` now runs `rm-snooze` first.

If command examples or release smoke tests list core commands, add `bob rm-snooze --help` where appropriate.

## Verification

Run repository checks:

```bash
cargo fmt --check
cargo test
cargo clippy --all-targets --all-features
```

Run command smoke checks:

```bash
cargo run -- rm-snooze --help
cargo run -- cronjob --help
```

For vault files:

1. Check `git -C /home/bryan/bob status --short` again immediately before editing.
2. Edit only `/home/bryan/bob/_templates/daily.md` and `/home/bryan/bob/2026/20260602_day.md`.
3. Verify both Tasks query blocks have the new snooze filter in the same place.
4. Commit only those vault files through `/sase_git_commit`, as required by the vault instructions.

Optional real-vault smoke after installing the local binary:

```bash
BOB_NOW=2026-06-02 bob rm-snooze
```

Only run the real command after reviewing `git -C /home/bryan/bob status --short`, because it intentionally commits and
pushes qualifying vault edits.
