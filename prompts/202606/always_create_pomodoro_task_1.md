---
plan: sdd/tales/202606/always_create_pomodoro_task_1.md
---
 The `<shift+enter>` Obsidian keymap's functionality for Pomodoro tasks currently only creates a new Pomodoro task below the current one (i.e. the one we are marking as done) when no existing Pomodoro tasks exist below the current one. Can you help me change that so we always create this new Pomodoro task (any sub-bullets we copy over should always be copied under this new Pomodoro task)? Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.


%xprompts_enabled:false
### Questions and Answers

#### Q1: Commit scope

> task-status-cycler/main.js contains both my Pomodoro change and unrelated in-progress task-routing work that was already dirty. How should I commit?

- [ ] **Isolate my hunk** — Recommended. Safely commit ONLY the Pomodoro buildPomodoroCompletionPlan change (back up the full file, write a HEAD+Pomodoro-only version, sase commit, then restore the file so the task-routing work stays uncommitted and untouched).
- [x] **Commit whole file** — Run sase_git_commit -f on the whole file. Simplest, but this commit would ALSO include the unrelated in-progress task-routing changes.
- [ ] **Do not commit** — Leave my Pomodoro change in the working tree uncommitted for you (or a finalizer) to commit later. Nothing is pushed.

---

> **Global Note:** Answered via Telegram

%xprompts_enabled:true