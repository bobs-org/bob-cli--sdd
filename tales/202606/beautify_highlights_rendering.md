---
create_time: 2026-06-10 14:02:59
status: done
prompt: sdd/prompts/202606/beautify_highlights_rendering.md
---
# Beautify PDF Highlight Rendering in Reference Notes

## Problem

The `## Highlights` section that `bob highlights sync` generates inside reference notes can look cramped and ragged,
with strange word splitting. Two distinct problems compound:

1. **Hard-wrapped, hyphen-split text.** The Highlights app exports quote text with the PDF's physical line breaks (and
   end-of-line hyphenation) intact, and the renderer reproduces them verbatim:

   ```md
   > It only writes the PDF marker when frontmatter is the selected source and --write-pdf is supplied. Confusing
   > latency and through- put leads to mis-sized capacity plans.
   ```

   In Obsidian's reading view each `>` line renders as its own line, so highlights show up as ragged columns of short
   lines with words like "through-put" split mid-word. PDF text extraction also leaks typographic artifacts into the
   text: ligature glyphs (`ﬁ`, `ﬂ`, `ﬀ`…), non-breaking spaces, soft hyphens, and doubled spaces.

2. **Visually flat markup.** Every annotation is a bare blockquote, with comments and notes distinguished only by inline
   `[comment]` / `[note]` text tags. Nothing visually separates the quoted source text from Bryan's own thoughts, and a
   page full of undifferentiated `>` walls is hard to scan.

## Root Cause

In `src/native/highlights_ref/mod.rs`:

- `normalize_annotation_text` (~line 2613) only trims structural whitespace; it joins the sidecar's physical lines with
  `\n`, preserving every hard wrap and hyphen split.
- `push_blockquote` (~line 2377) emits each preserved line as its own `> ` line.
- `render_annotation_block` (~line 2351) has exactly one visual vocabulary: a plain blockquote plus an inline
  `[comment]`/`[note]`/`[removed]` text tag.

There is no semantic text cleanup anywhere in the pipeline (no line reflow, no de-hyphenation, no ligature/space
normalization).

## Design

Two layers, both applied **at render time only**. The block-ID hash (`annotation_block_id`) and annotation-task intake
keep consuming the raw sidecar text, so existing `^h-...` block IDs, task backlinks (`[[#^h-...|🔖]]`), and `[h:: ...]`
processed IDs all stay stable. Re-syncing an existing note rewrites only the managed region's appearance — no
`### Removed highlights` churn.

### Layer 1: text beautification (the readability fix)

A `beautify_annotation_text` pass applied to highlight text, comments, and standalone notes before rendering:

1. **Reflow paragraphs.** Join consecutive prose lines into one flowing line with single spaces. Blank lines remain
   paragraph breaks. A line starting with a Markdown list marker (`- `, `* `, `+ `, including `- [ ]` checkboxes) always
   starts its own logical line, so task bullets and comment lists keep their structure; wrapped continuation prose joins
   into the line above it.
2. **De-hyphenate at join points.** When a joined line ends with `-` (or `‐` U+2010) preceded by a letter:
   - next fragment starts lowercase → drop the hyphen, join with no space (`through-` + `put` → `throughput`);
   - next fragment starts uppercase/digit → keep the hyphen, join with no space (`Marie-` + `Curie` → `Marie-Curie`). A
     trailing soft hyphen (U+00AD) is always dropped. This matches the heuristic used by mainstream PDF text tools; the
     rare false positive (`well-\nknown` → `wellknown`) is far less common than true hyphenation splits and is the
     accepted trade-off.
3. **Clean extraction artifacts.** Expand ligature glyphs (`ﬁ ﬂ ﬀ ﬃ ﬄ ﬅ ﬆ` → `fi fl ff ffi ffl ft st`), convert
   non-breaking/figure spaces to regular spaces, strip soft hyphens, zero-width spaces, and BOMs everywhere, collapse
   runs of spaces/tabs, and trim trailing whitespace.

### Layer 2: visual redesign with Obsidian callouts (the beauty fix)

The vault is Obsidian, so use its native callout vocabulary — colored, icon-labeled cards instead of bare `>` walls. All
callout types used (`quote`, `note`, `warning`) are Obsidian built-ins; in non-Obsidian renderers they degrade
gracefully to plain blockquotes.

- **Highlight** → a `[!quote]` callout. **Comment** → a `[!note] Comment` callout _nested inside_ the quote callout, so
  the highlight and Bryan's reaction read as one visual unit — and, critically, the trailing `^h-...` block ID still
  covers both (a sibling callout would steal the block reference).
- **Standalone note** → a `[!note]` callout.
- **Removed annotation placeholder** → a `[!warning] Removed highlight` callout.
- Everything structural is unchanged: `### Page N` headings, blank-line spacing, `^h-...` placement on its own line
  after the block, and the `<!-- highlights:begin/end -->` managed markers.

### Before / after

Before:

```md
### Page 2

> Confusing latency and through- put leads to mis-sized capa- city plans.
>
> [comment] Compare this with SLO notes.

^h-2b91f0a4c7de
```

After:

```md
### Page 2

> [!quote] Confusing latency and throughput leads to mis-sized capacity plans.
>
> > [!note] Comment Compare this with SLO notes.

^h-2b91f0a4c7de
```

## Implementation Plan

1. Add text-beautification helpers near `normalize_annotation_text` in `src/native/highlights_ref/mod.rs`.
   - `clean_pdf_text_artifacts`: ligature expansion, exotic-space normalization, soft-hyphen/zero-width stripping,
     space-run collapsing.
   - `beautify_annotation_text`: list-aware paragraph reflow with the de-hyphenation join rules above, calling the
     artifact cleaner.
   - Unit-test each rule directly: prose reflow, paragraph-break preservation, list-marker line starts, lowercase vs.
     uppercase hyphen joins, soft hyphens, ligatures, space collapsing.

2. Rework rendering in `render_annotation_block` and `push_blockquote`.
   - Beautify highlight text, comment text, and standalone-note text at render time only.
   - Emit the callout structure: `[!quote]` for highlights, nested `[!note] Comment` for comments, `[!note]` for
     standalone notes. Extend `push_blockquote` (or replace it with a callout-aware helper) to support a nesting depth
     and a callout header line.
   - Update the removed-annotation placeholder in `render_sidecar_highlights` to the `[!warning] Removed highlight`
     callout.
   - Do **not** touch `annotation_block_id`, `normalized_identity_text`, marker-mirror detection, or annotation-task
     candidate extraction — those keep reading raw sidecar text.

3. Update existing tests that assert the old rendered shape.
   - Unit tests in `src/native/highlights_ref/mod.rs` (e.g.
     `rendered_annotation_blocks_do_not_include_source_task_anchors` and the note-update tests around lines 6308–6520) —
     preserve their invariants (no `^ht-` anchors in the region, task bullets mirrored as list lines) under the new
     format.
   - Integration tests in `tests/cli.rs` asserting `> [comment] ...` / `> [note] ...` strings (lines ~4228, 4233,
     4339–4359, 4492–4500, 4721, 5075–5076, 5211).

4. Add regression coverage for the beautification itself.
   - A rendering unit test with a hard-wrapped, hyphen-split, ligature-bearing sidecar quote asserting the rendered
     callout contains one flowing line with the hyphenation healed.
   - A test proving block-ID stability: the same sidecar wrapped two different ways yields identical `^h-...` IDs.
   - A `tests/cli.rs` end-to-end sync test using a linked-style sidecar with wrapped/hyphenated quote lines plus a
     comment, asserting the full callout block shape.

5. Update `docs/highlights-ref-sync.md`.
   - Replace the generated-body examples (~lines 320–460) with the callout format and document the render-time
     beautification rules and the block-ID stability guarantee.

6. Verify.
   - `just all` (cargo fmt --check, clippy with all targets/features, full cargo test).
   - Real-world check against the vault if a synced PDF is available, e.g.
     `cargo run --quiet -- highlights sync ~/bob/lib/papers/log_is_the_agent.pdf --dry-run --bob-dir ~/bob`, then a real
     sync and a visual skim of the regenerated note to confirm the section is reflowed, de-hyphenated, and rendered as
     callouts with the original `^h-...` IDs intact.

## Expected Outcome

Highlights sections become genuinely pleasant to read in Obsidian: each highlight is a clean quote card containing
flowing, properly-joined prose; Bryan's comments sit inside as visually distinct nested note cards; standalone notes and
removed-annotation placeholders get their own card styles. No mid-word splits, no ligature garbage, no ragged short
lines. Existing notes upgrade automatically on their next sync with zero block-ID churn, so every task backlink and
block reference keeps working.
