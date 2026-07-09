---
create_time: 2026-06-04 09:43:39
status: done
prompt: sdd/prompts/202606/obsidian_alias_block_completion_cursor.md
---
# Obsidian Alias Block Completion Cursor Plan

## Goal

Make the existing `block-id-prompt` trailing-`^` workflow easier to use after Obsidian auto-converts a selected note
completion from:

```markdown
[[path/to/foobar]]
```

to:

```markdown
[[path/to/foobar|foobar]]
```

When the cursor is after the final `]` and the user types `^`, the plugin should:

1. Delete that typed trailing `^`.
2. Move the cursor inside the wikilink to the column just before the `|`.
3. Leave the link text unchanged as `[[path/to/foobar|foobar]]`.

Then the user can press `^` again at `[[path/to/foobar^|foobar]]` to trigger Obsidian's normal block completion menu for
the target note.

The existing behavior for block-target links must remain unchanged: if the user types `^` after a link that already
targets a block, such as `[[path/to/foobar#^old-id|alias]]^`, the plugin should still delete the marker and open the
block ID prompt used to rename/update that block ID.

## Context Reviewed

- Read project short memory from `memory/short/sase.md`.
- Read Obsidian long memory through:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault and editor workflow context before planning link completion behavior changes"`.
- Read `/home/bryan/bob/AGENTS.md`; vault edits must inspect vault status first, preserve unrelated changes, and commit
  task-related vault files with the SASE git commit workflow if edits are made under `~/bob`.
- Inspected current vault status with `git -C /home/bryan/bob status --short`; it is currently clean.
- Inspected the relevant custom plugins under `/home/bryan/bob/.obsidian/plugins`.
- Identified the target implementation as: `/home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js`
- No `bob-cli` Rust/script/doc change is expected.
- No hotkey JSON change is expected.

Current `block-id-prompt` facts:

- The plugin watches CodeMirror document changes through `EditorView.updateListener`.
- After a debounce, `inspectActiveEditor()` checks the active Markdown editor, current cursor, current line, and code
  fence state.
- `findMarkerLinkNearCursor()` scans wikilinks on the current line.
- Current marker parsing recognizes:
  - inline `#^^old-id` inside a wikilink target;
  - a single trailing `^` immediately after `]]` when the link destination already ends in a block target such as
    `#^old-id` or a supported bare `^old-id`.
- Existing block-marker sources include `raw`, `targetText`, `oldId`, `aliasSuffix`, `blockPrefix`, `startCh`, and
  `endCh`.
- The modal path uses that source to replace the marker link, validate the destination block, rewrite references, and
  rename the target block ID.
- Canceling the modal calls `cancelBlockIdPrompt()`, which rewrites the source link back to the old block ID and deletes
  the extra trailing `^`.

## Product Decisions

1. Implement this in `block-id-prompt`.
   - This plugin already owns the "press `^` after `]]`" behavior.
   - The new behavior is an extra branch in that same trigger, not a navigation hotkey or a CLI feature.

2. Keep block renaming precedence over cursor jumping.
   - If the link destination already parses as a block reference, run the existing prompt path exactly as today.
   - Only use the new jump behavior when the trailing `^` follows an aliased wikilink that is not a block-reference
     marker source.

3. Limit the new behavior to aliased wikilinks.
   - The requested pain comes from Obsidian rewriting note completions to `[[target|alias]]`.
   - The cursor target is "before the `|` character", so links without `|` should be left alone.
   - This avoids surprising rewrites for ordinary text like `[[target]]^`, where there is no alias separator to jump to.

4. Treat the typed trailing `^` as a transient command marker.
   - The final document should not retain the marker.
   - The command should be implemented by deleting only the trailing marker or replacing the marker span with the
     original wikilink text, then setting the cursor to the pipe column.

5. Preserve existing safety checks.
   - Require a single cursor, an active Markdown `TFile`, editor line access, and editor mutation support.
   - Do nothing inside fenced code blocks, matching the current block prompt behavior.
   - Suppress follow-up scans after the plugin deletes the transient marker so it does not react to its own edit.

6. Keep parsing narrow and deterministic.
   - Reuse `splitWikiLinkBody()` so the first `|` continues to define the alias boundary.
   - Reuse existing block-destination parsing for precedence.
   - Compute the cursor column from the parsed wikilink span: `match.index + 2 + destination.length`, which is exactly
     the column before the pipe in `[[destination|alias]]`.

## Implementation Scope

Expected vault file to edit after this plan is accepted:

- `/home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js`

No expected edits to:

- `/home/bryan/bob/.obsidian/plugins/block-id-prompt/manifest.json`
- `/home/bryan/bob/.obsidian/hotkeys.json`
- `/home/bryan/bob/.obsidian/community-plugins.json`
- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/*`
- Any `bob-cli` source, script, README, or test fixture

Likely JavaScript changes:

1. Add a small parser for trailing alias-jump markers, for example `parseTrailingAliasJumpMarker(match, lineText)`.
   - Confirm the character immediately after the matched wikilink is a single `^`.
   - Split the wikilink body into `destination` and `aliasSuffix`.
   - Require `aliasSuffix` to be non-empty so there is a pipe separator to jump to.
   - Require `destination` to be non-empty after trimming.
   - Return `null` if the destination parses as a block reference, so the existing block prompt branch stays in charge.
   - Return an action object with enough information to delete the marker and place the cursor:
     - `kind: "alias-jump"`
     - `raw: raw + "^"`
     - `replacement: raw`
     - `startCh`
     - `endCh`
     - `cursorCh`

2. Update marker lookup to return both existing block-prompt sources and the new alias-jump action.
   - Either extend `parseMarkerLink()` to try `parseInlineMarkerLink()`, `parseTrailingMarkerLink()`, then
     `parseTrailingAliasJumpMarker()`, or add a sibling finder that is called from `inspectActiveEditor()`.
   - Preserve nearest-candidate behavior around the cursor.
   - Preserve the `lineText[markerCh + 1] !== "^"` guard so `^^` keeps its current meaning and accidental double markers
     are not consumed.

3. Split `inspectActiveEditor()` after marker detection by action kind.
   - Keep the current code fence check before either action mutates the editor or opens a modal.
   - For block-prompt sources, keep the current `sourceKey`, `lastPromptKey`, `promptOpen`, and modal behavior.
   - For alias-jump actions:
     - verify the line slice still matches `raw`;
     - call `suppressEditorScans()`;
     - replace the action span with `replacement`, or delete only the trailing marker;
     - set the cursor to `{ line: cursor.line, ch: action.cursorCh }`;
     - clear `lastPromptKey`;
     - do not set `promptOpen`;
     - do not show a notice for the normal successful path.

4. Add tiny editor helpers only if needed for readability.
   - A helper such as `setEditorCursorIfPossible(editor, position)` can handle Obsidian editor APIs defensively.
   - Avoid broad abstractions; this should remain a focused single-plugin behavior.

5. Consider exposing pure parser helpers for focused Node assertions if the implementation needs direct automated
   behavior checks.
   - The plugin currently exports the class directly.
   - If helper exports are added, attach them as properties on the exported class so Obsidian runtime behavior remains
     unchanged.

## Acceptance Criteria

- Starting with:

  ```markdown
  [[path/to/foobar|foobar]]^
  ```

  with the cursor after the trailing `^`, the plugin rewrites the line to:

  ```markdown
  [[path/to/foobar|foobar]]
  ```

  and places the cursor at:

  ```markdown
  [[path/to/foobar|foobar]] ^
  ```

  meaning immediately before `|`.

- Pressing `^` again from that cursor position should leave Obsidian responsible for its normal block completion popup.

- Existing block prompt behavior still works for:

  ```markdown
  [[path/to/foobar#^old-id|foobar]]^
  ```

  and still opens the block ID modal instead of jumping to the alias pipe.

- Canceling or saving the block ID modal continues to delete the transient trailing marker as today.

- `[[path/to/foobar]]^` is not consumed by the new behavior because there is no alias pipe.

- The behavior does not run inside fenced code blocks.

## Verification Plan

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js
jq '.' /home/bryan/bob/.obsidian/plugins/block-id-prompt/manifest.json
git -C /home/bryan/bob diff --check -- .obsidian/plugins/block-id-prompt/main.js
```

Focused parser/editor behavior checks, using a small Node harness with stubbed `obsidian` and `@codemirror/view` modules
if helper exports are added or if the file can be loaded in a VM:

- `[[path/to/foobar|foobar]]^` is recognized as an alias-jump marker.
- The computed cursor column is exactly the pipe index.
- The replacement deletes the trailing `^` and preserves all wikilink text.
- `[[path/to/foobar#^old-id|foobar]]^` is recognized as the existing block-prompt marker, not alias jump.
- `[[path/to/foobar^old-id|foobar]]^` preserves the existing supported bare-block prompt behavior.
- `[[path/to/foobar]]^` is not recognized as alias jump.
- `[[path/to/foobar|foobar]]^^` is not recognized as alias jump.
- Candidate selection still chooses the marker nearest the cursor when a line contains multiple wikilinks.

Manual live-vault acceptance check:

1. Reload Obsidian or the `block-id-prompt` plugin.
2. In a Markdown note, type `[[`, accept a note completion that Obsidian renders as `[[path/to/foobar|foobar]]`.
3. With the cursor after the final `]`, press `^`.
4. Confirm the trailing `^` disappears and the cursor moves before `|`.
5. Press `^` again and confirm Obsidian opens the normal block completion menu for `path/to/foobar`.
6. Select a block completion and confirm the resulting link keeps the alias as expected.
7. On an existing block link such as `[[path/to/foobar#^old-id|foobar]]`, press `^` after `]]` and confirm the block ID
   prompt still opens.
8. Confirm the same text inside a fenced code block is not rewritten.

Before finishing implementation later:

```bash
git -C /home/bryan/bob status --short
git status --short
```

If vault plugin files are changed, commit only the task-related vault file with the required SASE commit workflow,
leaving unrelated vault changes untouched.

## Risks

- The trigger is debounce-based, so a very fast follow-up keystroke could race with the alias jump. This matches the
  existing block prompt design; the implementation should keep the action small and synchronous after detection.
- Obsidian's internal block completion behavior is not controlled by this plugin. The plugin should only place the
  cursor at the right column and let Obsidian handle the second `^`.
- Wikilinks can contain unusual text. The plan intentionally follows the plugin's current simple first-pipe alias
  parsing, which is consistent with existing behavior.
- Automated checks can validate parsing and editor mutation, but the final confirmation of Obsidian's completion popup
  needs a live Obsidian smoke test after plugin reload.
