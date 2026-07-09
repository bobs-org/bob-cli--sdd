---
create_time: 2026-07-09
status: research
topic: De-duplicating the three Obsidian Tasks queries in ~/bob/dash.md
---

# Research: De-duplicating `dash.md` Tasks Queries

## Question

`~/bob/dash.md` has three Obsidian Tasks query blocks: **WIP Tasks**,
**NEXT Tasks**, and **READY Tasks**. They are nearly identical and differ only
in the status selector. What shared-query mechanism should Bryan use?

## Prior Work Checked

The two research drafts agreed on the local facts but disagreed on the
recommendation:

- `.sase/sdd/research/202607/dash_tasks_query_dedup.md` recommended **Query
  File Defaults**.
- `.sase/sdd/research/202607/dedupe_dash_tasks_queries.md` recommended
  **Presets**.

The conflict resolves in favor of **Query File Defaults** for the current
request because the duplication is file-local: all three affected queries are
in one note, and the official Tasks docs describe Query File Defaults as the
feature for multiple Tasks searches in one Markdown file sharing common
instructions. Presets remain the best runner-up if the same common query body
needs to be reused across multiple notes.

## Local Facts

Verified on 2026-07-09:

- `~/bob` is the Obsidian vault.
- `~/bob/dash.md` has exactly three `tasks` code blocks, at lines 14, 30, and
  46.
- Installed Tasks plugin version is `8.0.0`
  (`~/bob/.obsidian/plugins/obsidian-tasks-plugin/manifest.json`).
- The installed Tasks plugin contains both Query File Defaults support
  (`TQ_extra_instructions`, `TQ_short_mode`, `TQ_show_toolbar`) and Presets
  support.
- `~/bob/.obsidian/plugins/obsidian-tasks-plugin/data.json` has
  `globalQuery: ""`.
- `data.json` already includes the stock `presets` object, including examples
  of nesting (`hide_everything`) and placeholders (`this_file`).
- The vault currently has 17 `tasks` blocks: three in `dash.md` and 14 in daily
  notes under `~/bob/2026/`. This matters because Global Query would affect the
  daily-note queries too.
- The three `dash.md` queries already use `filter by function` and
  `sort by function`, so Tasks 8's JavaScript-query setting must be enabled on
  any device that renders them. De-duplicating these lines does not add a new
  JavaScript requirement.

## What Is Duplicated

Each block has one distinct status line:

| Section | Distinct line |
| --- | --- |
| WIP Tasks | `status.type is IN_PROGRESS` |
| NEXT Tasks | `status.name includes Next` |
| READY Tasks | `status.type is TODO` |

The shared body is copied into all three blocks:

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

The ideal solution keeps the status line in each block and puts this shared
body in one place.

## Options

### 1. Query File Defaults - Recommended

Tasks Query File Defaults are file-scoped query instructions defined in the
note's frontmatter. The key property here is `TQ_extra_instructions`, a
multiline string that Tasks inserts at the start of every `tasks` block in that
file.

For `dash.md`, the frontmatter could become:

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

Then the three blocks shrink to:

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

- Best scope match: shared instructions apply only to `dash.md`.
- The dashboard remains self-contained; the common query body stays in the
  note, not in plugin settings.
- No new plugin, custom code, template regeneration, or vault-wide setting.
- It produces the smallest query blocks: each block only contains the status
  selector.
- The official docs call out this exact use case: multiple Tasks searches in a
  file with common instructions that are tedious to keep synchronized.

Cons:

- It applies to every `tasks` block in `dash.md`. If a future dashboard query
  needs different shared filters, either move that query to another note, use a
  Preset for explicit per-block opt-in, or reconsider the structure.
- The shared instructions move from code blocks into frontmatter. That is still
  visible in the file, but less obvious than plain query text while reading the
  body.

Notes:

- Tasks also provides dedicated Query File Defaults such as
  `TQ_short_mode: true` and `TQ_show_toolbar: false`. Those could replace the
  final two lines, but a single `TQ_extra_instructions` block is the simplest
  direct transformation and preserves the existing query text verbatim.
- Tasks assembles queries as Global Query, then Query File Defaults, then the
  block source. Filters combine; later layout instructions override earlier
  layout instructions. This ordering is fine for the proposed `dash.md` shape.

### 2. Tasks Presets

Tasks Presets define named reusable instruction blocks in Tasks settings, then
individual queries opt in with `preset <name>`.

Example preset:

```text
# Shared filters/layout for dash.md task lists
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

Usage:

````markdown
```tasks
status.type is IN_PROGRESS
preset dash_common
```
````

Pros:

- Best option if this shared query body should be reused in multiple notes.
- Per-block opt-in is explicit, so a future `dash.md` query can skip the preset.
- Already supported by the installed Tasks version and existing settings file.
- Presets can nest other presets and can be referenced as placeholders when a
  partial expression is needed.

Cons:

- The shared body lives in `data.json` / Tasks settings, not in `dash.md`.
- Each query still needs a `preset dash_common` line.
- Presets are vault-global names. That is usually harmless, but it is broader
  than necessary for three blocks in one note.

Verdict: strong fallback, but not the cleanest first move for this specific
file-local duplication.

### 3. Query File Defaults Plus Presets

A hybrid is possible:

```yaml
TQ_extra_instructions: |-
  preset dash_common
```

This keeps each `dash.md` block to one status line while storing the shared body
in a Preset.

Verdict: useful if the same common body will be shared by many files, but it is
unnecessary indirection for the current `dash.md`-only problem.

### 4. Global Query

Tasks Global Query prepends instructions to every Tasks query in the vault.

Pros:

- Zero per-query syntax.
- Good for truly vault-wide defaults.

Cons:

- Wrong scope here: it would affect the 14 daily-note queries, not just
  `dash.md`.
- The shared dashboard body includes layout and grouping instructions that are
  not obviously desirable everywhere.
- Opt-out is all-or-nothing via `ignore global query`, and the Tasks docs warn
  that Global Query filters are not always overrideable.

Verdict: do not use for this request.

### 5. One Combined Tasks Query

The three status filters could be combined with Boolean logic in one Tasks
block, with custom grouping to recreate WIP/NEXT/READY sections.

Pros:

- Only one query block.
- No plugin settings or frontmatter property.

Cons:

- Changes the dashboard structure from three Markdown sections to one rendered
  query with generated groups.
- Requires more custom JavaScript for group labels.
- Changes counts, toolbar behavior, and section-level ergonomics.

Verdict: technically possible, but more complex and less faithful to the
current dashboard.

### 6. Templater, Embeds, DataviewJS, Or A Custom Plugin

These are possible but poor fits:

- **Templater** can generate the repeated query blocks, but the saved
  `dash.md` still contains expanded duplicated text.
- **Obsidian embeds** can reuse whole rendered sections, but cannot
  parameterize one Tasks query body by status without another mechanism.
- **DataviewJS** can render task lists from code, but loses or must reimplement
  Tasks-native query semantics and UI behavior.
- **Custom plugin / Tasks API** is over-engineered. The public Tasks API exposed
  by the installed plugin covers task creation, editing, and toggling; relying
  on private query-rendering internals would be brittle.

Verdict: not recommended for three duplicated query blocks.

## Recommendation

Use **Tasks Query File Defaults** in `~/bob/dash.md`, specifically
`TQ_extra_instructions`, and reduce each of the three Tasks blocks to only its
status selector.

Why this is the best current solution:

- It is the native Tasks feature whose documented use case matches this exact
  file-local duplication.
- It avoids the broader scope of Presets and Global Query.
- It keeps the dashboard logic self-contained in `dash.md`.
- It preserves the existing rendered behavior: same status filters, same
  blocking/scheduled/hidden filters, same grouping, same sort order, same short
  mode, same hidden toolbar.

Use a **Preset** instead if the same shared query body later needs to be reused
across several notes, or if `dash.md` grows additional Tasks queries that should
not inherit the dashboard defaults.

## Sources

- Tasks User Guide: Query File Defaults  
  https://publish.obsidian.md/tasks/Queries/Query+File+Defaults
- Tasks User Guide: Presets  
  https://publish.obsidian.md/tasks/Queries/Presets
- Tasks User Guide: About Queries  
  https://publish.obsidian.md/tasks/Queries/About+Queries
- Tasks User Guide: Global Query  
  https://publish.obsidian.md/tasks/Queries/Global+Query
- Tasks User Guide: Comments  
  https://publish.obsidian.md/tasks/Queries/Comments
- Tasks User Guide: Custom Filters  
  https://publish.obsidian.md/tasks/Scripting/Custom+Filters
- Tasks User Guide: Custom Sorting  
  https://publish.obsidian.md/tasks/Scripting/Custom+Sorting
- Local: `~/bob/dash.md`
- Local: `~/bob/.obsidian/plugins/obsidian-tasks-plugin/manifest.json`
- Local: `~/bob/.obsidian/plugins/obsidian-tasks-plugin/data.json`
