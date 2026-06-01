---
create_time: 2026-06-01 09:58:18
status: wip
prompt: .sase/sdd/prompts/202606/bob_cli_migration_2.md
---
# Bob CLI Migration Plan

## Context

Create a Rust `bob` CLI in this repo and migrate the executable Bob/Obsidian scripts that currently live in the chezmoi
repo so `cargo install` users get a working `bob` command. For the MVP, Rust may dispatch to the existing Bash/Python
scripts, but those scripts must become repo-owned and must not depend on the chezmoi source tree.

Current chezmoi inventory found during planning:

- `/home/bryan/.local/share/chezmoi/home/bin/executable_bob_pomodoro`
- `/home/bryan/.local/share/chezmoi/home/bin/executable_bob_pomodoro_runtimes`
- `/home/bryan/.local/share/chezmoi/home/bin/executable_bob_notify`
- `/home/bryan/.local/share/chezmoi/home/bin/executable_bob_sync`
- `/home/bryan/.local/share/chezmoi/home/bin/executable_tmux_bob_pomodoro`
- `/home/bryan/.local/share/chezmoi/tests/bash/bob_pomodoro_runtimes_test.sh`

Relevant active integrations in chezmoi:

- tmux status uses `tmux_bob_pomodoro`.
- Hammerspoon calls `$HOME/bin/bob_pomodoro`.
- Neovim Bob/Obsidian Lua config and tests are related to the vault, but are editor configuration rather than CLI
  scripts. Leave them in chezmoi for the MVP unless a later phase explicitly scopes an editor-plugin extraction.

Do not migrate the old `zo_*` scripts as part of this plan. The Obsidian memory says Bryan has fully switched from zorg
to Bob/Obsidian, so those are historical references only.

## Design Direction

Use a Rust crate named `bob-cli` with an installed binary named `bob`. Add a `[[bin]]` entry for `bob`, use `clap` for
the command surface, and delegate each MVP command to repo-owned runtime assets.

Cargo does not install arbitrary script files beside the binary in a reliable source-relative location, so do not make
the installed binary depend on `scripts/` existing on disk after `cargo install`. Instead, embed the migrated scripts
with `include_bytes!` or an equivalent build-time embedding mechanism, extract them into a version/hash-specific runtime
directory such as `$XDG_CACHE_HOME/bob-cli/scripts/<package-version-or-content-hash>/`, mark them executable, prepend
that directory to `PATH`, and execute the selected script with argument passthrough.

Several Bash scripts currently source `~/lib/bugyi.sh`. That private dependency must be removed or vendored before the
MVP is considered installable. The safest MVP path is to vendor the required helper library as a repo-owned runtime
asset and patch migrated scripts to source it from their extracted script directory, not from `~/lib`.

Target MVP command map:

- `bob pomodoro` delegates to `bob_pomodoro`.
- `bob pomodoro runtimes [--check] [NOTE ...]` delegates to `bob_pomodoro_runtimes`.
- `bob notify PRE_CHECK_SLEEP POST_NOTIFY_SLEEP` delegates to `bob_notify`.
- `bob sync` delegates to `bob_sync`.
- `bob tmux pomodoro` delegates to `tmux_bob_pomodoro`.

Preserve existing environment overrides where applicable: `BOB_DIR`, `BOB_NOW`, `BOB_DAY_FILE`, `DATE`, `OB_COMMAND`,
`BOB_SYNC_LOCK_FILE`, `BOB_SYNC_COMMIT_MESSAGE`, `GIT_SSH_COMMAND`, and logging-related variables used by `bugyi.sh`.

## Phase 1: Rust Crate Skeleton And Runtime Asset Runner

Owner: first implementation agent.

Scope:

- Initialize the Rust crate in this repo.
- Configure package metadata so `cargo install --path .` installs a binary named `bob`.
- Add a small `clap` command tree for the target MVP commands. Commands may initially fail with a clear "not wired yet"
  error if the asset migration has not landed.
- Implement the runtime asset extraction/exec layer with a tiny fixture script embedded in tests.
- Preserve exit status, stdout, stderr, current working directory, and argument ordering when delegating.
- Add focused Rust tests for command parsing and extraction/exec behavior.

Exit criteria:

- `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, and `cargo test` pass.
- `cargo install --path . --root <tempdir>` installs `<tempdir>/bin/bob`.
- The installed binary can execute a fixture-backed delegated command in tests without depending on repo-relative files.

## Phase 2: Migrate Scripts And Remove Private Shell Dependencies

Owner: second implementation agent.

Scope:

- Copy the five active Bob executable scripts from chezmoi into this repo using clean installed names without the
  chezmoi `executable_` prefix.
- Vendor only the shell helper functionality needed by `bob_pomodoro`, `bob_notify`, and `tmux_bob_pomodoro`, or vendor
  the current `bugyi.sh` whole if that is faster and lower risk for the MVP.
- Patch migrated Bash scripts to source the repo-owned helper from the extracted runtime asset directory.
- Keep inter-script calls working by ensuring the runtime extraction directory is prepended to `PATH`; `bob_notify` and
  `tmux_bob_pomodoro` should still be able to invoke `bob_pomodoro` internally.
- Port the existing `bob_pomodoro_runtimes_test.sh` into this repo and update its script path assumptions.
- Add script verification: `shellcheck` for Bash, `python3 -m py_compile` for Python, and the ported regression test.

Exit criteria:

- No migrated script references `/home/bryan/.local/share/chezmoi`, `~/lib/bugyi.sh`, or `home/bin/executable_*`.
- The ported runtime annotation test passes in this repo with a fake `ob`.
- Script tests do not touch the real `~/bob` vault.

## Phase 3: Wire The Real CLI Commands

Owner: third implementation agent.

Scope:

- Connect each `bob` subcommand to the corresponding embedded migrated script.
- Add command-level help text that describes the new `bob` interface while preserving script argument passthrough.
- Add integration tests for the public commands:
  - `bob pomodoro` against a temporary fake Bob daily note with `BOB_DIR`/`BOB_NOW`.
  - `bob pomodoro runtimes --check` against a fixture note and fake `ob`.
  - `bob tmux pomodoro` with a fake/current Pomodoro state.
  - `bob notify --help` or a non-looping argument validation path.
  - `bob sync` using a temp Git repo and fake `ob`/`git` where needed, avoiding the real vault and network.
- Decide whether to expose hidden compatibility aliases or additional installed binaries for legacy names. Prefer
  updating integrations to `bob ...`, but if compatibility binaries are added, they should call the same Rust dispatcher
  and not duplicate script logic.

Exit criteria:

- `cargo run -- <command>` works for all MVP commands.
- `cargo install --path . --root <tempdir>` followed by installed-binary smoke tests works without the chezmoi repo.
- Subcommand failures preserve useful stderr and the delegated script exit code.

## Phase 4: Documentation, Packaging, And Cross-Platform Notes

Owner: fourth implementation agent.

Scope:

- Fill in `README.md` with installation, command examples, environment overrides, and external runtime dependencies.
- Document that `ob`/obsidian-headless remains an external dependency for sync-capable commands.
- Document Bash/Python/Perl/Git expectations inherited from the MVP scripts.
- Document GNU `date` expectations and the macOS `gdate` workaround if the MVP scripts still require `date --date`.
- Add a release/install smoke script or justfile target if the repo establishes one.
- Ensure `.gitignore` ignores Cargo build output and temporary install roots without hiding real source files.

Exit criteria:

- A new user can read the README, run `cargo install --path .`, and understand which commands require `ob`, Git, or GNU
  date.
- `cargo package --allow-dirty` succeeds or any packaging blocker is explicitly documented.

## Phase 5: Chezmoi Cutover And Integration Cleanup

Owner: fifth implementation agent, ideally in a chezmoi workspace or with explicit permission to edit that repo.

Scope:

- Remove the old Bob executable script ownership from chezmoi or replace those files with temporary shims that point to
  the installed `bob` CLI.
- Update tmux from `#(tmux_bob_pomodoro)` to `#(bob tmux pomodoro)`.
- Update Hammerspoon from `$HOME/bin/bob_pomodoro` to the installed `bob pomodoro` command, preserving PATH setup for
  Cargo/Homebrew locations.
- Search chezmoi for remaining active references to `bob_pomodoro`, `bob_pomodoro_runtimes`, `bob_notify`, `bob_sync`,
  and `tmux_bob_pomodoro`; either update them or leave intentional compatibility notes.
- Keep Neovim Bob/Obsidian configuration in chezmoi unless a separate plan extracts editor integration.

Exit criteria:

- chezmoi no longer contains the authoritative copies of migrated Bob scripts.
- Local tmux/Hammerspoon integrations call `bob` instead of the old script paths.
- The old scripts are either absent or deliberate thin compatibility shims.

## Global Acceptance Criteria

- The repo owns the active Bob CLI scripts and tests.
- `cargo install` users get a functional `bob` binary with all MVP commands.
- Installed command behavior does not rely on the chezmoi repo or `~/lib/bugyi.sh`.
- Tests never mutate Bryan's real `~/bob` vault.
- Active local integrations can be switched from old script names to `bob ...` commands.
