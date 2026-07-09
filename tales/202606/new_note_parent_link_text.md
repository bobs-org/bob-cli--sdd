---
create_time: 2026-06-07 09:57:21
status: done
prompt: sdd/prompts/202606/new_note_parent_link_text.md
---
# Plan: Hide `.md` In New Note Parent Link Text

## Goal

Update the Bob vault's `new_note.md` template so generated `parent` values still link to the inferred parent note, but
the visible wiki-link text no longer includes the trailing `.md` extension.

The existing parent-selection behavior should remain unchanged:

- Prefer the valid `tp.config.active_file` source note when it is not the target note or the template itself.
- Scan recent open files as a fallback.
- Skip the target note and `_templates/new_note.md`.
- Fall back to `[[org]]` when no valid parent note is available.

This plan is only for the display text of the chosen parent link.

## Context Reviewed

- Read project short memory from `memory/short/sase.md`.
- Read required Obsidian long memory through:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault/template workflow context before planning visible parent link text change"`.
- Read `/home/bryan/bob/AGENTS.md`; vault edits require a status check first, preserving unrelated dirty files, and
  committing only task-related vault changes with the SASE git commit workflow before finishing.
- Inspected the live template: `/home/bryan/bob/_templates/new_note.md`.
- Reviewed the approved/current-parent fallback plan: `sdd/tales/202606/new_note_current_parent_fallback.md`.
- Checked the last commit affecting the template: `99e0863 fix: infer parent from current note for new notes`.
- Confirmed `/home/bryan/bob` currently has many unrelated dirty files; the implementation must avoid touching, staging,
  or committing them.
- No new `bob-cli` CLI subcommands or options are being added, so `memory/long/cli_rules.md` is not required.

## Current Behavior

The current template returns a parent link like this when it finds a candidate:

```js
return path ? `[[${path}]]` : defaultParent;
```

Because the candidate is an Obsidian `TFile.path`, it usually includes the Markdown extension, for example:

```md
parent: "[[projects/example.md]]"
```

That makes the visible link text include `.md`.

## Desired Behavior

When a parent candidate is found, keep the link target as the resolved path but provide an alias whose display text
strips one trailing Markdown extension:

```md
parent: "[[projects/example.md|projects/example]]"
```

This preserves link-target reliability while changing only the visible text. The fallback should remain:

```md
parent: "[[org]]"
```

Important choice: do not simply remove `.md` from the link target. Obsidian often resolves extensionless wiki links, but
the current template already has a known-good target path from `tp.file.find_tfile(candidate)`. Keeping that target and
adding an alias is the narrower behavioral change.

## Primary Design

Update only `/home/bryan/bob/_templates/new_note.md`.

In the inline Templater expression, introduce display text derived from the selected path:

```js
const linkText = path.replace(/\.md$/i, "");
return path ? `[[${path}|${linkText}]]` : defaultParent;
```

The actual implementation should compute `linkText` only after a valid `path` has been selected. A helper expression is
acceptable if it keeps the single-line frontmatter style readable enough; otherwise keep the change minimal inside the
existing inline expression.

Behavioral details:

- Strip only a terminal `.md`, case-insensitively.
- Preserve folders in the visible text; this request is specifically to remove `.md`, not to switch to basename-only
  display text.
- Leave `[[org]]` unchanged because it already has no visible extension and is the established fallback.
- Leave candidate discovery, self-parent avoidance, template-file avoidance, and `getLastOpenFiles` guarding unchanged.
- Do not broaden the task into general wiki-link escaping or YAML quoting changes unless testing reveals that the alias
  syntax breaks the existing template format.

## Scope

Expected implementation file:

- `/home/bryan/bob/_templates/new_note.md`

Expected files not to edit:

- any generated or ordinary note files in `/home/bryan/bob`
- `/home/bryan/bob/.obsidian/**`
- any `bob-cli` source files
- any memory files

## Implementation Steps

1. Re-check vault status before editing:

   ```bash
   git -C /home/bryan/bob status --short -- _templates/new_note.md
   git -C /home/bryan/bob status --short
   ```

2. Edit only the `parent` expression in `/home/bryan/bob/_templates/new_note.md`.
3. Preserve the existing `created` line and heading.
4. Inspect the diff and confirm it is limited to the template expression.

## Verification

Static checks:

```bash
git -C /home/bryan/bob diff --check -- _templates/new_note.md
git -C /home/bryan/bob diff -- _templates/new_note.md
```

Focused JavaScript harness cases:

- Valid source path `projects/example.md` returns `[[projects/example.md|projects/example]]`.
- Valid source path `example.md` returns `[[example.md|example]]`.
- A path without a terminal `.md` still returns a valid alias, for example `[[example|example]]`.
- A path with uppercase `.MD`, if ever supplied, displays without that extension.
- Existing target/template skipping still prevents self-parenting and template-parenting.
- Invalid or missing candidates still return `[[org]]`.
- Missing `getLastOpenFiles` still does not throw.

Manual/live acceptance after Obsidian or Templater reloads the template:

1. Open a normal note whose path ends in `.md`.
2. Press `Cmd+N`.
3. Confirm the new note's `parent` links to the prior note.
4. Confirm the displayed parent text does not include `.md`.
5. Confirm the raw frontmatter uses alias syntax with the `.md` target preserved.
6. Create a note from a context with no source note and confirm the fallback remains `[[org]]`.
7. Delete any scratch notes created solely for testing.

## Risks

- Obsidian's property UI may display wiki-link aliases differently from reading mode/source mode. The raw frontmatter
  should still clearly encode the intended visible text via `[[target.md|target]]`.
- Keeping folders in the alias means a nested note displays as `folder/name`, not just `name`. That matches the narrow
  request to remove `.md`; switching to basename-only text would be a separate product decision.
- The existing template does not solve all possible special-character escaping issues in note paths. This plan keeps
  that unchanged to avoid broadening the behavior.
- A live Obsidian smoke test is the only way to verify the exact property-rendering behavior in the UI.

## Finish Criteria

- This plan is submitted with:

  ```bash
  sase plan sase_plan_new_note_parent_link_text.md
  ```

- No implementation files are edited before plan submission.
- If implementation later edits under `~/bob`, commit only `_templates/new_note.md` with the required SASE git commit
  workflow, leaving unrelated dirty vault changes untouched.
