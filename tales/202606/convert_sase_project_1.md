---
create_time: 2026-06-14 08:42:25
status: done
prompt: sdd/prompts/202606/convert_sase_project_1.md
---
# Plan: Convert `~/bob/sase.md` Into a Bob Project File

## Context

The requested target is `~/bob/sase.md`, an Obsidian note in the Bob vault. Per `~/bob/_templates/new_project.md`,
`~/bob/sase_install.md`, and nearby SASE project notes, a proper Bob project note should have project frontmatter, a
single root project task ending in `^prj`, normal active tasks under `## Tasks`, and backlog/reference material under
project notes or future-work sections.

The live vault already contains uncommitted edits to `~/bob/sase.md` that appear to be the intended project conversion:

- frontmatter now uses `parent: "[[dev]]"`, `type: "[[project]]"`, `status: wip`, `created`, `task_count: 7`, and
  `open_task_count: 7`;
- the body starts with a `^prj` completion task and a nested sub-project line;
- the original `[p::1]` tasks have been moved out of `## Tasks`;
- those former `[p::1]` tasks now appear as normal bullets in `### Future Work`;
- `SASE Blog Post Drafts` and `Related: [[ai]]` now live under `## Project Notes`.

Treat those existing `sase.md` edits as authoritative user/workspace state. Do not revert them while finishing this
task.

## Proposed Work

1. Validate the current `~/bob/sase.md` conversion against the project-note convention:
   - keep `parent: "[[dev]]"` and `done_tasks: "[[done/sase_done]]"`;
   - keep `type: "[[project]]"`, `status: wip`, and the existing `created` timestamp;
   - keep the root project task:

     ```markdown
     - [ ] #task SASE is ready for regular use as a structured agentic software engineering system! [p::2] ^prj
       - 🧩 **Sub-projects:** [[sase_blog]] • [[sase_install]] • [[sase_piw_multi_prompt]]
     ```

   - keep the seven open non-`^prj` tasks under `## Tasks`;
   - keep `task_count: 7` and `open_task_count: 7` if validation confirms those counts still match;
   - keep the `## Project Notes` section and its `### Future Work` subsection.

2. Confirm all former `[p::1]` project backlog items in `~/bob/sase.md` are normal bullets:
   - no checkbox syntax;
   - no `#task`;
   - no `[p::1]` or `[p:: 1]` priority field;
   - preserve useful inline metadata such as `[created::...]`, `[dependsOn::...]`, `[id::...]`, links, and block IDs;
   - preserve child bullets under the moved parent bullets.

3. Apply the Q1 resolution for `sase_install.md`:
   - change only the frontmatter parent from `parent: "[[sase.md|sase]]"` to `parent: "[[sase]]"`;
   - do not change the Bob project resolver in code;
   - do not drop `[[sase_install]]` from the `sase.md` `^prj` sub-project line.

## Verification

After the note edits:

1. Run `rg -n '\[p::\s*1\]' ~/bob/sase.md` and confirm there are no matches.
2. Run `rg -n '^parent: "\\[\\[sase\\.md\\|sase\\]\\]"|^parent: "\\[\\[sase\\]\\]" ~/bob/sase_install.md` to confirm the
   parent link is normalized to `[[sase]]`.
3. Run `bob projects list -b ~/bob` and inspect the SASE-related rows for valid project status and expected counts.
4. Run `bob projects sync --dry-run -b ~/bob` and expect the dry run to stop wanting to remove `[[sase_install]]` from
   `~/bob/sase.md`.
5. Review `git -C ~/bob diff -- sase.md sase_install.md` and confirm the final diff is limited to:
   - the requested `sase.md` project conversion and future-work migration;
   - the one-line `sase_install.md` parent normalization from Q1.

## Guardrails

- Do not modify memory files.
- Do not update generated files under `~/bob/_generated`.
- Do not run mutating `bob projects sync`; use dry-run only for verification.
- Do not make broader `bob-cli` code changes for this task.
- Preserve unrelated dirty vault changes and avoid formatting churn outside the requested notes.
