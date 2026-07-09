---
create_time: 2026-06-19 21:46:40
status: wip
prompt: sdd/prompts/202606/fix_trailing_at_rename_source_marker.md
---
# Fix trailing @ rename source-marker detection

## Context

The `block-id-prompt` Obsidian plugin recently split trailing wikilink markers so:

- `[[...]]^` starts block-link completion.
- `[[...#^old-id]]@` starts block-ID rename.
- inline `#^^old-id` remains the explicit inline rename marker.

The observed failure from `.sase/home/tmp/screenshots/20260619_214116.png` is:

- The trailing `@` does open the Block ID modal.
- Saving from the modal fails with `Block ID rename blocked: source marker link was not found`.

The target file is currently clean in git:

- `/home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js`

The vault has unrelated dirty files, so implementation and commit must stay scoped to the plugin file only.

## Root Cause

`parseTrailingAtBlockRenameMarker()` returns a source marker whose `raw` and `endCh` include the trailing `@`.

During save, `submitLinkedBlockId()` calls `buildReferenceRewritePlan()` with `requireSourceMarker: true`. That planner
reparses candidate files via `collectWikiBlockReferences()`, which uses `parseWikiBlockReference()`.

`parseWikiBlockReference()` only treats a trailing `^` as part of a parsed source marker:

```js
const hasTrailingMarker = lineText[markerCh] === "^" && lineText[markerCh + 1] !== "^";
```

It does not include trailing `@`. Therefore the same line is parsed as `[[...#^old-id]]` instead of `[[...#^old-id]]@`.
The source marker start matches, but the source marker end does not match `source.raw.length`, so `sourceMarkerPlanned`
remains false and save is blocked.

## Technical Plan

1. Update source-marker parsing used during rewrite planning so it recognizes the same trailing marker lifecycle as the
   modal trigger.

2. Replace the hard-coded trailing-`^` check in `parseWikiBlockReference()` with marker-aware logic that accepts a
   single trailing `^` or a single trailing `@`.

3. Preserve existing semantics:
   - `[[...#^old-id]]@` is included as the source marker during rewrite planning, so the source marker can be rewritten
     to `[[...#^new-id]]`.
   - `[[...#^old-id]]` without a trailing marker remains a normal block reference.
   - `[[...#^old-id]]^` remains supported for the older/newly shared marker-reference parsing behavior where needed.
   - doubled markers like `@@` and `^^` stay ignored as trigger markers.
   - plain links such as `[[note]]@` still do not open the rename modal, because the modal trigger remains gated by
     `parseTrailingBlockDestination()`.

4. Keep the change narrowly scoped to parser/rewrite-planner behavior in `main.js`. Do not alter UI text, modal flow,
   destination resolution, duplicate-ID validation, or candidate-file discovery.

## Verification Plan

Run static checks:

- `node -c /home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js`
- `git -C /home/bryan/bob diff --check -- .obsidian/plugins/block-id-prompt/main.js`

Run a focused Node harness with stubbed Obsidian modules to verify parser/rewrite behavior:

- `[[sase_blog#^outline]]@` opens a rename source with `raw` ending in `@`.
- `collectWikiBlockReferences()` includes the trailing `@` in `raw` and `end`.
- `buildReferenceRewritePlan()` accepts the source marker and plans the source edit instead of emitting
  `source marker link was not found`.
- Applying the planned source replacement removes the transient `@` and rewrites to `[[sase_blog#^foobar]]`.
- `[[sase_blog#^outline]]@@` is not treated as a marker source.
- `[[sase_blog#^outline]]^` continues to parse with the trailing `^` where existing behavior expects it.
- `[[sase_blog#^outline]]` without a trailing marker is still collected as a normal block reference.
- `[[sase_blog]]@` still does not trigger a rename prompt.

After implementation, confirm git scope:

- `git -C /home/bryan/bob status --short -- .obsidian/plugins/block-id-prompt/main.js`
- Ensure unrelated vault dirty files are not staged, committed, or modified.

Because the vault `AGENTS.md` requires committing changes under `~/bob`, commit only
`.obsidian/plugins/block-id-prompt/main.js` through the SASE git commit workflow after verification.
