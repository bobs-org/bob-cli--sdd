---
create_time: 2026-06-04 09:29:25
status: done
prompt: sdd/prompts/202606/highlights_ref_marker_syntax.md
---
# Plan: Tighten `bob highlights-ref` PDF Marker Syntax

## Context

`bob highlights-ref` syncs a PDF marker note with generated reference-note frontmatter. The marker note is intended to
be compact and user-authored, for example:

```text
- status: wip
- parent: memory_ref
- title: The Log is the Agent
```

The current implementation has two representation layers mixed together:

- Marker/frontmatter projections are canonicalized so `parent: memory_ref` becomes `[[memory_ref]]`.
- The same canonical projection is also used to render PDF marker write-back.

That means when a note-side change contributes to the synced projection, `render_marker()` can rewrite the whole PDF
marker into frontmatter-like syntax:

```text
- status: wip
- parent: [[memory_ref]]
- title: "The Log is the Agent"
```

This is the root cause of unwanted marker-note normalization. The code path is:

- `plan_pdf_sync()` parses the marker and frontmatter, resolves the synced projection, and calls
  `render_marker(&synced_projection)`.
- `canonicalize_parent()` canonicalizes marker and frontmatter `parent` values to wikilinks for hashing and generated
  frontmatter.
- `MarkerValue::as_marker_value()` quotes ordinary strings with spaces, so `title: The Log is the Agent` renders as
  `title: "The Log is the Agent"`.
- `marker_write_needed` compares that rendered marker with the raw PDF annotation whenever frontmatter contributes.

`scan` currently sets `write_pdf: false` and should refuse marker writes, but the rendering bug still matters because
dry-runs preview the wrong marker shape, `sync --write-pdf` writes it, and any scan variant or older deployed build that
allows marker writes will normalize the marker annotation.

## Desired Contract

- The PDF marker note uses bare marker syntax for `parent`: `- parent: memory_ref`.
- Marker `parent` values using Obsidian wikilinks, such as `- parent: [[memory_ref]]`, are invalid and should fail with
  a clear marker parse/validation error.
- Generated reference-note frontmatter should continue to render `parent` as an Obsidian wikilink, e.g.
  `parent: "[[memory_ref]]"`.
- Projection hashes and conflict detection should continue to use the canonical linked parent so existing generated
  frontmatter and bare marker parent values compare as the same logical parent.
- PDF marker write-back should render marker-style values, not frontmatter-style values:
  - simple parent wikilinks are unwrapped back to bare targets;
  - ordinary strings with spaces render without quotes when they are unambiguous;
  - values that genuinely need structured syntax, such as inline lists, continue to render in supported marker syntax.
- The provided latter marker form should fail. At minimum it fails because marker `parent` uses a wikilink. If we decide
  to make marker scalar strings stricter too, add explicit tests for quoted scalar `title` rejection and update docs to
  remove or narrow the existing YAML-subset language.

## Implementation Plan

1. Split parent validation by source.
   - Keep frontmatter canonicalization accepting bare or linked parent values so old/generated notes remain usable.
   - Add marker-specific parent validation before canonicalization, using the raw parsed marker value or raw marker
     text.
   - Reject marker `parent` values that are wikilinks, aliases, embeds, block links, inline lists, null, empty, or other
     non-bare scalar forms.
   - Canonicalize accepted bare marker parents to `[[target]]` only inside the internal projection.

2. Add marker-specific rendering for `parent`.
   - Keep `render_with_projection()` using `MarkerValue::as_frontmatter_value()`.
   - Change `render_marker()` so `FIELD_PARENT` renders through a helper that converts a simple canonical wikilink like
     `[[memory_ref]]` back to `memory_ref`.
   - If frontmatter contributes a parent value that cannot be represented as the bare marker contract, return an error
     before any write instead of emitting linked marker syntax.

3. Make marker string rendering match the marker note contract.
   - Adjust marker string rendering so ordinary strings with spaces, such as `The Log is the Agent`, render bare rather
     than JSON-quoted.
   - Preserve quoting only where needed to avoid changing the parsed value, or intentionally reject unsupported values
     if we tighten the marker grammar further.
   - Keep frontmatter rendering unchanged; frontmatter may still quote wikilinks and strings as needed for YAML.

4. Update tests.
   - Add unit coverage that `parse_marker("- parent: memory_ref")` succeeds and hashes equivalently with frontmatter
     `parent: "[[memory_ref]]"`.
   - Add unit/integration coverage that marker `parent: [[memory_ref]]` fails and causes `sync`, `marker`, and `scan`
     planning to fail before writes.
   - Add marker renderer coverage for: `- parent: memory_ref` and `- title: The Log is the Agent`.
   - Add a regression integration test with a bare marker and a frontmatter-contributed change, then run
     `sync --write-pdf` and assert the PDF marker keeps bare `parent` and bare title.
   - Update existing integration fixtures/tests that currently author PDF markers with `[[obsidian]]` to use bare
     `obsidian`, except tests that intentionally verify rejection.
   - Keep or revise YAML-subset tests depending on the final strictness decision for quoted non-parent values.

5. Update documentation and fixtures.
   - Update `docs/highlights-ref-sync.md` and `README.md` so marker examples show only bare marker parent syntax.
   - Remove wording that says marker `parent` wikilinks are accepted.
   - Clarify that generated note frontmatter renders `parent` as a wikilink even though the PDF marker must stay bare.
   - Update `tests/fixtures/highlights_ref/*` marker examples to the bare syntax.

6. Verify.
   - Run focused unit/integration tests around `highlights_ref`.
   - Run `cargo fmt --check`.
   - Run `cargo test highlights_ref`.
   - Run `cargo test` if the focused suite passes in reasonable time.
   - Run `git diff --check`.

## Risks

- Existing PDFs with `parent: [[...]]` markers will fail until edited to the bare syntax. That is intentional per the
  new requirement, but docs and errors need to make the fix obvious.
- If marker quoted-string support is removed broadly, existing markers using quoted aliases or list elements may fail.
  Avoid broad removal unless we explicitly decide the marker grammar should no longer support those values.
- Parent aliases such as `[[memory_ref|Memory Ref]]` cannot be represented in the new bare marker contract. Treat them
  as invalid marker input rather than silently changing their target.
