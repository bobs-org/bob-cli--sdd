---
plan: sdd/tales/202606/bob_cronjob.md
---
 Can you help me create a new `bob cronjob` command?

- This command will act as the one and only command that we run from this user's crontab (you should remove the other
  `bob` references in my crontab for a single entry that runs `bob cronjob` at 3:30AM).
- This script will wrap the existing `bob sync` and `bob collect-done` commands.
- We should remove the `ob sync` logic from the wrapped commands (see above bullet) in favor of handling when running
  the `bob cronjob` command before delegating to the wrapper commands (note: we should probably use the same Rust logic
  as these commands instead of executing them directly).
- The wrapper scripts should, however, still be in charge of making git commits (and pushing to GitHub).
- I plan on adding more "wrapped commands" in the future, so make sure it is very clear (via great user output), which
  wrapper command/logic is running at any given moment. I want you to lead the design on this one. Just make sure it looks beautiful!

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
 

%xprompts_enabled:false
### Questions and Answers

#### Q1: Standalone sync

> After extracting `ob sync` into the shared `bob cronjob` logic, what should standalone `bob sync` and `bob collect-done` do about running `ob sync` themselves?

- [x] **Remove entirely (recommended)** — ob sync runs ONLY inside bob cronjob. Standalone `bob sync` becomes commit+push of the vault; standalone `bob collect-done` just archives+commits. Cleanest, matches your literal request, single source of truth.
- [ ] **Keep standalone, skip under cronjob** — Each command still runs ob sync when invoked directly, but bob cronjob passes an internal --no-sync flag so it only happens once. Preserves today's standalone behavior at the cost of a flag + conditional in each command.

#### Q2: Failure mode

> If one wrapped step fails during `bob cronjob` (e.g. collect-done errors), how should the run proceed?

- [x] **Abort ob sync failure, else continue (recommended)** — A failed shared `ob sync` aborts the whole run (nothing to commit safely). After that, each wrapped command runs even if a prior one failed; cronjob exits non-zero if any failed, with a clear summary of what passed/failed.
- [ ] **Fail fast on any error** — Stop at the first failing step and exit non-zero immediately. Simpler, but a collect-done failure would skip the vault sync/push entirely that night.

#### Q3: Run order

> Inside `bob cronjob`, which order should the wrapped commands run?

- [x] **collect-done then sync (recommended)** — Mirrors your current crontab (collect-done 3:25, sync 3:30): archive first so the sync push includes that night's archive edits.
- [ ] **sync then collect-done** — Push vault first, then archive (archive edits land in the next run).

%xprompts_enabled:true