---
create_time: 2026-06-02 08:55:19
status: wip
prompt: sdd/prompts/202606/bob_sync_crontab.md
---
# Plan: Fix `bob_sync` crontab entry to use `bob sync`

## Problem / Context

The user's crontab has a daily job that syncs the Bob Obsidian vault to GitHub. It currently invokes a shell wrapper
script `$HOME/bin/bob_sync` instead of the `bob sync` subcommand directly. The user wants this entry fixed to call the
appropriate `bob sync` command instead.

### Current crontab entry (line ~36 of `crontab -l`)

```cron
# Sync Bob Obsidian vault to GitHub daily.
30 3 * * * bash -c ". $HOME/.profile; $HOME/bin/bob_sync" >> /var/tmp/bob_sync.log 2>&1
```

### What `$HOME/bin/bob_sync` does today

```sh
#!/bin/sh
if command -v bob >/dev/null 2>&1; then
  exec bob sync "$@"
fi
exec "$HOME/.cargo/bin/bob" sync "$@"
```

It is a thin wrapper that runs `bob sync`, preferring `bob` on `PATH` and falling back to the cargo install path
`$HOME/.cargo/bin/bob`.

### Relevant findings

- `bob` is installed at `/home/bryan/.cargo/bin/bob` and exposes a real `sync` subcommand (`bob sync` — "Sync the
  Obsidian vault"). Verified working: a manual run committed and pushed vault changes successfully.
- The crontab already sources `$HOME/.profile` before running the command, the same pattern used by the sibling `tman`
  entry which calls a bare `tman` binary. So `bob` is expected to be on `PATH` inside the cron shell.
- The current `/var/tmp/bob_sync.log` tail shows a Node.js stack trace — evidence the cron wrapper path has been
  failing/stale, which is part of why this entry needs fixing.

## Goal

Replace the wrapper invocation `$HOME/bin/bob_sync` in the crontab entry with a direct `bob sync` invocation, keeping
all other aspects of the entry intact (schedule, `.profile` sourcing, log redirection).

## Proposed Change

Edit only the command portion of the single crontab line. Schedule (`30 3 * * *`), the `. $HOME/.profile;` prefix, and
the `>> /var/tmp/bob_sync.log 2>&1` redirection stay the same.

**From:**

```cron
30 3 * * * bash -c ". $HOME/.profile; $HOME/bin/bob_sync" >> /var/tmp/bob_sync.log 2>&1
```

**To:**

```cron
30 3 * * * bash -c ". $HOME/.profile; bob sync" >> /var/tmp/bob_sync.log 2>&1
```

Using bare `bob sync` (rather than the absolute `$HOME/.cargo/bin/bob sync`) mirrors the existing `tman` entry
convention and relies on `.profile` putting `~/.cargo/bin` on `PATH`. The comment line above the entry stays unchanged.

### Decision point for the user

If a hardcoded path is preferred for robustness against `PATH` differences in cron, the alternative is:

```cron
30 3 * * * bash -c ". $HOME/.profile; $HOME/.cargo/bin/bob sync" >> /var/tmp/bob_sync.log 2>&1
```

Recommended default: bare `bob sync` for consistency with the `tman` entry.

## Implementation Steps

1. Capture current crontab: `crontab -l > /tmp/crontab.bak`.
2. Edit the `bob_sync` line in a copy, replacing `$HOME/bin/bob_sync` with `bob sync`.
3. Install the edited crontab: `crontab /tmp/crontab.new`.
4. Verify with `crontab -l` that the line now reads `... bob sync ...` and that no other entries changed.

## Verification

- `crontab -l` shows the updated entry and an otherwise-identical file (diff against the backup shows exactly one
  changed line).
- Dry-run the exact cron command in a shell to confirm it resolves and runs: `bash -c ". $HOME/.profile; bob sync"`
  exits cleanly and produces the normal sync log output (stage / commit / push lines).

## Scope / Out of Scope

- **In scope:** the single `bob_sync` crontab line.
- **Out of scope:** the `$HOME/bin/bob_sync` wrapper script itself. This plan does not delete it; it can be left in
  place (harmless) or cleaned up separately if the user wants. No repo source files are modified — this is a
  user-environment (crontab) change.

## Risks

- Low. The only change is which command the cron line runs. If `bob` is not on `PATH` under cron's `.profile`, fall back
  to the absolute-path alternative above. Backup of the prior crontab is taken before any change so it is fully
  reversible (`crontab /tmp/crontab.bak`).
