---
create_time: 2026-06-02 09:27:22
status: wip
prompt: sdd/prompts/202606/bob_collect_done_crontab.md
---
# Plan: Add a nightly `bob collect-done` crontab entry

## Problem / Context

The user wants `bob collect-done` to run automatically every night at ~3:30AM, by adding an entry to their user crontab.
We already run `bob sync` nightly from cron, so this new entry should follow that established pattern.

### What `bob collect-done` does

```
usage: bob collect-done [--threshold N]

Collect done and canceled Bob task blocks into archive notes, and link sources.

options:
  --threshold N    minimum completed/canceled task count per source note (default: 10)
```

It rewrites/links notes **inside the local Obsidian vault**. Importantly, it operates on local files only — it does
**not** commit or push to GitHub. That job belongs to `bob sync`.

### The existing `bob sync` crontab entry (live, from `crontab -l`)

```cron
# Sync Bob Obsidian vault to GitHub daily.
30 3 * * * bash -c ". $HOME/.profile; . $HOME/.config/nvm/nvm.sh; nvm use --silent default; bob sync" >> /var/tmp/bob_sync.log 2>&1
```

Notes on this entry (the canonical pattern to mirror):

- Runs at `30 3 * * *` — **exactly 3:30AM**, the same time the user is asking for `collect-done`.
- Wraps the command in `bash -c "..."` and sources `$HOME/.profile`, then sources nvm and selects the default node
  version before invoking `bob`. (The nvm prelude is part of the working entry, so we mirror it for safety/consistency
  even though `collect-done` is a local-only operation.)
- Redirects all output (stdout+stderr) to a dedicated log under `/var/tmp/` (`bob_sync.log`).
- `bob` resolves to `/home/bryan/.cargo/bin/bob` (an ELF binary), put on `PATH` via `.profile`.
- This entry ran successfully as recently as today (`/var/tmp/bob_sync.log` mtime `2 Jun 03:30`).

## Goal

Add **one new crontab entry** that runs `bob collect-done` nightly at ~3:30AM, mirroring the `bob sync` entry's wrapper,
environment prelude, and logging conventions. Make no other changes to the crontab and no changes to repo source files
(this is a user-environment change only).

## Key Decision: ordering relative to `bob sync` (both want 3:30AM)

`bob sync` already occupies `30 3 * * *`. `collect-done` modifies vault files locally but does not push them, so for its
archive changes to actually reach GitHub the **sync must run after collect-done**. Scheduling both at the exact same
minute creates a race (sync could push before/while collect-done is still rewriting notes).

**Recommended:** run `collect-done` a few minutes _before_ sync, so each night's archive edits are included in that same
night's push. Concretely:

```cron
# Collect done/canceled Bob tasks into archive notes nightly (before the sync push).
25 3 * * * bash -c ". $HOME/.profile; . $HOME/.config/nvm/nvm.sh; nvm use --silent default; bob collect-done" >> /var/tmp/bob_collect_done.log 2>&1
```

i.e. `collect-done` at **3:25AM**, leaving the existing `bob sync` at 3:30AM untouched. This satisfies "~3:30AM" while
guaranteeing correct ordering with no edit to the proven sync entry.

### Alternatives for the user to choose from

1. **Recommended — 3:25 collect-done, sync stays 3:30** (above). Smallest, safest change; correct ordering.
2. **Same minute (3:30) for both.** Literal "3:30AM", but risks a collect-done/sync race; that night's archive edits may
   not be pushed until the _next_ night's sync. Not recommended.
3. **Chain them in one entry** (`... bob collect-done && bob sync`) replacing the sync line at 3:30. Guarantees ordering
   and "3:30AM" exactly, but couples the two jobs (a collect-done failure would block the sync) and rewrites the
   currently-working sync entry. More invasive.

This plan implements option 1 unless the user prefers another.

## Proposed Change

Append the following block to the crontab, immediately after the existing `bob sync` entry (keeping related Bob jobs
grouped):

```cron
# Collect done/canceled Bob tasks into archive notes nightly (before the sync push).
25 3 * * * bash -c ". $HOME/.profile; . $HOME/.config/nvm/nvm.sh; nvm use --silent default; bob collect-done" >> /var/tmp/bob_collect_done.log 2>&1
```

- `--threshold` is omitted, so the default (10) applies. We can add `--threshold N` if the user wants a different
  cutoff.
- New dedicated log: `/var/tmp/bob_collect_done.log` (mirrors `bob_sync.log`).

## Implementation Steps

1. Back up the current crontab: `crontab -l > /tmp/crontab.bak`.
2. Create the new crontab in a temp file: `crontab -l > /tmp/crontab.new`, then append the new comment + entry after the
   `bob sync` line.
3. Install it: `crontab /tmp/crontab.new`.
4. Verify with `crontab -l`.

## Verification

- `diff /tmp/crontab.bak <(crontab -l)` shows **exactly** the two added lines (comment + entry) and nothing else changed
  — the `bob sync` entry and all other jobs are byte-for-byte identical.
- Dry-run the exact cron command in a shell to confirm it resolves and runs cleanly:
  `bash -c ". $HOME/.profile; . $HOME/.config/nvm/nvm.sh; nvm use --silent default; bob collect-done"` exits 0 and
  writes expected output. (Note: this is a real, side-effecting run against the vault — it will archive eligible
  done/canceled tasks. Run it knowing that, or confirm with the user first.)
- After the first scheduled run, confirm `/var/tmp/bob_collect_done.log` is created and contains a clean run.

## Scope / Out of Scope

- **In scope:** adding the single new `bob collect-done` crontab entry (+ its comment) and its log file.
- **Out of scope:** the existing `bob sync` entry (left untouched under option 1), the `$HOME/bin/bob_sync` wrapper
  script, the `tman` entry, and any repo source files. No code changes.

## Risks

- **Low.** Purely additive to the user environment; the proven `bob sync` entry is not modified. A full crontab backup
  is taken first, so the change is trivially reversible (`crontab /tmp/crontab.bak`).
- If `bob` is somehow not on `PATH` under cron despite `.profile`, fall back to the absolute path
  `$HOME/.cargo/bin/bob collect-done` — same fallback available for the sync entry.
- `collect-done` is side-effecting (it rewrites vault notes). The 3:25 schedule ensures its changes are captured by the
  3:30 sync; if the user reorders the times, preserve "collect-done before sync".
