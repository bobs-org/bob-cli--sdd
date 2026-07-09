---
create_time: 2026-06-06 06:58:30
status: wip
prompt: sdd/prompts/202606/new_note_created_field.md
---
# Plan: Add `created` Datetime to `new_note.md`

## Context

`~/bob/` is Bryan's Obsidian vault. The target template is `~/bob/_templates/new_note.md`, and the audited Obsidian
memory confirms new notes in this vault should preserve the existing `parent` frontmatter pattern.

The current template uses Obsidian Templater syntax:

- `parent` is computed from `tp.config.active_file?.path` or `tp.app.workspace.getLastOpenFiles()[0]`.
- The note heading is generated from `tp.file.title`.

The installed Templater plugin is version `2.20.5`; its settings use `_templates` as the template folder and point the
folder-template rule at `_templates/new_note.md`. The local plugin implementation documents and implements
`tp.file.creation_date(format = "YYYY-MM-DD HH:mm")` by formatting `this.config.target_file.stat.ctime`, which is the
target note file's creation timestamp.

## Goal

Add a `created` frontmatter field to `~/bob/_templates/new_note.md` so every new note created from this template records
the target note file's creation datetime.

## Proposed Change

Insert a new top-level YAML frontmatter field before `parent`:

```yaml
created: <% tp.file.creation_date("YYYY-MM-DD[T]HH:mm:ssZ") %>
```

This keeps the value dynamic until Templater renders the new note, and it records a full datetime with timezone offset
instead of Templater's default minute-only timestamp. The `[T]` literal follows Moment format syntax, and `Z` includes
the local timezone offset, producing values shaped like:

```yaml
created: 2026-06-06T07:15:30-04:00
```

## Scope

Change only `~/bob/_templates/new_note.md`.

Do not edit memory files, Templater plugin files, Obsidian settings, repo source code, or unrelated vault notes.

## Verification

After editing:

1. Re-read `~/bob/_templates/new_note.md` and confirm the frontmatter remains valid and includes `created` above the
   existing `parent` field.
2. Confirm the inserted expression uses `tp.file.creation_date(...)`, not `tp.date.now(...)`, so the value corresponds
   to the target note file creation time.
3. Optionally, if a lightweight automated render path is available, create a temporary test note from the template and
   inspect the rendered `created` value, then remove that temporary note. If that would risk vault churn, skip it and
   rely on the verified local Templater implementation.

## Risks and Mitigations

- **YAML parsing:** The generated timestamp contains colons. ISO-style YAML timestamps are valid as plain scalar values,
  and keeping the expression on one line matches existing Templater frontmatter style.
- **Wrong timestamp source:** Avoid `tp.date.now(...)` because that records render time, not the target file's creation
  timestamp. Use `tp.file.creation_date(...)`, verified locally to read `target_file.stat.ctime`.
- **Unrelated vault churn:** Do not change Obsidian settings or create permanent test notes.
