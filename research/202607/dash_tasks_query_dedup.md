---
create_time: 2026-07-09
status: research
topic: De-duplicating Obsidian Tasks queries in ~/bob/dash.md
---

# Research: De-duplicating Dash Tasks Queries

## Question

`~/bob/dash.md` contains three nearly identical Obsidian Tasks query blocks:

- `WIP Tasks`: `status.type is IN_PROGRESS`
- `NEXT Tasks`: `status.name includes Next`
- `READY Tasks`: `status.type is TODO`

Every other query line is duplicated: template-folder exclusion, blocked-task
exclusion, current-file exclusion, scheduled-date gating, `#hide` exclusion,
path grouping, path/line sorting, short mode, and hidden toolbar.

What shared-query mechanism should Bryan use to de-duplicate these blocks?

## Local Context

Checked on 2026-07-09:

- `~/bob` is Bryan's Obsidian vault.
- `~/bob/dash.md` has exactly three `tasks` code blocks, at lines 14-57.
- The installed Tasks plugin is `8.0.0`
  (`~/bob/.obsidian/plugins/obsidian-tasks-plugin/manifest.json`).
- Tasks settings use `globalFilter: "#task"` and `taskFormat: "dataview"`.
- Tasks `globalQuery` is currently empty.
- Tasks settings already contain the default `presets` object in
  `~/bob/.obsidian/plugins/obsidian-tasks-plugin/data.json`.
- Custom statuses include:
  - `/` = `In Progress`, type `IN_PROGRESS`
  - `*` = `Next`, type `ON_HOLD`
- The existing `bob-project-tasks` custom plugin only materializes project
  task counts in frontmatter; it does not render or share Tasks queries.

The repeated common query body is:

```text
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

Because this query body uses `filter by function` and `sort by function`, it
depends on Tasks' JavaScript/custom-search support. In Tasks 8.0.0, JavaScript
in Tasks queries is disabled by default and must be enabled per device. This is
already true of the current `dash.md`; moving the lines to a preset or file
default does not change that requirement.

## Option 1: Query File Defaults

Tasks has a feature called Query File Defaults. It is designed for exactly this
shape of problem: several Tasks blocks in one Markdown file share instructions,
and the common text should live once in that file's frontmatter.

The relevant property is `TQ_extra_instructions`, a multiline frontmatter string
whose contents are inserted at the start of every Tasks query in that file.
There are also dedicated `TQ_*` frontmatter properties for layout toggles such
as short/full mode and show/hide toolbar, but a single
`TQ_extra_instructions` block can hold all common query lines.

Applied to `dash.md`, this would look like:

```yaml
---
parent: "[[gtd]]"
created: 2026-06-11T17:49:43-04:00
aliases:
  - Dashboard
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
---
```

Then each Tasks block becomes only its distinguishing status clause:

````markdown
### WIP Tasks

```tasks
status.type is IN_PROGRESS
```

### NEXT Tasks

```tasks
status.name includes Next
```

### READY Tasks

```tasks
status.type is TODO
```
````

Pros:

- Best fit for "three queries in the same note share everything except one
  status filter."
- The shared logic stays visible in `dash.md`, next to the dashboard it affects.
- No vault-wide side effects.
- No custom plugin work.
- Works with the installed Tasks version (`8.0.0`; Query File Defaults were
  introduced in Tasks 7.15.0).

Cons:

- It applies to every Tasks block in `dash.md`. If a future dashboard query
  needs different common filters, it should live in another note or this option
  should be reconsidered.
- It does not create a reusable shared definition for other files unless those
  files get their own `TQ_extra_instructions` frontmatter.

Source:

- https://raw.githubusercontent.com/obsidian-tasks-group/obsidian-tasks/main/docs/Queries/Query%20File%20Defaults.md

## Option 2: Tasks Presets

Tasks Presets let you define a named block of query instructions in Tasks
settings and reference it from individual query blocks with `preset name`.
They were introduced for reusable query patterns, including daily notes and
repeated sorting/filtering logic.

For example, define a preset such as `bob_dash_visible_tasks`:

```text
# Common visible dashboard task filters and layout
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

Then `dash.md` becomes:

````markdown
```tasks
status.type is IN_PROGRESS
preset bob_dash_visible_tasks
```

```tasks
status.name includes Next
preset bob_dash_visible_tasks
```

```tasks
status.type is TODO
preset bob_dash_visible_tasks
```
````

Pros:

- Best fit if the same shared query body should be reused across many notes.
- Keeps each Tasks block explicit about which shared preset it uses.
- Presets can also be used as placeholders inside boolean expressions or partial
  `filter by function`/`sort by function` lines.

Cons:

- The shared logic lives in Tasks settings, not in the note. That is less
  discoverable when reading `dash.md`.
- It still repeats one `preset ...` line in each query.
- It adds another piece of plugin configuration to manage.

Source:

- https://raw.githubusercontent.com/obsidian-tasks-group/obsidian-tasks/main/docs/Queries/Presets.md

## Option 3: Combine The Three Queries Into One Tasks Block

Tasks supports boolean combinations of filters, so the three status filters
could be merged:

````markdown
```tasks
((status.type is IN_PROGRESS) OR (status.name includes Next) OR (status.type is TODO))
folder does not include _templates
is not blocked
filter by function task.file.path !== query.file.path
filter by function !task.scheduled.moment || task.scheduled.moment.isSameOrBefore(moment(), "day")
filter by function !task.tags.includes("#hide")
group by function \
  if (task.status.type === "IN_PROGRESS") return "WIP Tasks"; \
  if (task.status.name.includes("Next")) return "NEXT Tasks"; \
  return "READY Tasks";
group by path
sort by function task.file.path
sort by function task.lineNumber
short mode
hide toolbar
```
````

This removes duplicated query blocks by turning them into one combined query.

Pros:

- Only one Tasks block.
- Keeps all logic in Markdown.
- Avoids frontmatter or plugin-settings coupling.

Cons:

- Changes the dashboard structure: the three sections become query groups
  rather than three Markdown headings with separate query result blocks.
- Custom group labeling adds more JavaScript, making the query harder to read.
- Separate per-section task counts/toolbars/results are lost or changed.
- It solves duplication by making one more complex query, not by sharing a
  reusable query definition.

Sources:

- https://raw.githubusercontent.com/obsidian-tasks-group/obsidian-tasks/main/docs/Queries/Combining%20Filters.md
- https://raw.githubusercontent.com/obsidian-tasks-group/obsidian-tasks/main/docs/Scripting/Custom%20Filters.md

## Option 4: Global Query

Tasks has a Global Query setting that prepends instructions to every Tasks
query in the vault. This could technically hold lines such as template-folder
exclusion or `#hide` filtering.

Pros:

- Strongest de-duplication for rules that truly apply to every Tasks query in
  the vault.
- Existing queries can opt out with `ignore global query`.

Cons:

- Too broad for the current problem.
- The dashboard's "not blocked" and "scheduled today or earlier" rules are not
  necessarily valid for every Tasks query. A blocked-task review or future-task
  planning query would be filtered by default.
- Tasks docs warn that not every Global Query filter is easy to override.

Source:

- https://raw.githubusercontent.com/obsidian-tasks-group/obsidian-tasks/main/docs/Queries/Global%20Query.md

## Option 5: Embedded Shared Note Or Block

Obsidian can embed notes, headings, and blocks with `![[...]]`; embedded content
stays up to date when the source changes. A shared note could hold one or more
Tasks blocks, and `dash.md` could embed them.

Pros:

- Uses native Obsidian transclusion.
- Good when a whole rendered dashboard section should appear in multiple notes.

Cons:

- It does not parameterize a query block. You would still need one source block
  per status section unless combined with another mechanism.
- The query text moves away from `dash.md`.
- Query-file context can become less obvious, because the query is authored in
  the embedded note rather than the dashboard note.

Source:

- https://obsidian.md/help/embeds

## Option 6: Custom Bob Plugin Or DataviewJS View

A custom plugin or DataviewJS view could define a dashboard DSL and render the
three Tasks sections from shared JavaScript code. This could live in
`bob-plugins` or in a vault script file.

Pros:

- Maximum control over rendering and reuse.
- Could eventually support richer dashboard behavior than Tasks query blocks.

Cons:

- Over-engineered for three duplicated query blocks.
- The public Tasks API does not currently expose "run this Tasks query and
  render/search results" as a supported API. The documented API covers task
  creation/editing/toggling, not query execution.
- Using private Tasks internals would be brittle across plugin upgrades.
- DataviewJS task rendering would not preserve all Tasks-plugin behavior unless
  reimplemented or routed through private APIs.

Source:

- https://raw.githubusercontent.com/obsidian-tasks-group/obsidian-tasks/main/docs/Advanced/Tasks%20Api.md

## Recommendation

Use **Tasks Query File Defaults** in `~/bob/dash.md`, specifically
`TQ_extra_instructions`, and reduce the three Tasks blocks to only their status
filter lines.

This is the cleanest match for the current shape: one note contains multiple
Tasks blocks with a shared query body. It keeps the shared logic visible in
`dash.md`, avoids vault-wide Global Query side effects, avoids a custom plugin,
and does not require moving the common logic into hidden plugin settings.

If the same common query body later needs to be reused across many notes, add a
Tasks Preset and either:

1. reference that preset in each query block, or
2. put `preset bob_dash_visible_tasks` in each relevant file's
   `TQ_extra_instructions`.

For the current `dash.md` problem, start with file-local
`TQ_extra_instructions`; it is the smallest durable change with the fewest
surprises.
