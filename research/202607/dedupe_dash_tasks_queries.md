---
create_time: 2026-07-09
status: research
topic: De-duplicating the three near-identical Tasks queries in ~/bob/dash.md
---

# Research: De-duplicating the Tasks Queries in `dash.md`

## Question

`~/bob/dash.md` contains three ` ```tasks ` query blocks — **WIP Tasks**, **NEXT
Tasks**, and **READY Tasks** — that are nearly identical. Each shares ten
instruction lines and differs only in a single status-selector line. What
options exist for factoring the shared query text into one place, and which
should we adopt?

## TL;DR / Recommendation

Use the **Tasks plugin's native "Presets" feature**. Define one preset (e.g.
`dash_common`) holding the ten shared instruction lines, then shrink each block
to two lines: its unique status filter plus `preset dash_common`.

This is the purpose-built, first-party mechanism for exactly this problem. It
needs no new plugins, keeps each block a genuine live `tasks` query (filtering,
grouping, sorting, toolbar all unchanged), and the vault is already on Tasks
**v8.0.0** with Presets in active use. The alternatives (Global Query,
Templater, dataviewjs) each work in a narrow sense but are respectively too
broad, only DRY at authoring time, or discard Tasks-native behavior.

## What is actually duplicated

All three blocks are identical except for **one line** — the status selector:

| Block         | Distinct line                | Section heading in `dash.md` |
| ------------- | ---------------------------- | ---------------------------- |
| WIP Tasks     | `status.type is IN_PROGRESS` | `### WIP Tasks`              |
| NEXT Tasks    | `status.name includes Next`  | `### NEXT Tasks`            |
| READY Tasks   | `status.type is TODO`        | `### READY Tasks`           |

The other **ten lines** are copy-pasted verbatim across all three blocks:

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

So the ideal solution keeps the one distinct status line inside each block and
sources the ten shared lines from a single definition. Instruction **order
inside a `tasks` block does not matter** to the plugin, so the status line and
the shared block may appear in either order.

### Environment facts (verified locally, 2026-07-09)

- Installed Tasks plugin version: **8.0.0**
  (`~/bob/.obsidian/plugins/obsidian-tasks-plugin/manifest.json`;
  `"isDesktopOnly": false`, so it also works under `obsidian-headless`/`ob`).
- **Presets are already enabled and in use.** `data.json` ships the stock
  presets and they already demonstrate the two advanced capabilities we care
  about:
  - **Nesting** — `hide_everything` is literally
    `preset hide_date_fields` + `preset hide_non_date_fields` +
    `preset hide_query_elements`.
  - **Placeholders** — `this_file` is `path includes {{query.file.path}}`.
- `globalQuery` is currently the empty string `""` (nothing is applied
  vault-wide today).
- The only other `tasks` blocks in the vault are the daily notes under
  `~/bob/2026/` (one block each, 14 files) — relevant when weighing the
  blast radius of a Global Query change (Option 2).

## Options considered

### Option 1 — Tasks Presets  ✅ RECOMMENDED

The Tasks plugin lets you save a named block of query instructions as a
**preset** and reuse it in any query. Introduced in **Tasks 7.20.0**; the vault
runs **8.0.0**.

- **Define** in Settings → Tasks → *Presets* as a `name` → `instructions`
  pair. On disk this is a single string entry under the `presets` key of
  `~/bob/.obsidian/plugins/obsidian-tasks-plugin/data.json` (multi-line values
  are stored with `\n`).
- **Use** it two ways:
  - `preset <name>` — statement form; expands the named instructions inline.
    This is the normal case and the one we need here.
  - `{{preset.<name>}}` — placeholder form; needed only when the fragment must
    sit inside a Boolean expression, e.g.
    `({{preset.work_tasks}}) AND ({{preset.high_priority}})`. The statement
    form cannot be used inside Boolean combinations.
- Presets can be **combined** with other instructions in the same block, can
  **nest** other presets, and can contain **placeholders** like
  `{{query.file.path}}`.
- **Limitation:** presets take **no parameters** — per the docs they are
  "applied exactly as written and cannot be modified when used." This is a
  non-issue here: the only thing that varies (the status line) simply stays in
  each block.

**Pros**

- Native, first-party, zero new dependencies; already enabled in this vault.
- Exact fit — shared text lives in one place; each block keeps only its status
  line.
- Each block stays a real `tasks` query: live filtering, grouping, sorting, and
  toolbar behave exactly as they do today.
- Reusable if similar dashboards appear later.
- **Headless-friendly** — presets are plain JSON in `data.json`, so they can be
  managed through the `ob` workflow, not only the desktop GUI.

**Cons**

- The shared definition lives in plugin settings, not in `dash.md`, so it's
  slightly less discoverable from the note itself. Mitigate with a leading `#`
  comment line in the preset documenting its purpose (Tasks treats `#` lines as
  comments).
- Vault-global namespace: the preset name is visible to every query in the
  vault (harmless — just pick a clear name like `dash_common`).

### Option 2 — Global Query

Tasks has a **Global Query** setting whose instructions are prepended to
*every* `tasks` block in the vault.

**Pros**

- Zero per-block syntax; shared filters apply automatically everywhere.

**Cons (disqualifying here)**

- Applies to **every query in the entire vault**, including the 14 daily-note
  blocks under `~/bob/2026/`. The shared lines are dashboard-specific
  (`group by path`, `short mode`, `hide toolbar`, the "not this file" and
  "not #hide" filters) and are not wanted on those unrelated queries.
- Opting out is **all-or-nothing**: a query can add `ignore global query`, but
  cannot selectively drop a single line. And the docs warn "It isn't always
  possible to override a filter set in the Global Query" (tracked in Tasks issue
  #2074).
- `globalQuery` is empty today; commandeering it for one dashboard would be a
  surprising global side effect.

**Verdict:** wrong scope. Good for truly vault-wide defaults, not for three
blocks in one file.

### Option 3 — Templater generation

Use a Templater template that takes a status argument and emits a full `tasks`
block, invoked three times.

**Pros**

- Fully DRY at authoring time; can parameterize the status line.

**Cons**

- De-duplicates only at *generation* time — the rendered `dash.md` on disk
  still contains three fully-expanded blocks, so the file itself is not smaller
  unless kept as a template that must be re-run.
- Adds Templater indirection and a manual regeneration step for what is a
  static dashboard.
- More moving parts than Presets for no extra benefit.

**Verdict:** over-engineered for this case.

### Option 4 — dataviewjs / Tasks Query API

Render the three queries from a loop in a `dataviewjs` block, or via the Tasks
query-rendering API.

**Cons**

- Either rewrites the queries in Dataview's dialect (losing Tasks-specific
  status semantics, the toolbar, and the Tasks instruction set) or leans on
  non-obvious internal APIs.
- Highest complexity and lowest robustness of all options.

**Verdict:** not worth it.

### Option 5 — Do nothing

Keep the duplication.

- The only real cost today is the three-way manual edit whenever a shared
  filter changes. Presets removes that cost cheaply, so there's little reason to
  accept the status quo.

## Comparison at a glance

| Option           | Truly DRY on disk | Keeps native Tasks behavior | Scope = just `dash.md` | New dependency | Headless-editable |
| ---------------- | :---------------: | :-------------------------: | :--------------------: | :------------: | :---------------: |
| **1. Presets**   | ✅               | ✅                          | ✅                    | none           | ✅                |
| 2. Global Query  | ✅ (but shared)   | ✅                          | ❌ (whole vault)      | none           | ✅                |
| 3. Templater     | ❌ (expands)      | ✅                          | ✅                    | Templater      | partial           |
| 4. dataviewjs    | ✅               | ❌                          | ✅                    | Dataview       | ✅                |
| 5. Do nothing    | ❌               | ✅                          | ✅                    | none           | n/a               |

## Recommended solution (implementation sketch)

Adopt **Option 1 (Presets)**.

### 1. Define the preset

Add a preset named `dash_common` (Settings → Tasks → Presets, or directly in
`data.json` under `presets`) with this value:

```text
# Shared filters/layout for the dash.md task lists
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

As a `data.json` entry (note the escaped newlines and quotes) it looks like:

```json
"dash_common": "# Shared filters/layout for the dash.md task lists\nfolder does not include _templates\nis not blocked\nfilter by function task.file.path !== query.file.path\nfilter by function !task.scheduled.moment || task.scheduled.moment.isSameOrBefore(moment(), \"day\")\nfilter by function !task.tags.includes(\"#hide\")\ngroup by path\nsort by function task.file.path\nsort by function task.lineNumber\nshort mode\nhide toolbar"
```

### 2. Rewrite the three blocks in `dash.md`

````markdown
### WIP Tasks

```tasks
status.type is IN_PROGRESS
preset dash_common
```

### NEXT Tasks

```tasks
status.name includes Next
preset dash_common
```

### READY Tasks

```tasks
status.type is TODO
preset dash_common
```
````

Each block drops from twelve lines to two, and the shared logic now has a single
home.

### 3. Verify

Reload the vault (or reopen `dash.md`) and confirm all three lists render
identically to before. If Tasks reports an unknown-preset error, the preset
name/definition didn't save — re-check the `presets` entry in `data.json` or the
Presets settings pane.

## Notes / caveats

- **Editing `data.json` directly (headless via `ob`):** ensure Obsidian isn't
  simultaneously writing the file and keep the JSON valid. When a GUI is
  available, the Settings → Presets pane is the safest path.
- **Documentation comment:** the leading `# …` line inside the preset is a Tasks
  comment; it documents intent and is ignored at execution time.
- **Placeholder form not needed here:** `preset dash_common` (statement form) is
  correct because we're inserting whole instruction lines. Reserve
  `{{preset.dash_common}}` for cases where a fragment must sit inside a Boolean
  (`AND`/`OR`/`NOT`) expression.
- **Don't reuse `hide_query_elements` for the toolbar line.** The stock
  `hide_query_elements` preset hides more than the dashboard currently does
  (`hide toolbar` + postpone/edit/backlinks). Keeping a plain `hide toolbar`
  inside `dash_common` preserves today's exact behavior; only nest
  `hide_query_elements` if you later decide to hide those extra elements too.

## Related prior work

A near-identical research note already exists in the repo at
`sdd/research/202607/dedupe_dash_tasks_queries.md` (commit `251469b`, authored by
a prior `research.4.cld` agent). This document reaches the same conclusion and
additionally re-verifies every external claim against the official Tasks docs
and every environment claim against the live vault on 2026-07-09.

## Sources

- [Presets — Tasks User Guide](https://publish.obsidian.md/tasks/Queries/Presets)
  — introduced in 7.20.0; `preset <name>` and `{{preset.<name>}}` forms; "applied
  exactly as written and cannot be modified when used"; nesting via
  `hide_everything`.
- [Global Query — Tasks User Guide](https://publish.obsidian.md/tasks/Queries/Global+Query)
  — prepended to all queries; `ignore global query` opt-out; "It isn't always
  possible to override a filter set in the Global Query" (issue #2074).
- [About Queries — Tasks User Guide](https://publish.obsidian.md/tasks/Queries/About+Queries)
- Local: `~/bob/.obsidian/plugins/obsidian-tasks-plugin/manifest.json` (v8.0.0)
  and `data.json` (existing presets incl. nesting + placeholders; empty
  `globalQuery`).
