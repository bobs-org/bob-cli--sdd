---
create_time: 2026-06-11 18:08:28
status: done
prompt: sdd/prompts/202606/fix_bad_area_type_links.md
---
# Plan: Fix Bad `[[area]]` Type Links in the Bob Vault

## Goal

Correct the over-eager note typing introduced by the bob-cli-6 epic's Phase 1 (vault commit `33f4239`, bead
`bob-cli-6.1`). That migration blanket-typed **every** note containing a `- [ ]` checkbox as `type: "[[area]]"`, which
wrongly swept in two groups that are not GTD areas of responsibility:

1. **Reference hub notes** (`*_ref.md` in the vault root, e.g. `ai_ref.md` — body literally reads
   "`[[X]] [[ref]] notes live here`"). These should carry `type: "[[ref]]"`, matching `sase_ref.md` and the ~300
   `ref/`-typed reading notes.
2. **Legacy zorg-mirror todo lists** (`soon_*` / `now_*` notes with `generated_from_zorg: true`). Their untyped siblings
   (`soon.md`, `soon_gtd.md`, `soon_own.md`, `soon_work.md`, `now_work.md`, `now_zorg.md`, `now_prjs.md`, …) prove the
   convention: these frozen zorg conversions carry **no** `type` field. The typed ones were only typed because they
   happened to contain `- [ ]` sub-bullets.

This also makes progress on Bryan's open task in `bob_projects.md`:
"`- [ ] #task Clean up bad links to [[area]] and [[project]]!`" (the `[[area]]` half; see Out of Scope for the
`[[project]]` half).

## Context Reviewed

- `memory/short/sase.md` (via AGENTS.md). `memory/long/cli_rules.md` is **not** required: no `bob` CLI subcommands or
  options are touched — this plan only edits vault note frontmatter.
- `~/bob/AGENTS.md`: the vault is live (Obsidian Sync) and dirty. Inspect `git -C ~/bob status` before editing, never
  touch unrelated pre-existing changes, and commit only this task's files via `/sase_git_commit` before terminating.
- Root cause confirmed via `git -C ~/bob log -S 'type: "[[area]]"'`: every bad typing below was added by commit
  `33f4239` ("feat: add Obsidian project and area types (bob-cli-6.1)"); the prior epic plan
  (`sdd/epics/202606/obsidian_projects.md`, Phase 1 classification table) explicitly — and, per Bryan's new guidance,
  wrongly — proposed `now_*`/`soon_*`/`*_ref.md` notes as areas.
- Type taxonomy: `type.md` is the parent of all type notes; `area.md`, `project.md`, and `ref.md` all have
  `parent: "[[type]]"`. Notes under `ref/` plus root-level `sase_ref.md` already use `type: "[[ref]]"`. Most other root
  `*_ref.md` hubs (e.g. `agent_ref.md`, `claude_code_ref.md`) carry no `type` at all — only the 12 listed below were
  mistyped as areas.
- Full inventory: exactly **26** notes link to `[[area]]` today — 24 via a frontmatter `type:` line (all using the
  identical quoted form `type: "[[area]]"`) and 2 via legitimate body prose (`project.md`'s type-contract text and the
  `bob_projects.md` task text). No note uses `parent: [[area]]`.
- Tasks-plugin impact check: **none** of the 18 notes to be edited contains a single `#task` line (the Tasks plugin
  global filter), so retyping/untyping them cannot affect Tasks queries, `dash.md`, or daily-note views.
- Automation impact check: `projects.base` filters on `note.type == link("project")`; `refs.base` filters on
  `file.path.startsWith("ref/")`; the `bob-project-tasks` plugin only acts on `type: "[[project]]"` notes (and its
  stale-count cleanup only fires on notes that _have_ `task_count` frontmatter, which none of the 18 do). The
  `bob-navigation-hotkeys` `create-project-note` command treats area/project notes as valid parents — after this fix,
  ref hubs and legacy zorg mirrors stop being valid project parents, which is the desired behavior.

## Classification (all 26 `[[area]]`-linking notes)

### A. Retype to `type: "[[ref]]"` — 12 reference hub notes

`ai_ref.md`, `alfred_ref.md`, `asciidoc_ref.md`, `dev_ref.md`, `gemini_cli_ref.md`, `keyboard_maestro_ref.md`,
`mcp_ref.md`, `nvim_ref.md`, `obsidian_ref.md`, `org_mode_ref.md`, `work_ref.md`, `zorg_ref.md`

Rationale: each body says "`[[ref]] notes live here`"; `sase_ref.md` is the established precedent for a root-level ref
hub typed `"[[ref]]"`. Their `parent` fields (existing ref-hub hierarchy, e.g. `ai_ref` → `dev_ref` → `dev`) are
untouched. They will not appear in `refs.base` (path-filtered to `ref/`) and carry no `status`, so the reading-list
pipeline is unaffected.

### B. Remove the `type` line entirely — 6 legacy zorg mirrors

`soon_dev.md`, `soon_zorg.md`, `prj/rap/soon_rap.md`, `now_dev.md`, `now_gtd.md`, `now_sase.md`

Rationale: all are `generated_from_zorg: true` frozen mirrors of `~/org` zorg files, in the same naming families as
their untyped siblings. Bryan named `soon_*` as the legacy example; `now_dev`/`now_gtd`/`now_sase` are the same kind of
zorg-era "Next Actions" mirror (their `- [ ]` items are indented zorg sub-bullets, not Tasks-plugin tasks). Alternative
considered and rejected: keeping `now_*` as areas — rejected because their actively-maintained counterparts (e.g.
`sase.md` with real `#task` items) are the areas now, and every untyped `now_*` sibling proves the convention. Only the
one `type: "[[area]]"` line is removed; all `zorg_*` provenance metadata, parents, bodies, and block anchors stay
byte-identical.

### C. Keep `type: "[[area]]"` — 6 genuine areas (no change)

`gtd_daily.md`, `job.md`, `mac_inbox.md`, `needs_attn_tasks.md`, `recur.md`, `sase.md`

These are real ongoing spheres of responsibility with actively-managed `#task` items (or, for `job.md`, the deliberate
Phase 1 retyping called out in the epic plan).

### D. Legitimate body links — 2 notes (no change)

`project.md` (type-contract prose: "Ongoing responsibilities use [[area]] instead") and `bob_projects.md` (task text
mentioning `[[area]]`).

## Implementation (single phase)

The whole change is 18 one-line frontmatter edits in `~/bob`, so one phase / one agent / one commit.

1. **Hygiene first**: `git -C ~/bob status --short` — note pre-existing dirty files; never stage or revert them. Re-read
   each target file immediately before writing (Obsidian Sync may have changed it).
2. **Bucket A**: in the 12 ref hub notes, replace the line `type: "[[area]]"` with `type: "[[ref]]"` (the line is
   identical in all 12; no other frontmatter or body changes).
3. **Bucket B**: in the 6 legacy zorg notes, delete the single `type: "[[area]]"` line (no other changes).
4. **Leave Buckets C and D untouched.** Leave the `bob_projects.md` cleanup task **open** — its `[[project]]` half is
   out of scope here (Bryan can close it after reviewing that half).

### Verification

- `grep -rl --include='*.md' '^type: .*\[\[area\]\]' ~/bob` returns exactly the 6 Bucket C files.
- Each Bucket A file has exactly one `type:` line with value `"[[ref]]"`; each Bucket B file has no `type:` line;
  frontmatter of all 18 files still YAML-parses (`python3 -c "import yaml, ..."` on the `---` block).
- `git -C ~/bob diff` for each edited file is exactly a one-line change (or one-line deletion); no other files staged.
- Re-run the `#task` audit on the 18 files (expect 0 matches) to confirm no Tasks-plugin/area-dashboard impact.
- Manual acceptance for Bryan: in Obsidian, `area.md`'s backlinks pane shows only the 6 genuine areas (plus the 2 prose
  mentions); `ref.md`'s backlinks now include the 12 hubs; metadata-menu `type` suggestions unchanged.
- Commit only the 18 files via `/sase_git_commit`, then close the bead tracking this plan.

## Risks

- **Live, dirty vault** (Obsidian Sync): mitigated by status checks, re-reading before each write, and staging only the
  18 task files.
- **Misclassification of `now_*` notes**: if Bryan actually still drives work from `now_dev`/`now_gtd`/`now_sase`,
  untyping them removes them from any future area dashboard. They contain no `#task` items, so nothing functional breaks
  today; re-adding a type later is a one-line change. Flagged here so plan review can override (move them to Bucket C)
  if my read is wrong.
- **Phase 1 audit invariant**: the bob-cli-6 epic established "every open-task note outside carve-outs is typed
  area/project". This plan deliberately narrows that invariant — the carve-out list now effectively includes
  zorg-generated mirror notes and ref hubs, whose `- [ ]` checkboxes are not Tasks-plugin tasks. Future audits should
  treat `#task`-bearing notes (not bare `- [ ]` checkboxes) as the signal that a note needs an area/project type.

## Out of Scope

- The `[[project]]` half of Bryan's cleanup task (e.g. whether book notes like `outlive.md` / `think_fast_and_slow.md`
  should stay `type: "[[project]]"` or move to a reading-list concept) — needs Bryan's taxonomy call.
- Typing the ~18 other root `*_ref.md` hubs that currently have **no** `type` (e.g. `agent_ref.md`,
  `claude_code_ref.md`, `gtd_ref.md`) as `"[[ref]]"` for full consistency — a natural follow-up if Bryan wants every ref
  hub typed, but they don't link to `[[area]]` so they're not part of this fix.
- Deleting or archiving the legacy `soon_*`/`now_*` zorg mirrors.
- Documenting a formal `ref`-type contract in `ref.md` (it's still a zorg-generated note serving double duty as the type
  note).
