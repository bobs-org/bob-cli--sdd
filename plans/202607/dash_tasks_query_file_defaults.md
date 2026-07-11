---
create_time: 2026-07-09 12:54:31
status: wip
prompt: .sase/sdd/plans/202607/prompts/dash_tasks_query_file_defaults.md
tier: tale
---
# Plan: De-duplicate `dash.md` Tasks queries with Query File Defaults

## Goal

Use Obsidian Tasks Query File Defaults to remove the repeated shared query body from the three Tasks queries in
`~/bob/dash.md`, while preserving the rendered dashboard behavior.

## Current facts

- `~/bob` is the Obsidian vault.
- `~/bob/dash.md` has exactly three `tasks` code blocks under:
  - `WIP Tasks`
  - `NEXT Tasks`
  - `READY Tasks`
- The three blocks differ only by their status selector:
  - `status.type is IN_PROGRESS`
  - `status.name includes Next`
  - `status.type is TODO`
- The installed Tasks plugin is version `8.0.0`.
- Tasks settings currently have `globalQuery: ""` and `globalFilter: "#task"`.
- The existing queries already use `filter by function` and `sort by function`, so this change must preserve the current
  JavaScript-query requirement rather than introduce a new one.
- Upstream Tasks docs say Query File Defaults apply to every Tasks query in one Markdown file, are defined in
  frontmatter properties, and are assembled after Global Query and before the source `tasks` block.

## Proposed design

Add a file-scoped `TQ_extra_instructions` YAML scalar to the frontmatter of `~/bob/dash.md`. Put the shared query body
there exactly once:

```yaml
TQ_extra_instructions: |-
  folder does not include _templates
  is not blocked
  filter by function task.file.path !== query.file.path
  filter by function !task.scheduled.moment || task.scheduled.moment.isSameOrBefore(moment(), "day")
  filter by function !task.tags.includes("#hide")
  group by path
  sort by function task.file.path
  sort by function task.lineNumber
  short mode
  hide toolbar
```

Then reduce each Tasks block to only its status selector:

```tasks
status.type is IN_PROGRESS
```

```tasks
status.name includes Next
```

```tasks
status.type is TODO
```

Do not change Tasks plugin settings, Presets, Global Query, task statuses, or any other vault notes.

## Implementation steps

1. Re-read `~/bob/dash.md` immediately before editing to avoid overwriting concurrent user changes.
2. Add `TQ_extra_instructions` to the existing frontmatter, preserving existing `parent`, `created`, and `aliases`
   fields.
3. Replace the body of each of the three `tasks` code blocks with its unique status selector only.
4. Keep the Markdown headings and surrounding dashboard embeds unchanged.
5. Avoid adding explanatory prose to the note body; the frontmatter property itself is the source of truth.

## Verification

1. Confirm `~/bob/dash.md` still has exactly three `tasks` code blocks.
2. Confirm the only instructions inside those blocks are the three status selector lines.
3. Confirm the frontmatter contains one multiline `TQ_extra_instructions` value with all ten shared instructions.
4. Confirm no Tasks settings files changed.
5. Review the effective assembled queries manually:
   - Global Query contributes nothing because it is empty.
   - Query File Defaults contribute the shared body.
   - Each `tasks` block contributes its status selector.
6. If a renderer-level check is available locally, open or refresh `dash.md` in Obsidian/obsidian-headless and verify
   that the WIP, NEXT, and READY sections still render without query errors.

## Risks and mitigations

- `TQ_extra_instructions` applies to every Tasks block in `dash.md`. This is currently fine because there are exactly
  three and all need the same shared body. If new dashboard task queries are added later, they will inherit these
  defaults unless moved to another note or changed to a Preset-based design.
- The existing queries use Tasks JavaScript custom searches. On Tasks 8, each rendering device must have custom searches
  enabled. This plan preserves the existing requirement but should mention it if verification shows disabled-JavaScript
  errors.
- YAML formatting matters. Use a literal block scalar (`|-`) because `TQ_extra_instructions` is a single multiline
  string, not an array.

## Sources checked

- Consolidated local research note: `.sase/sdd/research/202607/dash_tasks_query_dedup_consolidated.md`
- Tasks docs source: `docs/Queries/Query File Defaults.md`
- Tasks docs source: `docs/Queries/About Queries.md`
- Tasks docs source: `docs/Scripting/JavaScript in Tasks Queries.md`
- Local vault file: `~/bob/dash.md`
- Local Tasks settings: `~/bob/.obsidian/plugins/obsidian-tasks-plugin/data.json`
