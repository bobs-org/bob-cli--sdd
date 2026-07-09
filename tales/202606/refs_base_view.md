---
create_time: 2026-06-03 20:57:49
status: wip
prompt: sdd/prompts/202606/refs_base_view.md
---
# Plan: A Beautiful Obsidian Bases View for Ref Notes

## Goal

Create a single Obsidian **Bases** file at the vault root that renders all of Bryan's ref notes (the 292 markdown files
living under `~/bob/ref/`) as a polished, browsable database — with topic grouping, color-coded status badges, a reading
queue, and one-click links to each note's original source.

## Important correction: `.base`, not `.bases`

The request names the file `~/bob/refs.bases`, but Obsidian's Bases plugin only recognizes the **`.base`** extension
(confirmed by the existing `~/bob/Untitled.base` stub and by Obsidian's official docs). A file named `refs.bases` would
be treated as an unknown file type and would **not render** as a table. I will therefore create **`~/bob/refs.base`**
(vault root, as requested). If you truly want the literal name `refs.bases`, say so and I'll match it — but it won't
display as a Base.

## What I learned about the data

`~/bob/ref/` holds **292 `.md` notes** across 5 category subfolders, almost all nested one more level into per-topic
`*_ref` folders:

| Category folder | Count | Notes                                                                                                                                                                   |
| --------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ref/ai/*`      | 282   | organized into topic folders: `agent_ref` (112), `claude_code_ref` (63), `ai_ref` (36), `gemini_cli_ref` (26), `xprompt_ref` (24), `mcp_ref` (11), `langgraph_ref` (10) |
| `ref/papers/`   | 3     | arXiv-style PDFs                                                                                                                                                        |
| `ref/chat/`     | 4     | chat transcripts                                                                                                                                                        |
| `ref/docs/`     | 2     | product docs                                                                                                                                                            |
| `ref/blogs/`    | 1     | blog posts                                                                                                                                                              |

**Frontmatter properties** (coverage across all 292):

- `type` → always `"[[ref]]"` (100%)
- `status` → 100%. Values: `unread` (144), `collect_fleeting_notes` (92), `read` (28), `review_fleeting_notes` (13),
  `wip` (6), `abandoned` (5), `review_lit_notes` (4)
- `parent` → 100%, a wikilink to the topic note (e.g. `"[[mcp_ref]]"`) — ideal grouping key
- `title` → 285/292 (human-readable title)
- `url` → 280/292 (original web source)
- `tags` → 282 (e.g. `ai/reference`, `dev`)
- A newer PDF-highlights pipeline adds `ref_type`, `highlights_count`, etc. to ~10 notes

The two design-relevant facts: **everything has `status` + `parent`**, and **nearly everything has `title` + `url`**.
The plan leans on those, with graceful fallbacks for the few that lack `title`/`url`.

Verified environment: the `bases` core plugin is **enabled** in `~/bob/.obsidian/core-plugins.json`.

## Design

A single `refs.base` file with **three table views**, each a different lens on the same 292 notes.

### Global scope (filters)

```yaml
filters:
  and:
    - 'file.path.startsWith("ref/")' # recursive: captures all nested subfolders
    - 'file.ext == "md"' # excludes the .base file & any stray non-notes
```

I use `file.path.startsWith("ref/")` rather than `file.inFolder("ref")` because it is unambiguously recursive across the
`ai/<topic>_ref/` nesting and the trailing slash prevents accidentally matching a sibling like `reference.md`.

### Formulas (the "beautiful" layer)

| Formula        | Purpose                                                                                                                             |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `title_link`   | Clickable note title; falls back to filename when `title` is absent: `if(note.title, file.asLink(note.title), file.asLink())`       |
| `category`     | Emoji-labeled category derived from the folder: 🤖 AI / 📄 Paper / 📰 Blog / 📚 Docs / 💬 Chat                                      |
| `status_badge` | Color-dot status label, e.g. 🔵 Unread, 🟡 Collecting, 🟠 Review · Fleeting, 🟣 Review · Lit, 🛠️ In Progress, ✅ Read, ⚫ Abandoned |
| `source`       | One-click external link to the note's `url`: `if(note.url, link(note.url, "🔗 Source"), "")`                                        |

### Views

1. **📚 All Refs** — the headline view. Grouped by `parent` (topic), so the table reads as collapsible sections
   (agent_ref, claude_code_ref, …). Columns: Title · Category · Status · Source · Updated. Sorted alphabetically within
   each topic.

2. **🔖 Reading Queue** — only actionable notes (`unread`, `wip`, `collect_fleeting_notes`, `review_fleeting_notes`,
   `review_lit_notes`), grouped by status, **newest-updated first**. Columns add a Topic column since it's not the group
   key.

3. **📊 By Status** — the whole collection grouped by `status` for a portfolio/overview lens (how much is unread vs.
   read vs. abandoned). Columns: Title · Topic · Category · Updated.

Column display names are set via the `properties` section (Title, Category, Status, Source, Topic, Updated).

### Proposed file contents (`~/bob/refs.base`)

```yaml
filters:
  and:
    - 'file.path.startsWith("ref/")'
    - 'file.ext == "md"'

formulas:
  title_link: "if(note.title, file.asLink(note.title), file.asLink())"
  category:
    'if(file.folder.contains("/ai/"), "🤖 AI", if(file.folder.contains("/papers"), "📄 Paper",
    if(file.folder.contains("/blogs"), "📰 Blog", if(file.folder.contains("/docs"), "📚 Docs",
    if(file.folder.contains("/chat"), "💬 Chat", "🔖 Ref")))))'
  status_badge:
    'if(status == "unread", "🔵 Unread", if(status == "collect_fleeting_notes", "🟡 Collecting", if(status ==
    "review_fleeting_notes", "🟠 Review · Fleeting", if(status == "review_lit_notes", "🟣 Review · Lit", if(status ==
    "wip", "🛠️ In Progress", if(status == "read", "✅ Read", if(status == "abandoned", "⚫ Abandoned", status)))))))'
  source: 'if(note.url, link(note.url, "🔗 Source"), "")'

properties:
  formula.title_link:
    displayName: Title
  formula.category:
    displayName: Category
  formula.status_badge:
    displayName: Status
  formula.source:
    displayName: Source
  note.parent:
    displayName: Topic
  file.mtime:
    displayName: Updated

views:
  - type: table
    name: 📚 All Refs
    order:
      - formula.title_link
      - formula.category
      - formula.status_badge
      - formula.source
      - file.mtime
    groupBy:
      property: note.parent
      direction: ASC
    sort:
      - property: file.name
        direction: ASC

  - type: table
    name: 🔖 Reading Queue
    filters:
      or:
        - 'status == "unread"'
        - 'status == "wip"'
        - 'status == "collect_fleeting_notes"'
        - 'status == "review_fleeting_notes"'
        - 'status == "review_lit_notes"'
    order:
      - formula.title_link
      - note.parent
      - formula.category
      - formula.status_badge
      - file.mtime
    groupBy:
      property: status
      direction: ASC
    sort:
      - property: file.mtime
        direction: DESC

  - type: table
    name: 📊 By Status
    order:
      - formula.title_link
      - note.parent
      - formula.category
      - file.mtime
    groupBy:
      property: status
      direction: ASC
    sort:
      - property: file.mtime
        direction: DESC
```

## Implementation steps

1. Write the YAML above to `~/bob/refs.base`.
2. Validate it as well-formed YAML before finishing (e.g. a quick
   `python -c "import yaml,sys; yaml.safe_load(open('/home/bryan/bob/refs.base'))"`), and re-read the data assumptions
   hold (folder prefix, status values).
3. Report the result and ask Bryan to open `refs.base` in Obsidian to confirm rendering (Bases rendering itself can only
   be verified inside the Obsidian app).

## Decisions I made (leading the design)

- **One file, three views** instead of three files — keeps it a single artifact while still offering topic /
  reading-queue / status lenses.
- **Topic grouping** as the default view, because `parent` is the most meaningful axis (it maps to the `*_ref` hubs
  Bryan already uses) and turns 292 rows into ~11 tidy sections.
- **Emoji status badges + category** for visual scanning ("beautiful"), built as formulas so the underlying frontmatter
  is untouched.
- **No frontmatter changes** to any of the 292 notes — this is purely additive (one new file).
- Left the stray `~/bob/Untitled.base` in place (not part of this task); happy to remove it if you'd like.

## Out of scope / open questions

- Card/gallery view (would need cover images; ref notes don't have them).
- A `bob` CLI subcommand — not needed; this is a static vault file, no code changes.
- Confirm the `.base` vs `.bases` filename point above.
