---
create_time: 2026-06-01 10:06:38
status: done
prompt: sdd/prompts/202606/bob_cli_migration_3.md
bead_id: bob-cli-1
tier: epic
---
# Bob CLI Migration Plan

## Context

`~/bob/` is the active Obsidian vault. The current Bob command logic lives in the chezmoi source tree, mostly under
`~/.local/share/chezmoi/home/bin`, while this `bob-cli` repo currently has no Rust crate or script assets.

The Bob-specific executable candidates found in chezmoi are:

- `home/bin/executable_bob_pomodoro`
- `home/bin/executable_bob_pomodoro_runtimes`
- `home/bin/executable_bob_notify`
- `home/bin/executable_bob_sync`
- `home/bin/executable_tmux_bob_pomodoro`

Adjacent Bob integration code also exists in Hammerspoon, tmux, and Neovim config/tests:

- `home/dot_hammerspoon/init.lua`
- `home/dot_config/tmux/tmux.conf`
- `home/dot_config/nvim/lua/config/bob_keymaps.lua`
- `home/dot_config/nvim/lua/config/bob_pomodoro_keymaps.lua`
- `home/dot_config/nvim/lua/plugins/obsidian.lua`
- `home/dot_config/nvim/tests/bob_keymaps_spec.lua`
- `home/dot_config/nvim/tests/bob_pomodoro_keymaps_spec.lua`

No Bob-specific shell test file was found in the inspected chezmoi tree. Existing Neovim Lua tests cover editor behavior
around Bob paths and Pomodoro note editing, but the CLI migration should add its own script and Rust tests in this repo.

The old `zo_*` scripts are Zorg-specific and parse `~/org/*.zo` data. Since the project memory says Bryan has fully
switched to Obsidian and no longer uses Zorg, they should be audited for references but not migrated into the Bob CLI
MVP unless a later agent finds a Bob workflow still depends on them.

## Goals

- Create a Rust Cargo package in this repo with a primary installed binary named `bob`.
- Make `bob` the user-facing interface for the migrated scripts, starting with commands like `bob pomodoro`.
- Move the Bob script implementations out of chezmoi and into this repo as the canonical source.
- Preserve MVP behavior by delegating to the existing Bash/Python logic where practical.
- Ensure a normal `cargo install` makes the commands usable without requiring a checkout of this repo or the old chezmoi
  files.
- Keep the phases independent enough that distinct agent instances can complete them one at a time.

## Key Design Decision

Do not rely on Cargo installing `scripts/` as loose data files. `cargo install` installs binaries, not arbitrary runtime
assets. The Rust CLI should embed the migrated script assets at compile time and materialize them at runtime into a
versioned cache directory such as:

```text
$XDG_CACHE_HOME/bob-cli/scripts/<package-version-or-content-hash>/
```

The runner should write executable files atomically, include any local shell helper files, prepend that cache directory
to `PATH`, and then `exec` or spawn the target script with inherited stdio. This keeps scripts available after
`cargo install` and lets scripts call each other by legacy names during the MVP.

The Bash scripts currently source `~/lib/bugyi.sh`. That dependency must not remain required for installed users. Import
only the small helpers needed by the Bob scripts into this repo, likely as `scripts/lib/bob_shell.sh`, and update the
moved Bash scripts to source that helper relative to their script directory.

## Phase 1 - Rust Crate Skeleton and Script Import

Owner: first implementation agent.

Create the initial Cargo package without changing chezmoi yet.

Expected work:

- Add `Cargo.toml` for package `bob-cli` with primary binary target `bob`.
- Add a minimal `src/main.rs` and shared library module structure that can grow into a script runner.
- Create a repo-local script layout, for example:
  - `scripts/bob_pomodoro`
  - `scripts/bob_pomodoro_runtimes`
  - `scripts/bob_notify`
  - `scripts/bob_sync`
  - `scripts/tmux_bob_pomodoro`
  - `scripts/lib/bob_shell.sh`
- Copy the Bob script logic from chezmoi into those files with the chezmoi `executable_` prefix removed.
- Remove the direct `~/lib/bugyi.sh` dependency by replacing it with the local helper file. Keep helper scope narrow:
  `SCRIPTNAME`, `usage`, `die`, and the `log::*` functions actually used by these scripts are enough.
- Preserve existing environment overrides such as `BOB_DIR`, `BOB_DAY_FILE`, `BOB_NOW`, `DATE`, `OB_COMMAND`, and
  `BOB_SYNC_LOCK_FILE`.
- Stage fixtures that a later phase can use for `bob_pomodoro` and `bob_pomodoro_runtimes` behavior. If a prior
  chezmoi-local shell test exists outside the inspected tree, import it; otherwise create new focused fixtures in this
  repo.

Acceptance checks:

- `cargo check` passes for the skeleton.
- `bash -n` passes for the imported Bash scripts.
- The Python script still runs `python3 scripts/bob_pomodoro_runtimes --help`.
- A temporary `HOME` without `~/lib/bugyi.sh` can run an equivalent no-op/syntax path for the Bash scripts without
  failing on the missing personal shell library.
- No chezmoi source files are modified in this phase.

## Phase 2 - `bob` CLI Delegation and Legacy Installed Shims

Owner: second implementation agent, after Phase 1 lands.

Implement the Rust runtime bridge and expose the MVP command surface.

Expected work:

- Add a command parser, preferably with `clap`, while preserving pass-through script arguments after each subcommand.
- Implement a script asset table using `include_bytes!`, `include_str!`, or a small generated manifest. The published
  crate must include `scripts/**`.
- Materialize embedded scripts into a versioned/cache directory with executable permissions and stable invalidation when
  script contents change.
- Run delegated scripts with inherited stdin/stdout/stderr and return the child exit status accurately.
- Prepend the extracted script directory to `PATH` so scripts like `bob_notify` can call `bob_pomodoro` without
  depending on chezmoi.
- Add primary subcommands:
  - `bob pomodoro` -> `bob_pomodoro`
  - `bob pomodoro-runtimes` -> `bob_pomodoro_runtimes`
  - `bob notify` -> `bob_notify`
  - `bob sync` -> `bob_sync`
  - `bob tmux-pomodoro` -> `tmux_bob_pomodoro`
- Add installed Rust shim binaries for compatibility with existing callers:
  - `bob_pomodoro`
  - `bob_pomodoro_runtimes`
  - `bob_notify`
  - `bob_sync`
  - `tmux_bob_pomodoro`
- Have each shim call the same Rust runner rather than duplicating logic.

Acceptance checks:

- `cargo run -- pomodoro --help` reaches the migrated script help/error path.
- `cargo run -- pomodoro-runtimes --help` reaches the Python argparse help.
- The legacy shim binaries work through `cargo run --bin bob_pomodoro -- ...` or direct target paths.
- Exit codes and stderr/stdout are preserved for at least one success and one failure fixture.
- `cargo install --path . --root "$(mktemp -d)"` installs `bob` and the legacy shim binaries, and the installed
  `bob pomodoro-runtimes --help` works without a repo checkout in the current directory.

## Phase 3 - Test Coverage and Package Hardening

Owner: third implementation agent, after Phase 2 lands.

Turn the migration into a maintainable package with focused tests.

Expected work:

- Add or port focused shell/Python fixtures so `bob_pomodoro_runtimes` runs against the repo-local script or the
  `bob pomodoro-runtimes` command without depending on the real `~/bob` vault.
- Add Rust integration tests for the script runner:
  - cache extraction creates expected files and modes,
  - `PATH` contains the extracted script directory,
  - pass-through arguments are not eaten by Clap,
  - child exit statuses propagate.
- Add fixtures for Bob daily notes covering completed/open Pomodoro ledger entries, runtime suffix idempotence, and
  missing day-file behavior.
- Add non-networked tests for `bob sync` using stubbed `ob` and `git` commands where practical. Do not push or touch the
  real `~/bob` vault in tests.
- Add basic formatting/lint commands to docs or a `justfile` if the repo adopts one.
- Verify packaging metadata so a future crates.io or Git install includes `scripts/**`, tests, README/license metadata
  if present, and excludes unrelated local artifacts.

Acceptance checks:

- `cargo test` passes.
- `cargo fmt --check` passes.
- `cargo clippy --all-targets --all-features` passes or documented local blockers are filed.
- Script syntax checks pass: `bash -n scripts/bob_* scripts/tmux_bob_pomodoro`.
- Python checks are run where available: at minimum `python3 -m py_compile scripts/bob_pomodoro_runtimes`; run `ruff` if
  configured.
- A local `cargo install --path . --root <tmp>` smoke test proves the installed package is self-contained.

## Phase 4 - Chezmoi Cutover and Local Integration

Owner: fourth implementation agent, after Phase 3 lands.

Make this repo canonical and remove Bob script logic from chezmoi.

Expected work:

- In the chezmoi repo, delete the migrated Bob script implementations or replace them temporarily with tiny wrappers
  that exec the installed Rust CLI. The end state should have no duplicated Bob script logic in chezmoi.
- Update tmux config to call `bob tmux-pomodoro` directly, or rely on the installed `tmux_bob_pomodoro` shim if that
  better preserves current config.
- Audit references to old executable names across chezmoi:
  - shell aliases/functions,
  - tmux config,
  - Neovim config,
  - cron/systemd/desktop launchers if any are present.
- Keep the Neovim Bob Lua modules in chezmoi for now unless a separate decision is made to package editor integrations
  in this repo. They are editor config, not CLI scripts.
- Update chezmoi tests so Bob CLI behavior is covered by this repo instead of the old script paths.
- Apply chezmoi only after the Rust CLI is installed locally, so the live machine does not lose commands during the
  transition.

Acceptance checks:

- `command -v bob` resolves to the Cargo-installed binary.
- `bob pomodoro`, `bob pomodoro-runtimes --help`, and `bob tmux-pomodoro` run from outside the repo.
- Existing old command names still work if the compatibility shim binaries are intentionally supported.
- `rg "executable_bob_|bob_pomodoro_runtimes|bob_notify|bob_sync" ~/.local/share/chezmoi` shows no remaining duplicated
  implementation logic.
- Tmux status uses the new command path after applying chezmoi.

## Phase 5 - Documentation and Release Workflow

Owner: fifth implementation agent, after Phase 4 lands.

Document how users install and use the new tool.

Expected work:

- Write README usage for:
  - `cargo install --path .` for local development,
  - `cargo install --git <repo-url>` once the remote is known,
  - `bob pomodoro`,
  - `bob pomodoro-runtimes`,
  - `bob notify`,
  - `bob sync`,
  - `bob tmux-pomodoro`.
- Document runtime dependencies that remain after the MVP:
  - `bash`,
  - `python3`,
  - `perl` for `bob_pomodoro`,
  - `ob`/obsidian-headless for sync/runtime annotation,
  - `git` and `ssh` for `bob sync`,
  - `notify-send` when desktop notifications are desired.
- Document important environment variables: `BOB_DIR`, `BOB_DAY_FILE`, `BOB_NOW`, `DATE`, `OB_COMMAND`,
  `BOB_SYNC_LOCK_FILE`, and `BOB_SYNC_COMMIT_MESSAGE`.
- Add a release checklist that includes `cargo test`, local `cargo install` smoke tests, and a tmux status smoke test.
- Add migration notes explaining that the legacy command names are compatibility shims and the preferred interface is
  now `bob <subcommand>`.

Acceptance checks:

- A fresh agent can install from this repo and run the documented smoke tests using only README instructions.
- README clearly states that the MVP delegates to embedded Bash/Python scripts.
- The repository has no hidden dependency on the old chezmoi script files.

## Phase 6 - Post-MVP Native Rust Migration

Owner: later agents, only after the delegated MVP is stable.

This is intentionally outside the initial migration. Reimplement script logic in Rust one command at a time, keeping
behavior tests green and retaining script delegation as a rollback path until each command is complete.

Suggested order:

1. `bob pomodoro-runtimes`, because it is already Python with clear pure parsing behavior plus an `ob sync` boundary.
2. `bob pomodoro`, because it is core status-bar logic and currently depends on Bash plus embedded Perl.
3. `bob notify`, after `bob pomodoro` is native.
4. `bob sync`, last, because it touches Git, SSH, locks, and external sync.

Do not migrate the legacy `zo_*` Zorg scripts unless Bryan explicitly asks for a Zorg compatibility package.

## Risks and Mitigations

- Cargo data-file trap: mitigate by embedding scripts and extracting them at runtime instead of assuming `scripts/`
  exists beside the installed binary.
- Hidden personal dependency on `~/lib/bugyi.sh`: mitigate by importing only the helper functions the Bob scripts need.
- PATH precedence with old `~/bin` scripts: mitigate during cutover by deleting or replacing chezmoi implementations and
  confirming `command -v` results.
- Live vault mutation in tests: mitigate with temp `BOB_DIR`, `BOB_DAY_FILE`, `BOB_NOW`, and stubbed `ob`/`git`.
- Long-running notifier tests: mitigate with stub `bob_pomodoro`, tiny sleep values, and `timeout`.
- Existing external callers: mitigate with Cargo-installed legacy shim binaries while documenting `bob <subcommand>` as
  the preferred interface.
