---
plan: sdd/epics/202606/bob_plugins_repo.md
---
 #fork:research.y.final Can you help me migrate these 6 Obsidian plugins to the new bbugyi200/bob-plugins repo?

- Use the research markdown file created by the previous agent as inspiration.
- I have already created the GitHub repo and linked it as a remote to the ~/projects/github/bbugyi200/bob-plugins/ repo.
- The command to manage (e.g. sync to my vault) the plugins should be named `bob plugins` (not `bob obsidian-plugins`).
- Make sure the `bob plugins` command has a `list` subcommand (should be used as the default) that lists useful information about bob plugins. Use your best judgement on what the output should include in order to provide the most value to the user. I want you to lead the design on this one. Just make sure it looks beautiful!
- Give the bob-plugins repo a great README.
- Configure this repo (in the sase.yml file) to adopt the bob-plugins repo as a sase sibling repo (see how we do this for the sase project's siblings in the ~/projects/github/sase-org/sase/ directory for context). Run the `sase init` command when you are done to initialize your changes.

This is a large piece of work that should be split into phases. I'll let you decide how many phases to create, but
keep in mind that each phase will be completed by a distinct agent instance (i.e. a distinct `claude` / `agy` /
`codex` / `qwen` / `opencode` command). Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.

 