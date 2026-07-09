---
create_time: 2026-06-19 21:37:31
status: proposed
prompt: sdd/prompts/202606/strip_existing_block_suffix_for_caret_completion.md
---

# Strip Existing Block Suffix Before Caret Completion

## Goal

Update the live Bob vault `block-id-prompt` plugin so the trailing-`^` completion path removes an existing block-id
suffix from the wikilink destination before inserting the new completion caret.

This fixes the current behavior where typing `^` after an existing block link can produce a doubled block target such as
`[[some_file^foobar^]]`. The desired result is that the old `^foobar` portion is removed first, so Obsidian receives a
clean completion trigger like `[[some_file^]]`.

## Context Reviewed

- Used the `sase_plan` skill and will submit this plan with `sase plan propose`.
- Used the `sase_memory_read` skill as required for Obsidian-domain work:
  `sase memory read obsidian.md --reason "Need Obsidian vault workflow before planning changes to the block-id-prompt plugin"`.
- Read `/home/bryan/bob/AGENTS.md`; edits under `~/bob` require checking vault status first, preserving unrelated dirty
  work, and committing task-related vault changes with the SASE git commit workflow before termination.
- Checked `git -C /home/bryan/bob status --short --branch`; the vault currently has unrelated dirty notes/plugins, while
  `.obsidian/plugins/block-id-prompt/main.js` is clean at the time of planning.
- Read the previously approved plan at `sdd/tales/202606/split_wiki_link_markers.md`.
- Inspected `/home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js`, especially:
  - `parseTrailingCaretCompletionMarker()`
  - `parseTrailingBlockDestination()`
  - `dispatchFileLinkBlockCompletion()`
  - `applyFileLinkBlockCompletionWithEditorApi()`
  - `applyFileLinkJumpMarker()`

## Current Implementation Facts

- `parseTrailingCaretCompletionMarker()` handles the trailing-`^` behavior and currently derives all output from the
  original destination text before any alias suffix.
- It sets:
  - `plainReplacement: [[${destination}]]`
  - `completionReplacement: [[${destination}^]]`
  - `insertionCh: match.index + 2 + destination.length`
  - `finalCursorCh: insertionCh + 1`
- That is correct for plain links and aliased links, but wrong for existing block links because the old `^id` suffix is
  treated as part of the base destination.
- `parseTrailingBlockDestination(destination)` already recognizes existing block destinations in both forms:
  - `target#^old-id`
  - `target^old-id`
- The caret path is correctly ordered before the trailing-`@` rename path and inline rename path; that ordering should
  remain unchanged.

## Product Decisions

1. Keep this as a narrow parser/replacement change in `block-id-prompt/main.js`.

2. Strip only a recognized existing block-id suffix from the caret completion base.
   - Reuse the plugin's existing block-id parsing rules (`BLOCK_ID_RE` through `parseTrailingBlockDestination()`).
   - This avoids deleting arbitrary caret-containing destination text that is not already treated by the plugin as a
     block reference.

3. Preserve the link form's separator when appropriate.
   - `[[some_file^foobar]]^` should become `[[some_file^]]`.
   - `[[some_file#^foobar]]^` should become `[[some_file#^]]`.
   - For a hash block suffix, remove the old `^foobar` but keep the preceding `#`, because the user was already in the
     `#^` block-link form.

4. Continue removing aliases on the caret completion path.
   - Alias removal was part of the previous approved behavior and should still happen after the base destination is
     stripped.

5. Do not change trailing-`@` rename behavior.
   - `@` remains the block-ID rename trigger for links that already target a block ID.
   - A trailing `^` after an existing block link must continue to avoid opening the rename modal.

## Proposed Technical Design

1. Add a small helper near the trailing marker parsers, for example `getCaretCompletionDestination(destination)`.

2. In that helper:
   - Call `parseTrailingBlockDestination(destination)`.
   - If it returns `null`, return the original `destination`.
   - If it returns `blockPrefix: "^"`, return `parsed.targetText`.
   - If it returns `blockPrefix: "#^"`, return `${parsed.targetText}#`.
   - This makes the later caret insertion produce either `target^` or `target#^` without preserving the old ID text.

3. Update `parseTrailingCaretCompletionMarker()` to compute:
   - `const completionDestination = getCaretCompletionDestination(destination);`
   - `const insertionCh = match.index + 2 + completionDestination.length;`
   - `plainReplacement: [[${completionDestination}]]`
   - `completionReplacement: [[${completionDestination}^]]`
   - `finalCursorCh: insertionCh + 1`

4. Keep `raw`, `startCh`, and `endCh` based on the original matched link plus transient trailing `^`.
   - This preserves the stale-line guard in `applyFileLinkJumpMarker()`.
   - It also ensures the old block suffix and any alias are removed by replacing the full original marker range.

5. Leave the editor action paths unchanged.
   - CodeMirror dispatch should continue to send one `input.type` transaction with `marker.completionReplacement`.
   - The editor API fallback should continue to replace with `marker.plainReplacement`, place the cursor at
     `marker.insertionCh`, insert `^`, and leave the cursor at `marker.finalCursorCh`.

6. Preserve dirty-work discipline.
   - Re-check `git -C /home/bryan/bob status --short --branch` immediately before implementation.
   - Patch only `/home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js`.
   - Do not touch or revert unrelated dirty vault files.
   - After implementation and verification, commit the task-related vault change with the SASE git commit workflow.

## Acceptance Criteria

- `[[some_file]]^` becomes `[[some_file^]]`, with the cursor after the inserted `^`.
- `[[some_file|alias]]^` becomes `[[some_file^]]`, with the alias removed and cursor after the inserted `^`.
- `[[some_file^foobar]]^` becomes `[[some_file^]]`, with `^foobar` removed before the new caret is inserted.
- `[[some_file^foobar|alias]]^` becomes `[[some_file^]]`, with both the existing block suffix and alias removed.
- `[[some_file#^foobar]]^` becomes `[[some_file#^]]`, with `^foobar` removed before the new caret is inserted.
- `[[some_file#^foobar|alias]]^` becomes `[[some_file#^]]`, with no rename modal.
- `[[some_file#^foobar|alias]]@` still opens the existing rename modal for `foobar`.
- `[[some_file]]@` is still not consumed.
- Double-marker guards still hold: `[[some_file]]^^` and `[[some_file#^foobar]]@@` are ignored.
- The behavior still does nothing inside fenced code blocks and with multiple cursors.

## Verification Plan

Static checks:

```bash
node -c /home/bryan/bob/.obsidian/plugins/block-id-prompt/main.js
jq '.' /home/bryan/bob/.obsidian/plugins/block-id-prompt/manifest.json
git -C /home/bryan/bob diff --check -- .obsidian/plugins/block-id-prompt/main.js
```

Focused Node behavior harness with stubbed `obsidian` and `@codemirror/view` modules:

- Assert `[[some_file]]^` produces `[[some_file^]]`.
- Assert `[[some_file|alias]]^` produces `[[some_file^]]`.
- Assert `[[some_file^foobar]]^` produces `[[some_file^]]`.
- Assert `[[some_file^foobar|alias]]^` produces `[[some_file^]]`.
- Assert `[[some_file#^foobar]]^` produces `[[some_file#^]]`.
- Assert `[[some_file#^foobar|alias]]^` produces `[[some_file#^]]` and captures no modal source.
- Assert `[[some_file#^foobar|alias]]@` still captures a rename modal source with `oldId: "foobar"`,
  `blockPrefix: "#^"`, and `aliasSuffix: "|alias"`.
- Assert `[[some_file]]@`, `[[some_file]]^^`, and `[[some_file#^foobar]]@@` are ignored.

Manual live-vault checks after plugin reload:

1. Type `^` after a plain wikilink and confirm the block completion menu opens inside the link.
2. Type `^` after an aliased wikilink and confirm the alias is removed before completion opens.
3. Type `^` after a bare existing block wikilink and confirm the old block ID is removed before completion opens.
4. Type `^` after a `#^` existing block wikilink and confirm the old block ID is removed before completion opens.
5. Type `@` after an existing block wikilink and confirm the rename modal behavior is unchanged.
