---
plan: sdd/epics/202606/bob_cli_migration_3.md
---
 Can you help me migrate all scripts related to my new ~/bob/ Obsidian value that currently live in my chezmoi repo to this repo? Let's create a new Rust `bob` CLI tool that is used as ther interface for all of these scripts (ex: `bob pomodoro`). For this MVP, it is fine if these commands just delegate to the existing bash / Python scripts. For example, the `bob pomodoro` command can be a thin wrapper around the `bob_pomodoro` script, but that script MUST be moved to this repo and be available to users who install this Rust tool (e.g. using the `cargo install` command).

This is a large piece of work that should be split into phases. I'll let you decide how many phases to create, but
keep in mind that each phase will be completed by a distinct agent instance (i.e. a distinct `claude` / `gemini` /
`codex` / `qwen` / `opencode` command). Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.

