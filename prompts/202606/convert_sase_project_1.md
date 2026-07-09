---
plan: sdd/tales/202606/convert_sase_project_1.md
---
 Can you help me convert the `~/bob/sase.md` file into a proper project file (see other project files like `~/bob/sase_install.md` for an idea of what a project file should look like)? Also, all `[p::1]` tasks in that file should be converted to normal bullets and moved to a "Future Work" section at the bottom of the file.

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.


%xprompts_enabled:false
### Questions and Answers

#### Q1: sase_install link

> The converted sase.md `^prj` line lists [[sase_install]] as a sub-project (per the plan), but `bob projects sync --dry-run` wants to remove it. Cause: sase_install.md has the non-canonical `parent: "[[sase.md|sase]]"` (the only `.md`-style parent link in the vault), and the resolver in projects.rs never strips `.md` from wikilink targets, so it resolves to `sase.md` instead of `sase`. How should I resolve this?

- [x] **Normalize sase_install.md parent** — Change its frontmatter to parent: "[[sase]]". Surgical 1-line edit, matches every other parent link in the vault, makes dry-run sync clean. Touches one extra note beyond the plan.
- [ ] **Fix the resolver in bob-cli** — Make wikilink_ref_from_inner strip a trailing .md from link targets so [[sase.md|sase]] resolves to sase. Fixes the root cause for all such links; a code change with tests, broader than the plan.
- [ ] **Drop sase_install from the line** — Match current sync behavior: ^prj shows only [[sase_blog]] • [[sase_piw_multi_prompt]]. Contradicts the plan and loses a real parent-child link. Not recommended.
- [ ] **Leave as-is** — Keep [[sase_install]] on the line and do not run mutating sync. Accepts that a future sync run would silently drop it.

%xprompts_enabled:true