---
create_time: 2026-06-03 12:56:06
status: wip
prompt: sdd/prompts/202606/ob_sync_continuous_polling_fix.md
---
# Plan: Make Bob Obsidian Sync Resilient to Missed Watch Events

## Problem

`ob-sync-bob.service` currently runs:

```bash
ob sync --path /home/bryan/bob --continuous
```

The service stays active and logs `Fully synced`, but Bryan often has to run:

```bash
systemctl --user restart ob-sync-bob.service
```

after SASE agents change files under `~/bob`. Restarting should not be necessary.

## Evidence Gathered

- `~/bob/` is the Obsidian vault, and this machine uses `ob` / `obsidian-headless` for Obsidian Sync.
- The installed service is `/home/bryan/.config/systemd/user/ob-sync-bob.service`.
- The installed `ob` is `obsidian-headless` version `0.0.8`.
- Recent service logs show the service repeatedly reporting `Fully synced`, but each manual restart performs a fresh
  startup scan and re-detects files as `New file`.
- The installed `obsidian-headless` source shows that `--continuous`:
  - does an initial `adapter.watch(...)` plus startup `listAll()` scan;
  - schedules `requestSync()` every 30 seconds;
  - does not rescan normal vault files every 30 seconds;
  - relies on Node `fs.watch` events to add or update normal Markdown files in `localFiles`;
  - only does extra periodic-style scanning for selected `.obsidian` config files.
- Kernel watch limits are not exhausted:
  - vault directory count is small relative to the watch limit;
  - no `ENOSPC`, `EMFILE`, or watcher setup errors appear in the service logs.

## Root Cause

The long-running `ob sync --continuous` process depends on Node `fs.watch` to notice normal vault file changes after
startup. On Linux, `fs.watch` is not a durable recursive polling scanner; events can be missed or coalesced. When an
event is missed, the in-memory `localFiles` state is not updated, so the 30-second sync loop has nothing to upload and
can still report `Fully synced`.

Manual restart fixes the symptom because startup runs a full vault scan before syncing.

This is not primarily an Obsidian Sync server failure, a systemd restart policy failure, or an inotify limit failure.

## Recommended Fix

Replace the fragile continuous watcher service with a polling one-shot sync loop under the same systemd unit name:

```bash
while true; do
  ob sync --path /home/bryan/bob
  sleep 30
done
```

Rationale:

- one-shot `ob sync` performs the full local scan that currently only happens after a manual restart;
- the existing unit name stays the same, so Bryan's existing commands still work;
- no fork or patch of the minified global `obsidian-headless` package is required;
- the loop is resilient to transient network or sync failures;
- it avoids relying on best-effort `fs.watch` delivery for agent-written notes.

## Implementation Steps

1. Preserve the current service file for comparison before editing.
2. Add a small executable wrapper at `/home/bryan/.local/bin/ob-sync-bob-poll` that:
   - runs `/home/bryan/.config/nvm/versions/node/v22.14.0/bin/ob sync --path /home/bryan/bob`;
   - repeats every `OB_SYNC_INTERVAL_SECONDS`, defaulting to 30 seconds;
   - logs non-zero `ob sync` exits but keeps running;
   - exits cleanly on `SIGINT` / `SIGTERM`.
3. Update `/home/bryan/.config/systemd/user/ob-sync-bob.service` to run the wrapper instead of `ob sync --continuous`,
   while keeping:
   - `WorkingDirectory=/home/bryan/bob`;
   - `HOME=/home/bryan`;
   - the current Node/NVM `PATH`;
   - the same service name and enablement target.
4. Run:

```bash
systemctl --user daemon-reload
systemctl --user restart ob-sync-bob.service
systemctl --user status ob-sync-bob.service --no-pager
```

5. Verify through logs that the service is now executing one-shot sync cycles instead of a single long-running
   continuous process.
6. If vault-touch verification is needed, first inspect `git -C /home/bryan/bob status --short`; then create and delete
   a temporary Markdown probe with valid `parent` frontmatter and confirm the log shows upload and deletion. Leave no
   net vault changes.

## Rejected Alternatives

- Increase inotify limits: not indicated by the current limits or logs.
- Add `Restart=always` to the current continuous process: the process is not failing, so restart policy does not address
  stale watcher state.
- Use a systemd `.path` unit: user path units are not a clean recursive full-vault watcher and would still just automate
  restarts.
- Patch the installed minified `obsidian-headless` bundle: brittle and likely to be overwritten by package updates.
- Run `bob sync` repeatedly: it also commits and pushes Git changes, which is broader than the Obsidian Sync service's
  job.

## Validation Criteria

- `systemctl --user status ob-sync-bob.service --no-pager` shows the service active with the polling wrapper as
  `ExecStart`.
- `journalctl --user -u ob-sync-bob.service` shows repeated one-shot `Starting sync:` cycles without manual restart.
- A controlled vault file change is picked up by a later cycle without restarting the service.
- No unrelated files in `/home/bryan/bob` or the bob-cli workspace are modified.
