---
create_time: 2026-06-01 11:24:14
status: done
prompt: sdd/prompts/202606/bob_help_redesign.md
---
# Bob `-h` Help Redesign Plan

## Context

The top-level `bob -h` / `bob --help` output is functional but plain, and the commands are listed in source-declaration
order rather than alphabetically. The user wants a drastically improved, _beautiful_ help screen, starting with
alphabetical command ordering but going well beyond that.

Current output:

```
Bob command-line tools

Usage: bob <COMMAND>

Commands:
  pomodoro           Show the current Bob Pomodoro status
  pomodoro-runtimes  Annotate Bob Pomodoro ledger entries with runtimes
  notify             Notify when the current Bob Pomodoro is complete
  sync               Sync the Bob Obsidian vault
  tmux-pomodoro      Print Bob Pomodoro status for tmux
  help               Print this message or the help of the given subcommand(s)

Options:
  -h, --help     Print help
  -V, --version  Print version
```

Problems with the status quo:

1. **Not sorted** — commands appear in `SUBCOMMANDS` declaration order (`pomodoro`, `pomodoro-runtimes`, `notify`,
   `sync`, `tmux-pomodoro`), not alphabetically. clap 4 preserves insertion order by default.
2. **Bland framing** — "Bob command-line tools" gives no sense of _what Bob is_ (Obsidian vault + Pomodoro workflow).
3. **No examples** — a newcomer has no copy-pasteable starting point.
4. **No discoverability footer** — nothing tells the user how to get per-command help.
5. **Flat styling** — default clap styling only; no deliberate color/emphasis design even though the `color`/`anstyle`
   support is already compiled in (clap 4.6.1, default features).

### Relevant code

- `src/runner.rs` — the single source of truth. `SUBCOMMANDS` (lines 15–46) is the `(name, script, about, native)`
  table; `build_cli()` (lines 157–169) assembles the clap `Command`; `delegate_subcommand()` (lines 171–182) builds each
  subcommand. All help layout flows from here.
- `Cargo.toml` — `clap = "4.5"` with default features (resolves to 4.6.1). `color`/`anstyle` are already available, so
  no dependency changes are required for styling.
- `tests/cli.rs` — integration tests invoking the real `bob` binary. There is currently **no** test asserting the
  top-level `bob -h` content, so ordering/regressions are unguarded.

## Design Direction

Keep clap as the rendering engine (robust, well-tested, handles wrapping/TTY detection/`NO_COLOR`) and shape a
deliberate, beautiful layout on top of it via four levers: **(a) alphabetical ordering**, **(b) richer about text**,
**(c) a custom `help_template` with an examples + footer block**, and **(d) an intentional color `Styles` palette**. No
new dependencies.

### 1. Alphabetical command ordering

Sort the command list so help renders `notify`, `pomodoro`, `pomodoro-runtimes`, `sync`, `tmux-pomodoro`. Two viable
mechanics; the plan uses the first:

- **Preferred:** reorder the `SUBCOMMANDS` array to be alphabetical by `name`, and add a guard (a unit test or a
  `debug_assert!` in `build_cli`) that fails if the array ever drifts out of sorted order. This keeps the source table
  itself self-documenting and avoids relying on clap internals.
- Alternative: assign `display_order` per subcommand from a sorted view. More indirection for no benefit here.

The synthetic `help` subcommand stays where clap places it (last), which is conventional.

### 2. Richer identity / about text

Replace `"Bob command-line tools"` with a short, accurate tagline that explains the domain, e.g.:

> `Bob — command-line tools for the Bob Obsidian vault and Pomodoro workflow`

Optionally add a `long_about` (shown only on `--help`, not `-h`) with a 1–2 sentence description of the vault/Pomodoro
workflow and the `bob <command>` convention. Per-command `about` strings will be reviewed for parallel, consistent
phrasing (imperative mood, no redundant "Bob").

### 3. Custom `help_template` with examples + footer

Use clap's `help_template` plus `after_help` to add two new sections the default layout cannot express:

- **Examples** — a few copy-pasteable invocations covering the most common entry points:
  ```
  Examples:
    bob pomodoro                 Show today's Pomodoro status
    bob sync                     Sync the Obsidian vault
    bob pomodoro-runtimes --check  Preview ledger runtime updates (no writes)
  ```
- **Footer** — a discoverability hint:
  ```
  Run 'bob <command> --help' for more information on a command.
  ```

The template will preserve the standard `{about}` / usage / `{all-args}` (Commands + Options) regions so clap still owns
alignment and wrapping; the Examples/footer come from `after_help`.

### 4. Intentional color palette

Define a `clap::builder::styling::Styles` palette so section headers and command/literal names are emphasized with
color, not just bold. clap already auto-disables color for non-TTY output and honors `NO_COLOR`, so this stays
terminal-friendly and CI-safe. The palette will be tasteful (e.g., headers in a bold accent color, command
names/literals in a second color) rather than loud.

### Scope boundaries (explicitly out of scope)

- **Per-subcommand help** (`bob pomodoro --help` currently forwards `--help` to the native binary, which errors for some
  commands). This is a real inconsistency but is a separate concern from the top-level screen; note it for a follow-up
  rather than expanding scope here.
- **Subcommand category grouping** (e.g. a "Pomodoro" group vs a "Vault" group). clap 4 has no first-class multi-heading
  grouping for subcommands; faking it requires hand-rolling the `{subcommands}` block and gives up clap's alignment
  guarantees. With only five commands, alphabetical + styling reads cleanly, so grouping is deferred unless the user
  specifically wants it.

## Implementation Phases

### Phase 1 — Ordering + content

- Reorder `SUBCOMMANDS` alphabetically by `name`; add the sorted-order guard test.
- Update the top-level `about` (and optionally `long_about`); normalize per-command `about` wording.

### Phase 2 — Layout + styling

- Add `help_template` + `after_help` (Examples + footer) in `build_cli()`.
- Define and apply the `Styles` color palette.
- Manually inspect `bob -h`, `bob --help`, `bob` (no args), and piped/`NO_COLOR` output to confirm it degrades cleanly.

### Phase 3 — Tests + docs

- Add `tests/cli.rs` coverage for `bob -h`: assert the commands appear in alphabetical order, that the Examples section
  and footer hint are present, and that output is stable (snapshot-style substring assertions, not brittle full-string
  matches). Assert non-TTY output contains no raw ANSI escape codes.
- Update `README.md` if its command framing should mirror the new tagline.

## Risks & Mitigations

- **Brittle snapshot tests** → assert on ordering and key substrings, not the entire help blob, so cosmetic wording
  tweaks don't break CI.
- **Color noise in pipes/CI** → rely on clap's built-in TTY detection + `NO_COLOR`; add a test asserting no ANSI escapes
  in captured (non-TTY) output.
- **Array drift** → the sorted-order guard test keeps `SUBCOMMANDS` alphabetical permanently.

## Acceptance Criteria

- `bob -h` lists commands in alphabetical order.
- The screen has an informative tagline, an Examples section, and a "per-command help" footer.
- Section headers / command names are color-emphasized on a TTY and plain (no ANSI) when piped or under `NO_COLOR`.
- New tests cover ordering, the Examples/footer presence, and ANSI-free non-TTY output; `cargo test` passes.
- No new dependencies added.
