---
create_time: 2026-06-03 06:55:06
status: done
prompt: sdd/prompts/202606/highlights_ref_plain_parent.md
---
# Highlights Ref Plain Parent Marker Plan

## Goal

Allow the PDF marker note for `bob highlights-ref` to use a bare `parent` value such as:

```text
- parent: obsidian
```

instead of requiring:

```text
- parent: [[obsidian]]
```

The marker should be easier to type, but generated Bob reference notes should still satisfy the Obsidian note workflow
requirement: `parent` frontmatter links to another Markdown note. In practice, bare marker/frontmatter parent strings
should be canonicalized to Obsidian wikilinks in the synced projection, so generated notes continue to render
`parent: "[[obsidian]]"`.

## Context From Inspection

- `src/native/highlights_ref/mod.rs` already parses bare marker scalars like `obsidian` as
  `MarkerValue::String("obsidian")`.
- Today that parsed value is preserved as-is through hashing and rendering, so a bare marker parent would generate
  `parent: obsidian` frontmatter rather than a linked `parent: "[[obsidian]]"`.
- Hashing currently compares exact parsed projections. Without canonicalization, `parent: obsidian` and
  `parent: [[obsidian]]` would be treated as different values even though they should represent the same parent note.
- Existing docs and fixtures only show bracketed parent values, so users have no clear contract that bare parent values
  are accepted.
- No new CLI subcommands or options are needed.

## Proposed Contract

- `parent` remains required in marker/frontmatter projections.
- A marker value of `parent: foobar` means the same parent target as `parent: [[foobar]]`.
- Bare parent targets should also work for nested or spaced note names, for example `parent: projects/foo` and
  `parent: Systems Performance`, by wrapping the trimmed target in `[[...]]`.
- Existing wikilinks such as `[[foobar]]`, `[[projects/foo]]`, and aliases like `[[foobar|Foo Bar]]` should be
  preserved, not double-wrapped.
- Generated reference note frontmatter should continue to render the canonical linked form, e.g. `parent: "[[foobar]]"`.
- PDF marker write-back can render the canonical linked form. The important behavior is that a user-authored marker does
  not need to start in that form.
- Projection hashes and conflict detection should use the canonical parent value. This makes `foobar` and `[[foobar]]`
  equivalent and avoids false marker/frontmatter conflicts.
- Empty parent remains invalid. Non-scalar parent values such as lists should fail with a clear parent-specific error
  instead of producing invalid parent frontmatter.

## Implementation Plan

1. Add a parent canonicalization helper in `src/native/highlights_ref/mod.rs`.
   - Detect the `parent` field after generic marker/frontmatter value parsing.
   - Trim string-like values.
   - Preserve existing `[[...]]` wikilinks.
   - Wrap non-empty bare targets as `[[target]]`.
   - Reject empty or non-scalar values with a clear error message tied to the source (`marker` or `frontmatter`).

2. Apply canonicalization before projection hashes and rendering.
   - Canonicalize marker projections immediately after parsing the PDF marker.
   - Canonicalize frontmatter projections before computing `frontmatter_hash`.
   - Keep `validate_required_marker_keys` operating on the canonical projection.
   - Ensure `render_marker`, `render_with_projection`, and stored `highlights_marker_hash` all receive the canonical
     projection.

3. Preserve idempotence and conflict behavior.
   - A PDF marker containing `parent: obsidian` plus a generated note containing `parent: "[[obsidian]]"` should hash as
     unchanged on subsequent runs.
   - A frontmatter edit from `parent: "[[obsidian]]"` to `parent: obsidian` should be normalized back to the linked form
     instead of creating a false conflict.
   - Marker-only and frontmatter-only edit decisions should continue to work the same way for all other fields.

4. Update tests.
   - Add unit coverage that `parse_marker` accepts bare parent values and canonicalizes them to `[[...]]`.
   - Add coverage that an already bracketed parent remains unchanged.
   - Add coverage for a frontmatter-sourced bare parent normalizing to the same canonical projection.
   - Add an integration test where a marker with `- parent: obsidian` creates a note with `parent: "[[obsidian]]"`.
   - Add or extend an idempotence assertion so a second sync with the bare marker reports `writes: none`.
   - Add rejection coverage for an invalid non-scalar parent if the implementation introduces that stricter validation.

5. Update docs and fixtures.
   - Change marker examples in `docs/highlights-ref-sync.md` to show the bare shorthand, while explicitly saying
     `[[...]]` is also accepted.
   - Update troubleshooting for missing parent to suggest `- parent: obsidian` as the simple form.
   - Update README wording if needed so it does not imply brackets are required in marker notes.
   - Consider updating `tests/fixtures/highlights_ref/marker_note.txt` to use a bare parent value as executable
     documentation.

6. Verify.
   - Run `cargo fmt --check`.
   - Run focused highlights-ref tests, e.g. `cargo test highlights_ref`.
   - Run the full `cargo test`.
   - Run `cargo clippy --all-targets --all-features`.
   - Run `git diff --check`.

## Risks and Mitigations

- **False conflicts from representation changes:** normalize both marker and frontmatter projections before hashing.
- **Double-wrapped links:** explicitly detect existing `[[...]]` values before wrapping.
- **Breaking existing bracketed markers:** preserve wikilinks exactly.
- **Invalid generated parent frontmatter:** reject empty/non-scalar parent values and render generated notes from
  canonical projections only.
