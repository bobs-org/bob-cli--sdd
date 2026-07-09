---
create_time: 2026-06-03 05:04:11
status: done
---
# Plan: Add CLI Rules Long-Term Memory

## Context

The project currently loads `memory/short/sase.md` from `AGENTS.md`; there is no project-local `memory/long/` directory
yet. The requested change adds a durable long-term memory file for CLI authoring rules, then refreshes SASE memory
instruction shims so the file is referenced from `AGENTS.md`.

## Goals

- Create `memory/long/cli_rules.md` with frontmatter whose `description` says the file should be read anytime new CLI
  subcommands or options are added.
- Include concise agent-facing guidance that emphasizes excellent `-h|--help` output.
- State that listed subcommands and options should always be sorted alphabetically.
- State that beautiful, colored output is preferred over black-and-white output.
- Run `sase memory init` after the file exists so generated SASE memory references are refreshed.
- Verify the resulting memory context and git diff.

## Implementation Approach

1. Create the missing `memory/long/` directory and add `cli_rules.md`.
2. Use simple YAML frontmatter with a `description` field matching the requested trigger semantics.
3. Keep the body short, durable, and phrased as rules for future agents rather than as implementation notes for this
   one-off change.
4. Run `sase memory init` from the workspace root to link the new memory file into the provider instruction files.
5. Inspect `AGENTS.md`, `sase memory list`, and `git diff --stat`/targeted diff output to confirm the new file is
   visible and that the command made the expected instruction-shim updates.

## Risks and Mitigations

- `sase memory init` may update multiple provider shim files, not just `AGENTS.md`; verify the diff and do not adjust
  unrelated generated output by hand.
- If `sase memory init` attempts an automatic commit, treat that as part of the requested command behavior, then report
  exactly what changed.
- Avoid reading or editing unrelated long-term memory files; this task only creates the new `cli_rules.md` file.
