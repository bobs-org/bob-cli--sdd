---
create_time: 2026-06-12 15:43:29
status: wip
prompt: sdd/prompts/202606/non_transcluded_block_link_priority.md
---
# Plan: Prioritize Current-Line Obsidian Block Links for Ctrl+6

## Goal

Extend the `block-id-prompt` plugin's `Ctrl+6` command so that any supported Obsidian block link on the active line can
be renamed directly, even when it is not transcluded. For example, with the cursor on a line containing
`[[foobar^baz]]`, the modal should target the `baz` block in `foobar` instead of adding or renaming a block ID on the
local Markdown block that contains the link.

The priority order should become:

1. Supported block wikilink on the current line, transcluded or not.
2. Local selected/current Markdown block add or rename.

Existing typed-marker behavior should remain unchanged.

## Context Reviewed

- Project instructions: `AGENTS.md`.
- Short memory: `memory/short/sase.md`.
- Obsidian long memory through:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault/plugin workflow before planning block link rename behavior"`.
- Approved prior plan: `sdd/tales/202606/ctrl6_block_id_keymap.md`.
- Live plugin source: `/home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js`.

No `bob-cli` CLI subcommand or option is involved, so `memory/long/cli_rules.md` is not required.

## Current Implementation Facts

- The relevant implementation is the live Obsidian vault plugin:
  `/home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js`.
- `Ctrl+6` is registered as `rename-selected-block-id` and calls `openSelectedBlockIdPrompt(editor, view)`.
- `openSelectedBlockIdPrompt()` currently checks the active line for `findTranscludedBlockReferenceOnLine()` before
  falling back to `discoverSelectedBlockIdSource()`.
- `findTranscludedBlockReferenceOnLine()` only accepts wikilinks with a leading `!`, but it already creates a source
  object compatible with the linked-block rename path.
- The command source kind `link-block` is cancel-safe because there is no typed marker to restore.
- `parseBlockReferenceDestination(destination, { allowPathBareBlock: true })` can parse examples like `foobar^baz`,
  `foobar#^baz`, and `#^baz`.
- `collectWikiBlockReferences()` currently uses `parseWikiBlockReference()`, whose bare `path^id` support is limited to
  typed trailing-marker cases. As a result, a plain `[[foobar^baz]]` source would not be found by the reference rewrite
  planner unless reference collection is also updated.

## Product Decisions

1. **Treat current-line block wikilinks as command targets, not typed markers.**
   - The new behavior belongs only to the explicit `Ctrl+6` command path.
   - The existing CodeMirror scan for typed `^` markers should keep its current grammar and timing.

2. **Support both embedded and plain wikilinks with one resolver.**
   - Replace or generalize `findTranscludedBlockReferenceOnLine()` into a current-line block-link finder.
   - Accept:
     - `[[foobar^baz]]`
     - `[[foobar#^baz]]`
     - `[[foobar.md#^baz|Alias]]`
     - `[[folder/foobar^baz]]`
     - `[[#^baz]]`
     - the same forms with a leading `!`
   - Preserve the existing behavior that replacement spans only `[[...]]`, so `![[...]]` remains transcluded after
     rename.

3. **Use deterministic candidate selection.**
   - Prefer a block link that contains the cursor.
   - If none contains the cursor, choose the nearest supported block link on the active line by cursor distance.
   - If there is still a tie, choose the earliest link on the line. This avoids a surprise fallback to the local block.

4. **Broaden wiki block-reference collection enough for correctness.**
   - The reference rewrite plan must recognize plain bare `path^id` wiki block links, not just `path#^id`.
   - Without this, the initiating `[[foobar^baz]]` source would fail the existing "source marker link was not found"
     check and other equivalent references would not be updated.
   - Markdown links can remain unchanged; this request is specifically about Obsidian wikilinks.

5. **Keep local block add/rename behavior intact.**
   - Only fall back to `discoverSelectedBlockIdSource()` when no supported block wikilink exists on the active line.
   - Existing notices for no selected block, multiple local IDs, stale content, duplicates, and fenced code should
     remain unchanged unless a new link-specific stale-source notice is needed.

## Implementation Plan

1. **Generalize the active-line block-link finder.**
   - Rename `findTranscludedBlockReferenceOnLine()` to something like `findBlockReferenceOnLine()`.
   - Iterate with the existing `WIKI_LINK_RE`.
   - Detect whether each match has a leading `!`, but do not require it.
   - Parse the destination with `parseBlockReferenceDestination(destination, { allowPathBareBlock: true })`.
   - Return a `link-block` source with `raw`, `targetText`, `oldId`, `aliasSuffix`, `blockPrefix`, `startCh`, `endCh`,
     `prefillId: true`, and ranking metadata.
   - Keep `startCh` at `match.index` and `endCh` at `match.index + raw.length` so replacement excludes the leading `!`.

2. **Update command priority in `openSelectedBlockIdPrompt()`.**
   - Replace the transcluded-only call with the generalized finder.
   - Open the returned `link-block` source before calling `discoverSelectedBlockIdSource()`.
   - Continue returning early inside fenced code blocks.

3. **Teach wiki reference collection about plain `path^id` references.**
   - Adjust `parseWikiBlockReference()` or add an option so `collectWikiBlockReferences()` recognizes bare path block
     destinations such as `foobar^baz`.
   - Preserve support for existing forms:
     - `#^^` inline marker workflow;
     - `#^` standard block references;
     - trailing typed marker cases;
     - aliases.
   - Keep replacement based on the `[[...]]` span so embedded links preserve the leading `!`.

4. **Preserve source-marker validation for command link sources.**
   - After collection is broadened, `buildReferenceRewritePlan()` should be able to find a `[[foobar^baz]]` initiating
     source without special casing.
   - Keep `requireSourceMarker` behavior unchanged for linked sources; direct local renames should continue to pass
     `{ requireSourceMarker: false }`.

5. **Review ambiguity and stale-source behavior.**
   - Confirm `sourceKey()` is still stable for plain current-line links.
   - Confirm `cancelBlockIdPrompt()` treats `link-block` as no-op, since no typed marker needs restoration.
   - Confirm `sourceMarkerStillPresent()` works for both plain and embedded links by checking only the `[[...]]` span.

## Acceptance Criteria

- Pressing `Ctrl+6` on a line containing `[[foobar^baz]]` opens the modal prefilled with `baz` and targets `foobar`, not
  the local line's Markdown block.
- Saving `qux` from that modal rewrites the source link to `[[foobar^qux]]` and renames the target block token from
  `^baz` to `^qux`.
- Pressing `Ctrl+6` on `[[foobar#^baz]]` behaves the same way, preserving the `#^` style in that link.
- Pressing `Ctrl+6` on `![[foobar^baz]]` continues to target the transcluded block and preserves the leading `!`.
- When multiple block wikilinks are on the same line, the cursor-contained link wins; otherwise the nearest link wins.
- When no supported block wikilink is on the line, existing local selected/current block add and rename behavior is
  unchanged.
- Existing typed `^` marker flows still work, including file-link cursor jump, block-link rename, cancel restoration,
  and transclusion preservation.
- Behavior remains blocked inside fenced code blocks.

## Verification Plan

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js
jq '.' /home/bryan/bob/.obsidian/plugins/block-id-prompt/manifest.json
git -C /home/bryan/bob diff --check -- .obsidian/plugins/block-id-prompt/main.js
git -C /home/bryan/bob status --short
git status --short
```

Focused Node VM checks with Obsidian APIs stubbed:

- Current-line finder accepts `[[foobar^baz]]`, `[[foobar#^baz]]`, `[[foobar.md#^baz|Alias]]`, `[[folder/foobar^baz]]`,
  `[[#^baz]]`, and the corresponding `![[...]]` forms.
- Current-line finder ignores non-block wikilinks, malformed IDs, and Markdown links.
- Candidate ranking prefers cursor-contained links, then nearest links, then earliest links.
- `collectWikiBlockReferences()` includes plain `path^id` wiki block references and still includes existing `#^` and
  marker forms.
- Source replacement preserves the original block prefix for `^` versus `#^` links and preserves aliases.
- `buildReferenceRewritePlan()` finds the initiating plain `[[foobar^baz]]` source marker and does not trigger "source
  marker link was not found".
- Existing direct local add/rename and typed-marker parser assertions from the previous change still pass.

Manual smoke checks after implementation and plugin reload:

1. In a scratch note, place the cursor on a line containing `[[target-note^old-id]]`, press `Ctrl+6`, rename to
   `new-id`, and confirm the target note's block token and source link update.
2. Repeat with `[[target-note#^old-id]]`.
3. Repeat with `![[target-note^old-id]]` and confirm the leading `!` remains.
4. Put two block links on one line and verify cursor placement selects the expected one.
5. Put a non-block wikilink on a line with no block link and confirm `Ctrl+6` still falls back to local block
   add/rename.
6. Confirm the existing typed `^` workflows still behave as before.

## Risks and Mitigations

- **Bare `path^id` parsing could theoretically conflict with unusual filenames containing `^`.** Limit the broadening to
  wikilink block-reference parsing and keep destination-file resolution plus old-ID validation before any writes.
- **Current-line link selection may surprise when the cursor is far from a link on the same line.** This is intentional
  for this request: a supported block link on the active line has priority over the local Markdown block.
- **Reference rewrite behavior is sensitive to parser changes.** Keep changes focused on wikilinks, preserve existing
  parser helpers, and cover old and new syntaxes in focused VM tests.

## Expected Files To Edit After Approval

- `/home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js`

No expected edits to `manifest.json`, `.obsidian/hotkeys.json`, `bob-cli` source files, or existing memory files.
