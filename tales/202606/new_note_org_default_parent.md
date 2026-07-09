---
create_time: 2026-06-07 08:52:35
status: done
prompt: sdd/prompts/202606/new_note_org_default_parent.md
---
# Plan: Default Cmd+N New-Note Parent To `[[org]]`

## Goal

When `Cmd+N` creates a new note through the Bob vault's root Templater folder-template rule, the rendered `parent`
frontmatter should default to `[[org]]`.

Keep the existing useful behavior for explicit Templater-created notes, especially the Bob missing-link/Enter flow: when
a note is created from a source note via Templater's `create_new_note_from_template(...)` API, `parent` should still
prefer the source/active note when Templater exposes one.

## Context Reviewed

- Read project short memory from `memory/short/sase.md`.
- Read required Obsidian long memory through:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault workflow before planning a default new-note template change"`.
- Read local project `AGENTS.md`; no new CLI commands or options are being added, so `memory/long/cli_rules.md` is not
  required.
- Read `/home/bryan/bob/AGENTS.md`; vault edits require a status check first, preserving unrelated pre-existing changes,
  and committing only task-related files with the SASE git commit workflow before finishing.
- Re-read the approved prior plan `sdd/tales/202606/obsidian_cmd_n_new_note_template.md`.
- Inspected the live vault state:
  - `/home/bryan/bob/.obsidian/plugins/templater-obsidian/data.json` already has the root folder-template rule:
    `{ "folder": "/", "template": "_templates/new_note.md" }`.
  - `/home/bryan/bob/_templates/new_note.md` is already modified before this task. The current dirty diff is the prior
    new-note work that inlined the `parent` Templater expression and added `created`.
  - `org.md` exists at the vault root, and other templates already use `parent: "[[org]]"`.
- Inspected the installed Templater implementation enough to distinguish relevant render modes:
  - `create_new_note_from_template(...)` renders with `tp.config.run_mode === 0`.
  - folder-template/file-creation expansion renders with `tp.config.run_mode === 2`.

## Interpretation

Treat "in that case" as the `Cmd+N` path enabled by the prior change: Obsidian creates an empty file and Templater fills
it through the root folder-template rule.

Use `[[org]]` for that folder-template/file-creation path. Do not make every `_templates/new_note.md` render always use
`[[org]]`, because that would regress source-note parenting for the existing missing-link creation workflow.

## Design

Update only `/home/bryan/bob/_templates/new_note.md`.

Change the `parent` Templater expression so it:

1. Defines a default parent value of `[[org]]`.
2. If `tp.config.run_mode === 2`, returns `[[org]]` immediately. This covers `Cmd+N` notes created by the root
   folder-template rule.
3. Otherwise, preserves the existing source-note selection logic:
   - prefer `tp.config.active_file?.path`;
   - fall back to `tp.app.workspace.getLastOpenFiles()[0]`;
   - return a wikilink only when `tp.file.find_tfile(path)` resolves.
4. If no valid source path is available in non-folder-template paths, return the same `[[org]]` default instead of an
   empty `parent` value.

Keep the current inline YAML shape and the existing `created` field intact unless a syntax issue is found during
verification.

## Expected Implementation Diff

The intended implementation is a single-line logical change in the template frontmatter, conceptually:

```md
parent: "<% (() => { const defaultParent = '[[org]]'; if (tp.config.run_mode === 2) return defaultParent; const
activePath = tp.config.active_file?.path; const lastOpenPath = tp.app.workspace.getLastOpenFiles()[0]; const path =
activePath || lastOpenPath; return path && tp.file.find_tfile(path) ? `[[${path}]]` : defaultParent; })() %>"
```

No planned changes to:

- `/home/bryan/bob/.obsidian/plugins/templater-obsidian/data.json`
- `/home/bryan/bob/.obsidian/hotkeys.json`
- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
- any `bob-cli` Rust source
- any memory files

## Implementation Steps

1. Re-check `git -C /home/bryan/bob status --short` immediately before editing.
2. Edit only the `parent` expression in `/home/bryan/bob/_templates/new_note.md`.
3. Preserve the existing `created` line and heading.
4. Inspect the diff and confirm it is limited to the intended template expression.

## Verification

Static checks:

```bash
git -C /home/bryan/bob diff --check -- _templates/new_note.md
git -C /home/bryan/bob diff -- _templates/new_note.md
```

Focused expression checks, using a small local JavaScript harness rather than a full Obsidian session:

- With `tp.config.run_mode === 2`, the expression returns `[[org]]`.
- With `tp.config.run_mode === 0` and a valid `active_file.path`, the expression returns `[[<source-path>]]`.
- With `tp.config.run_mode === 0` and no valid active/last-open path, the expression returns `[[org]]`.

Manual/live acceptance after Obsidian or Templater reloads the template:

1. Press `Cmd+N` from an ordinary note.
2. Confirm the new note is populated from `_templates/new_note.md`.
3. Confirm its `parent` is `[[org]]`.
4. Create a missing-link note through the existing Enter/link workflow.
5. Confirm that note still gets `parent` from the source note when Templater exposes the source path.
6. Delete any scratch notes created solely for testing.

## Risks

- `tp.config.run_mode` is inferred from the installed Templater code, not public docs. The numeric values should be
  verified with the local expression harness and, ideally, one live `Cmd+N` smoke test.
- The root folder-template rule applies to all new empty Markdown files under the vault unless overridden by a deeper
  folder rule. The new `run_mode === 2` branch means those notes will also default to `[[org]]`, which is consistent
  with making `[[org]]` the folder-template default but broader than only a physical keyboard shortcut.
- `_templates/new_note.md` is already dirty from prior work. The implementation must avoid normalizing unrelated
  formatting or reverting the existing `created` change.

## Finish Criteria

- This plan is submitted with `sase plan sase_plan_new_note_org_default_parent.md` before implementation edits.
- The implementation diff under `~/bob` is limited to `/home/bryan/bob/_templates/new_note.md`.
- After any vault edit, commit only `_templates/new_note.md` with the required SASE git commit workflow, leaving
  unrelated dirty vault files untouched.
