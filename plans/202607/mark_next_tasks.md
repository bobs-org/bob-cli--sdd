---
create_time: 2026-07-10 16:02:50
status: done
prompt: .sase/sdd/prompts/202607/mark_next_tasks.md
tier: tale
---
# Plan: `bob mark-next-tasks`

## 1. Product context

Bryan's Bob workflow captures actionable tasks and links them from today's daily note's Pomodoro ledger. During a work
session he wants a single, reliable command that re-derives the set of "next" tasks from what he has actually queued
under his open pomodoros — nothing more, nothing less.

`bob mark-next-tasks` makes today's daily note the **single source of truth** for which vault tasks carry the custom
**Next** status (`[*]`). It is a _sync_ command: after it runs, the set of `[*]` tasks in the vault equals exactly the
set of tasks that are block-linked from sub-bullets of **open** pomodoros in today's daily note.

Concretely:

- A task block-linked from a sub-bullet of an open pomodoro (`- [ ]`, not `- [x]`) is promoted to Next: `[ ]` → `[*]`.
- A task currently marked Next (`[*]`) that is **not** linked that way is reset: `[*]` → `[ ]`.
- A task already In Progress (`[/]`) is never touched, whether linked or not.
- Every other status (`[x]` done, `[-]` cancelled, unknown markers) is left alone.

The command must be intuitive, reliable, and produce beautiful, concise output. It is read-mostly and idempotent:
running it twice in a row is a no-op the second time.

### Status markers

Obsidian Tasks statuses used here (confirmed in the vault's `obsidian-tasks-plugin/data.json` and in `settings.rs`
defaults):

| Marker | Name                | Meaning in this command             |
| ------ | ------------------- | ----------------------------------- |
| `[ ]`  | Todo                | promotable to Next when linked      |
| `[*]`  | Next                | the status this command adds/clears |
| `[/]`  | In Progress         | never modified                      |
| others | done/cancel/unknown | never modified                      |

## 2. Scope

**In scope**

- New native subcommand `bob mark-next-tasks`.
- Parse today's daily note, find open pomodoros and their sub-bullet block links.
- Resolve each block link to the concrete task line it targets.
- Apply the promote/clear/leave-alone rules across the whole vault.
- `--dry-run`, `--format human|json`, `--bob-dir`, `--help`, matching the conventions of `bob capture` / `bob projects`.
- Beautiful colored human output + stable JSON output.
- Unit tests (in-module) and CLI integration tests + fixtures.
- Docs: `docs/mark-next-tasks.md`, README `## Commands` entry, help wiring, `justfile` install-smoke line.

**Out of scope**

- Git commit/push. Like `bob capture`, this command only edits notes locally; the user (or `bob nightly`) handles
  syncing. (Called out as a decision below.)
- Changing the Pomodoro ledger, creating block IDs, or editing links. This command only flips the single status
  character of existing task lines.
- Any interaction with a running Obsidian instance.

## 3. Behavior specification

### 3.1 Inputs

- **Vault root**: `--bob-dir` → `BOB_DIR` → `~/bob` (via `env::bob_dir`).
- **Daily note**: `pomodoro::day_file_for(&vault)`, which honors `BOB_DAY_FILE` and otherwise uses
  `<bob>/YYYY/YYYYMMDD.md` for "today" (respects `BOB_NOW`).
- **Global filter**: read `globalFilter` from `<vault>/.obsidian/plugins/obsidian-tasks-plugin/data.json`; default to
  `#task` when the file is missing/unreadable. A checkbox line is only treated as a task if its body contains this
  filter. This is what keeps the Pomodoro _ledger_ entries (`- [ ] Import Bob scripts (0900-0930)`) from being mistaken
  for tasks.

### 3.2 Reference extraction (open-pomodoro sub-bullet block links)

1. Read the daily note. Compute the Pomodoros section with `pomodoro::pomodoros_section_range`.
2. Walk the section tracking the current top-level ledger entry:
   - A non-indented line beginning with `-` is a ledger entry. It is **open** when `pomodoro::open_ledger_task` returns
     `Some` (i.e. not `- [x]`).
   - Indented lines belong to the most recent ledger entry's block.
3. For each indented sub-bullet under an **open** entry, extract every wiki link that carries a block fragment:
   `[[<target>#^<block-id>]]` (alias/heading-only links like `[[note]]` or `[[note#Heading]]` are ignored — only `#^id`
   links can point at a task). Embedded links mid-line count, matching how capture may render them.
4. Resolve `<target>` to a vault-relative note path (see 3.3) and record the desired reference `(note_path, block_id)`
   in a set (deduplicated).

### 3.3 Note-link resolution

Build a note index from scanned files (basename → unique path, plus the set of relative paths), mirroring the semantics
already used by `move-done-tasks`' `NoteIndex::resolve`:

- Exact relative path or `<path>.md` match wins.
- Otherwise resolve by unique basename (Obsidian's default), case-insensitively.
- Ambiguous basenames (same stem in two folders) do not resolve; reported as an unresolved reference rather than
  guessed.

### 3.4 Vault scan (candidate tasks)

Recursively scan vault Markdown, **excluding** `.`-prefixed dirs, `_generated`, `_templates` (via
`is_always_excluded_note_directory_name`) and `done/` archives — we never mutate templates or archived notes. For each
file, for each line, detect task lines: a list item (`-`/`*`/`+`/ordered) with a `[x]` checkbox whose body contains the
global filter. Record `(rel_path, line_index, status_char, status_char_byte_offset, trailing_block_id)`. The trailing
block id is the final `^<id>` token on the line (id bytes per `collect_done::is_block_id_byte`).

### 3.5 Transition rules

For each candidate task, `referenced = block_id.is_some() && desired.contains((rel_path, block_id))`:

- `status == ' '` and `referenced` → set to `'*'` (promote / "marked next").
- `status == '*'` and `!referenced` → set to `' '` (demote / "cleared").
- everything else → unchanged. This naturally satisfies "leave `[/]` alone", "referenced `[*]` stays next", and "never
  touch done/cancelled/unknown".

Bookkeeping for output/summary: count kept-already-next (referenced `[*]`), kept-in-progress (referenced `[/]`), and
collect unresolved references (target not found, or resolved but no task carries that block id).

### 3.6 Apply

Group changes by file; for each file with ≥1 change, rebuild contents by replacing the single status character in place
(indentation, list marker, body, trailing block id, and CRLF/LF endings all preserved) and write atomically (temp file +
rename). Files with no changes are not rewritten. `--dry-run` computes the full plan and prints it but writes nothing.

### 3.7 Guard rails (reliability)

Because this command clears status, two conditions **error out with no changes**:

- Daily note does not exist (we cannot compute the reference set).
- Daily note exists but has **no** `## Pomodoros` section (likely a half-written or malformed note — refuse rather than
  clear every Next task).

Within a valid Pomodoros section, the pure sync rule applies even if it yields an empty reference set (e.g. all
pomodoros closed → all `[*]` cleared); `--dry-run` plus the explicit output make this safe and predictable.

### 3.8 Edge cases

- Task referenced but currently `[/]` → left unchanged (spec); not counted as a clear.
- Task without a block id → can never be referenced → never promoted.
- A `[*]` checkbox lacking the global filter → not a task → never cleared.
- Same block id referenced by multiple open pomodoros → deduped by the set.
- Duplicate block ids on two task lines in one note → all matches promoted; surfaced as an ambiguity note (rare vault
  error).
- The daily note plays both roles (reference source + scanned file); it is read once and both uses share that content,
  so status edits to `#task` lines inside it never disturb the ledger sub-bullet links.

## 4. Output design

Uses the existing `style::Styler` (auto-detects TTY + `NO_COLOR`), matching the `bob capture` aesthetic. Palette per
`cli_rules`: green = promotions/success, yellow = clears + warnings, cyan = paths, dim = secondary detail.

**Human — changes made:**

```
✓ mark-next-tasks  2026/20260710.md
  2 open pomodoros · 3 references · 128 files scanned

  marked next
    [ ] → [*]  Write the design doc        dev.md ^design
    [ ] → [*]  Fix the parser              Projects/Alpha.md ^alpha-1
  cleared
    [*] → [ ]  Old thing                    Areas/Home.md ^home-3

  kept 1 already next · 1 in progress
Summary: 2 marked next, 1 cleared
```

**Human — already in sync:** `✓ mark-next-tasks  <daily> — already in sync, no changes`.

**Dry-run:** success prefix becomes `[dry-run] ok`; verbs read "would mark" / "would clear"; nothing is written.

Sections (`marked next`, `cleared`, `kept`) are omitted when empty. The `[ ] → [*]` markers and descriptions are
column-aligned with `style::pad_right`. Unresolved references are printed to **stderr** as `warning: ...` and do not
fail the run.

**JSON (`--format json`):** one stable object, modeled on `capture`'s serialized result — fields include `ok`,
`dry_run`, `daily_file`, `open_pomodoros`, `references`, `scanned_files`, `marked_next[]`, `cleared[]`, `kept_next`,
`kept_in_progress`, `unresolved_references[]` (each change item: `path`, `line_number`, `block_id`, `description`).
Human diagnostics never contaminate the JSON on stdout.

**Exit codes:** `0` success (incl. dry-run and no-op); `1` I/O error or guard-rail failure (missing daily note / missing
Pomodoros section); `2` CLI usage error (clap).

## 5. Technical design

### 5.1 New module `src/native/mark_next.rs`

Self-contained, following the `capture.rs` / `projects.rs` pattern (own clap CLI, own result structs, own `#[cfg(test)]`
suite). `COMMAND_NAME = "bob mark-next-tasks"`.

Reuses existing `pub(crate)` helpers rather than re-implementing them:

- `pomodoro::{pomodoros_section_range, open_ledger_task, day_file_for}` — ledger parsing and daily-note location.
- `collect_done::is_block_id_byte` — block-id character class.
- `style::{Styler, pad_right, display_width}` — output.
- `env as bob_env` — vault root, current date.
- `super::is_always_excluded_note_directory_name` — directory exclusion.

New small local helpers (kept local because the equivalents in `collect_done` / `projects` are private and tuned to
those commands): a Markdown file walker, a task-line parser (list marker + status char + body + trailing block id), a
block-link extractor that keeps the `#^id` fragment, a basename note index, the global-filter reader, and an atomic
write. These mirror existing idioms closely.

Rationale for **not** reusing `dataview::tasks::TaskIndex`: that lives inside the ~7k-line `dataview` module behind
`pub(super)` visibility and produces a rich Task model (dates, urgency, dependencies) with no editing surface. Wiring it
out would add large coupling for little gain. The codebase norm is that `capture` and `collect_done` each do focused
line-level parsing for their edits; this command follows that norm. (Reusing `TaskIndex` is noted as a considered
alternative.)

Status markers are pinned constants (`' '`, `'*'`, `'/'`) per the explicit spec, for predictability. (Deriving the Next
symbol from Tasks config by status name is a considered alternative, rejected to avoid fragile name matching.)

### 5.2 Wiring

- `src/native.rs`: add `mod mark_next;`, add `NativeCommand::MarkNextTasks`, and a dispatch arm
  `NativeCommand::MarkNextTasks => mark_next::run(args)`. No `command_for_script` mapping (native-only, like
  capture/projects).
- `src/runner.rs`: add a `SUBCOMMANDS` entry `mark-next-tasks` (`script_command: None`), placed alphabetically between
  `highlights` and `move-done-tasks` (the `subcommands_are_sorted_alphabetically` test guards this), about text e.g.
  "Sync Next-status tasks from today's open pomodoros". Add an `AFTER_HELP` example line.
- `justfile`: add `bob mark-next-tasks --help` to `install-smoke`.

### 5.3 Help text

`-h/--help` per `cli_rules`: clear usage, long description of the sync semantics and guard rails, an `environment:`
block (`BOB_DIR`, `BOB_DAY_FILE`, `BOB_NOW`), and options listed **alphabetically**, each with a short alias, matching
capture: `-b/--bob-dir`, `-d/--dry-run`, `-f/--format`, `-h/--help`.

## 6. Testing strategy

### 6.1 In-module unit tests (`mark_next.rs`)

- Reference extraction: open vs closed pomodoro; multiple sub-bullet links; embedded link mid-line; alias/heading-only
  links ignored; links under a closed pomodoro ignored.
- Note resolution: bare basename, subfolder path, `.md` suffix, ambiguous stem unresolved.
- Transition matrix: `[ ]`+ref→`[*]`; `[*]`+noref→`[ ]`; `[/]` untouched (ref and non-ref); `[x]`/`[-]`/unknown
  untouched; already-`[*]`+ref unchanged; `[ ]` without block id never promoted.
- Global-filter gating: a `[*]` checkbox without `#task` is ignored; ledger `[ ]` entries never promoted.
- Status-char replacement preserves indentation, list marker, trailing block id, and CRLF; only the target line changes.
- Guard rails: missing daily note and missing Pomodoros section both error and write nothing.
- Idempotency: applying the plan twice yields no second-run changes.

### 6.2 CLI integration tests (`tests/cli.rs`)

- `mark_next_tasks_help_is_native_only` (mirrors the other native-help tests: no script assets extracted;
  `usage: bob mark-next-tasks` present).
- Options-listed-alphabetically help test (mirror capture's).
- Extend `all_top_level_subcommand_help_is_safe_and_plain` / `public_help_surfaces_do_not_list_long_only_options`
  coverage to include the new subcommand.
- End-to-end against a temp vault: daily note with one open + one closed pomodoro, sub-bullet block links into target
  notes carrying `[ ]`, `[*]`, `[/]`, and an orphan `[*]`; assert files are updated correctly, human output, `--dry-run`
  leaves files byte-identical, and `--format json` shape.

### 6.3 Fixtures

Add `tests/fixtures/mark_next/` with a daily note (open + closed pomodoros, block links) and a couple of target notes
exercising every transition. Keep fixtures small (runner tests copy them into a temp vault, per existing convention).

## 7. Documentation

- New `docs/mark-next-tasks.md` following the one-file-per-command style (`docs/projects.md`), covering semantics, guard
  rails, examples, and JSON shape.
- README `## Commands`: add a `bob mark-next-tasks` subsection (usage line + a short worked example), and mention it
  where `BOB_DAY_FILE` / `BOB_NOW` are documented in `## Environment`.

## 8. Risks & mitigations

- **Accidental mass-clear.** Mitigated by the missing-note / missing-section guard rails, `--dry-run`, and explicit
  per-change output.
- **Mis-identifying pomodoro ledger entries as tasks.** Mitigated by requiring the global filter on task lines; ledger
  entries lack `#task` and have no block id.
- **Link-resolution mismatches.** Mitigated by Obsidian-faithful basename resolution and by surfacing unresolved
  references as warnings instead of silent no-ops.
- **Touching archives/templates.** Mitigated by excluding `done/`, `_generated`, `_templates`, and dot-directories from
  the scan.

## 9. Definition of done

- `bob mark-next-tasks [--dry-run] [--format human|json] [--bob-dir DIR]` works end-to-end with the specified sync
  semantics and guard rails.
- Beautiful, concise human output; stable JSON output; excellent `--help`.
- Unit + CLI tests and fixtures pass; `just all` (fmt, clippy, test) is clean.
- Docs, README, help wiring, and `justfile` install-smoke updated.
