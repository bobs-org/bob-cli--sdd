---
create_time: 2026-06-12 10:25:26
status: done
prompt: sdd/prompts/202606/obsidian_project_from_task_block_id.md
---
# Obsidian Project-From-Task: Block-ID-Derived Filename + Block-Link Rewriting

## Goal

Extend the `create-project-note-from-task` command (`<Ctrl+Alt+Shift+N>`, shipped in
`sdd/tales/202606/obsidian_project_from_task_keymap.md`, vault commit `1ed66b7`) so that when the source task carries a
trailing block ID, the feature **converts** the anchor instead of aborting or silently dropping it:

1. The new project note is **auto-named** by merging the source note's basename with the block ID, dashes→underscores:
   task `^foo-bar-baz` in `~/bob/fake_project.md` → project note `~/bob/fake_project_foo_bar_baz.md`. (The block ID
   itself is still never copied onto the new `^prj` line — that would put two block IDs on one task.)
2. Every Obsidian block link that targeted the task via that block ID (e.g. `[[fake_project#^foo-bar-baz]]`,
   `[[fake_project#^foo-bar-baz|alias]]`) is rewritten to point at the new note: `[[fake_project_foo_bar_baz]]` (alias
   preserved: `[[fake_project_foo_bar_baz|alias]]`).

This **replaces** the current "block ^id is linked from another note; remove that link first" abort: referenced anchors
are now migrated, not blocked on. Tasks without a block ID keep today's behavior exactly (untitled note, rename mode).

## Context Reviewed

- Workspace short memory: `memory/short/sase.md`. `memory/long/cli_rules.md` is **not** required: no bob-cli
  subcommands/options change (all work lives in the vault). If implementation deviates into the CLI surface, the agent
  MUST first run `/sase_memory_read` on `memory/long/cli_rules.md`.
- Vault instructions: `/home/bryan/bob/AGENTS.md` — vault is live under Obsidian Sync and dirty with the same
  pre-existing unrelated files as the prior task (`_templates/daily.md`, `_templates/new_project.md`, `bob_projects.md`,
  `dash.md`, `gtd_daily.md`, `mac_inbox.md`, `sase.md`, today's daily, two ref-chat notes). Re-check `git status` before
  editing; stage/commit only task files via `/sase_git_commit`.
- Live plugin: `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js` (~4700 lines after `1ed66b7`).
  Relevant code: `createProjectNoteFromTask()` (main.js:3671), shared `createProjectNoteFile()` (main.js:3798, currently
  passes `undefined` as the Templater filename → "Untitled"), abort guard `isProjectTaskBlockIdReferenced()`
  (main.js:3853) + `backlinkValueReferencesBlockId()` / `backlinkTextReferencesBlockId()` (main.js:983–1024), pure
  helpers exported via `module.exports.helpers`.
- Block ID grammar: `PROJECT_BLOCK_ID_RE = /^[A-Za-z0-9-]+$/` (main.js:31) — dash→underscore mapping plus the source
  basename yields a filesystem-safe filename with no further sanitization needed.
- Templater internals (installed `templater-obsidian/main.js`, verified in minified source):
  `create_new_note_from_template(template, folder, filename, open)` runs the target path through
  `vault.getAvailablePath(normalizePath(folder + "/" + (filename || "Untitled")), "md")` — an existing
  `fake_project_foo_bar_baz.md` would be **silently deduped** to `fake_project_foo_bar_baz 1.md`. Collisions must
  therefore be detected up front (abort) and the actual `createdFile.basename` used when building replacement links.
  Rename-mode/current-tab opening is unchanged and inherited.
- Real link shapes in the vault: `grep -rno '!?\[\[[^]]*#\^[^]]*\]\]'` shows wikilinks with aliases dominate (e.g.
  `[[goog#^z-241024-0l|youtube]]`, `[[prj_mcr_cats#^z-250425-0m|mcr_cats]]`, incl. same-file self-links). No `![[…#^…]]`
  embeds and no markdown-style `[txt](note.md#^id)` block links exist today.
- Design Contract (from `sase_plan_obsidian_projects.md`): `^anchors` referenced from daily Pomodoro logs must never be
  broken. Rewriting every referencing link before deleting the anchor upholds the contract while removing the
  manual-cleanup friction of the abort.

## Current Findings

- `metadataCache.getBacklinksForFile(file)` returns `{ data }` where `data` is a `Map` (newer API) or plain object keyed
  by referencing-file path; each value is an array of link caches carrying `link` (target incl. `#^id` subpath) and
  `original` (exact source text of the link, e.g. `[[fake_project#^foo-bar-baz|alias]]`). Every entry already resolves
  to the queried file, so no extra link-target resolution is needed — filter by subpath `#^id` and rewrite each cache's
  `original`.
- The current flow ordering is: validate/capture → `view.save()` → create note → seed `^prj` from placeholder → delete
  source task line → toast. Each failure degrades safely (nothing deleted unless the text landed in the new note).

## Design

### UX flow (task **with** block ID `^foo-bar-baz` in `fake_project.md`)

1. `<Ctrl+Alt+Shift+N>` validates the task line as today (open `#task` checkbox in an area/project note, no child
   bullets, non-empty description). The referenced-block-ID abort is **removed**.
2. The project note is created from `_templates/new_project.md` **named** `fake_project_foo_bar_baz` in the vault root
   (current tab; Obsidian still enters title-rename mode with the derived name pre-filled — harmless: if Bryan renames,
   Obsidian auto-updates the just-rewritten links). Frontmatter enforcement (`parent`/`type`/`status`) is unchanged.
3. `^prj` line seeded from the task exactly as today (block ID still dropped, `[p::N]` carried over).
4. All block links targeting `fake_project#^foo-bar-baz` (from any note, including `fake_project.md` itself) are
   rewritten to `[[fake_project_foo_bar_baz]]`, preserving `|alias` display text and a leading `!` if an embed ever
   appears.
5. The original task line is deleted from `fake_project.md` (only after every link rewrite succeeded).
6. Toast summarizes: created note name, task removal, and link-update count, e.g.
   `Created project fake_project_foo_bar_baz from task "Buy a new mattress…" (task removed from fake_project; 2 links updated)`.

Task **without** a block ID: behavior is byte-for-byte today's (untitled note, no rewriting, existing toast).

### Derived name + collision validation (before anything is created)

- `getProjectBasenameFromTaskBlockId(sourceBasename, blockId)` → `<sourceBasename>_<blockId with "-" → "_">`; returns
  `null` for an empty/invalid input (defensive — `PROJECT_BLOCK_ID_RE` already constrains the charset).
- Collision check: prefer `metadataCache.getFirstLinkpathDest(newBasename, sourceFile.path)` (guarded for existence) so
  a same-basename note **anywhere** in the vault is caught (it would make the rewritten short link ambiguous/wrong);
  fall back to `vault.getAbstractFileByPath(newBasename + ".md")`. On hit → abort with toast
  `Note "fake_project_foo_bar_baz" already exists; rename it first` — nothing created or modified. This also prevents
  Templater's silent `… 1.md` dedup.
- Belt-and-braces: after creation, replacement link text is built from the **actual** `createdFile.basename`, so even a
  raced dedup can't write links that point at the wrong note.

### Collecting and rewriting block links

- New pure helper `collectBlockIdBacklinkRewrites(backlinksData, blockId)` → array of `{path, originals: [string]}`:
  walks the `Map`/plain-object `data` shape (same tolerance as the existing `backlinkValueReferencesBlockId`), keeps
  link caches whose subpath is exactly `#^<blockId>` (reusing the `backlinkTextReferencesBlockId` boundary regex so
  `^foo-bar-baz2` never matches), dedupes identical `original` strings per file.
- New pure helper `rewriteBlockIdLinkOriginal(original, newBasename)` → rewritten link or `null` if the shape is
  unrecognized. Handles `[[target#^id]]`, `[[target#^id|alias]]`, `[[#^id]]` (same-file), each with optional leading
  `!`, and best-effort markdown links `[text](target.md#^id)` → `[text](new_basename.md)`. Per the user's spec the
  rewritten wikilink targets the whole note (`[[fake_project_foo_bar_baz]]`), not `#^prj`.
- New pure helper `replaceLinkOriginalsInContent(content, replacements)` → `{content, missing}` replacing **all**
  occurrences of each `original` (split/join — identical originals in one file resolve identically, so this is safe) and
  reporting originals that were not found (file changed since the cache snapshot).
- Command side: one `vault.process(referencingFile, …)` per referencing file. Any unrecognized original
  (`rewriteBlockIdLinkOriginal` → `null`), missing file, missing original, or process error marks the rewrite pass
  failed.
- If `getBacklinksForFile` is unavailable (mocked/edge environments): proceed with auto-naming, skip rewriting — same
  trust level as the current guard's unavailable-API path.

### Order of operations & failure semantics

1. Validate + capture task line (existing). Parse yields `blockId`.
2. **If blockId**: derive name; collision check (abort-toast on hit); snapshot backlink rewrites from the metadata
   cache.
3. `await view.save()` (existing).
4. Create note via shared helper, now `createProjectNoteFile(creatingFile, basename?)` — `createProjectNote()` keeps
   passing no basename and is behavior-unchanged.
5. Seed placeholder (existing). If the placeholder is missing → existing warning toast, **stop**: no links rewritten,
   source task kept — fully consistent state.
6. **If blockId**: rewrite links file-by-file. If any rewrite fails → toast
   `Created project, but N block links could not be updated; source task was kept` and **skip deletion** — the anchor
   stays so every non-rewritten link keeps resolving (Design Contract). Already-rewritten links point at the new note,
   which now contains the task text — nothing broken, manual cleanup possible.
7. Delete the source task line (existing exact-match logic) only after step 6 fully succeeded.
8. Success toast via extended notice helper (created name when auto-named + `; N link(s) updated` when N > 0).

Rewrites run **before** deletion so there is never a window where a link points at a deleted anchor.

### Dead code

The abort path (`isProjectTaskBlockIdReferenced`, `backlinkValueReferencesBlockId`) is removed/absorbed by the
collector; `backlinkTextReferencesBlockId` is kept (reused for subpath matching). `module.exports.helpers` is updated
accordingly.

## Implementation Steps

1. **`/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`** (only file changing; no manifest,
   hotkeys.json, template, or vimrc changes — the keybinding and template contract are untouched):
   - Add pure helpers near the existing project-task helpers and export them: `getProjectBasenameFromTaskBlockId`,
     `collectBlockIdBacklinkRewrites`, `rewriteBlockIdLinkOriginal`, `replaceLinkOriginalsInContent`; extend
     `getProjectFromTaskNoticeText` (created-name + link-count aware, existing signature behavior preserved when the new
     args are absent).
   - `createProjectNoteFile(creatingFile, basename)`: optional basename forwarded to Templater (replaces the hardcoded
     `undefined`).
   - `createProjectNoteFromTask()`: drop the referenced-block-ID abort; add derive-name + collision check +
     rewrite-snapshot (step 2), pass the derived basename at creation, insert the rewrite pass between seeding and
     deletion with the failure semantics above, extend the final toast.
   - Private helpers as needed for the command-side rewrite loop (e.g. `applyBlockIdLinkRewrites(rewrites)` returning
     `{updatedLinkCount, failed}`), keeping `vault.process` usage consistent with the existing calls.
2. No other files change.

## Validation

1. Static: `node --check …/bob-navigation-hotkeys/main.js`.
2. Node smoke tests (established mocked-`obsidian` pattern):
   - Helpers: basename derivation (`fake_project` + `foo-bar-baz` → `fake_project_foo_bar_baz`; single-word ID; ID
     needing no mapping); rewrite of plain/aliased/same-file/embedded wikilinks and markdown links; unrecognized shape →
     `null`; collector over `Map` and plain-object backlink data incl. other-block links ignored, boundary-safe ID
     matching, per-file dedup; content replacement incl. multiple occurrences and missing originals; notice text with
     and without link count/created name.
   - Command flow: blockId + 2 referencing files → note created with derived name, both files rewritten, task deleted,
     toast counts 2; blockId + name collision → abort, vault untouched; blockId + zero references → named note, no
     rewrite calls, task deleted; blockId + one rewrite failure → task NOT deleted, warning toast; placeholder missing
     with blockId → no rewrites attempted; **regression**: no-blockId task → Templater called with no filename and flow
     identical to `1ed66b7`; `create-project-note` (`<Ctrl+Shift+N>`) untouched.
3. Manual acceptance (Bryan, after Obsidian reload):
   - Task `… ^foo-bar-baz` in `fake_project.md` referenced from a daily note: hotkey creates
     `fake_project_foo_bar_baz.md` (current tab, rename mode shows derived name), `^prj` line carries the task text,
     daily-note link now reads `[[fake_project_foo_bar_baz|alias]]`, original task gone, toast reads well.
   - Same but with an existing `fake_project_foo_bar_baz.md`: abort toast, nothing changed.
   - Task with block ID but no references: named note created, task removed.
   - Task without block ID: untitled-note behavior identical to before.

## Risks / Notes

- **Vault is live and dirty** (Obsidian Sync): re-check `git -C ~/bob status --short` immediately before editing; never
  touch the unrelated dirty files.
- **Behavior change is intentional**: the conservative referenced-anchor abort is replaced by migration. The Design
  Contract ("never break anchors") is preserved by rewriting before deleting and by keeping the task when any rewrite
  fails.
- **Link semantics change for readers**: rewritten links target the whole project note rather than a specific block (per
  spec). Old Pomodoro-log links become project links — historically accurate enough since the task now IS the project's
  completion criteria.
- **Metadata cache staleness**: rewrites snapshot the cache before any mutation; per-original exact-string replacement
  plus the missing-original failure path means a stale snapshot degrades to "task kept + warning", never to corrupted
  content.
- **Rename-mode interplay**: if Bryan renames the auto-named note while in rename mode, Obsidian's own link-updating
  takes over for the just-written `[[fake_project_foo_bar_baz]]` links — no special handling needed.

## Commit Workflow

Per `/home/bryan/bob/AGENTS.md`: stage **only** `.obsidian/plugins/bob-navigation-hotkeys/main.js` and commit via the
`/sase_git_commit` skill before terminating.
