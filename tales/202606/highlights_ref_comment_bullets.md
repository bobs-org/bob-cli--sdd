---
create_time: 2026-06-03 09:14:42
status: done
prompt: sdd/prompts/202606/highlights_ref_comment_bullets.md
---
# Fix Highlights Sidecar Bullet Comments

## Problem

`bob highlights-ref sync ~/bob/lib/papers/log_is_the_agent.pdf --dry-run --bob-dir ~/bob` reports `note_action: none`,
so the current implementation believes the generated note for `~/bob/ref/papers/log_is_the_agent.md` is already correct.
The generated note does include the page 2 comment, but renders it as:

```md
> [comment] - Support sase tool call replay?
```

The associated Highlights sidecar at `~/bob/lib/papers/log_is_the_agent.md` exports the user comment as a Markdown list
item after the highlighted quote:

```md
> A determinism contract ...

- Support sase tool call replay?
```

That means the command did not miss the comment. It parsed the post-highlight text as a comment, but failed to normalize
the leading Markdown bullet marker.

## Root Cause

The sidecar parser in `src/native/highlights_ref/mod.rs` routes text after a blockquote through:

- `parse_sidecar_chunk`
- `normalize_annotation_text`
- `strip_comment_label`
- `render_annotation_block`

`strip_comment_label` only removes explicit `Comment:`, `comment:`, `Note:`, and `note:` prefixes. It does not recognize
the linked Highlights export shape where a freeform comment is emitted as one or more Markdown bullet list items.
Because of that, `- Support...` becomes the literal comment body, and rendering adds `[comment] ` in front of the
still-present dash.

There is existing linked-sidecar coverage, but it only covers:

- blockquoted highlight hard wrapping,
- marker-list fields after the first marker mirror,
- explicit `Comment:`/`Note:` labels,
- unlabeled non-list comments.

It does not cover ordinary bullet comments after a real highlight.

## Implementation Plan

1. Add focused parser coverage for the real export shape.
   - Extend the sidecar parser unit tests with a linked-page highlight followed by a bullet comment like
     `- Support sase tool call replay?`.
   - Assert the annotation text stays the highlight text and the comment becomes `Support sase tool call replay?`.
   - Include a multi-line bullet comment case if the parser can support it cleanly without changing unrelated behavior.

2. Normalize comment-side Markdown list markers.
   - Add a small helper near `strip_comment_label` that removes a leading Markdown unordered-list marker from comment
     text when every nonblank comment line is list-shaped, preserving multiline comment content without stripping
     hyphens that are part of normal prose.
   - Keep marker-list detection for marker mirrors intact: marker fields such as `- status: wip` and `- parent: sase`
     must still allow `is_sidecar_marker_mirror` to exclude the marker mirror instead of rendering it as a comment.
   - Avoid broad Markdown parsing unless the tests show it is necessary; this is a narrowly scoped normalization issue.

3. Preserve existing supported sidecar shapes.
   - Keep explicit labels working: `Comment: x` and `Note: x` should still render as `[comment] x`.
   - Keep unlabeled prose after a quote working unchanged.
   - Keep wrapped linked-sidecar highlight lines from being misclassified as comments.
   - Keep marker mirror exclusion unchanged.

4. Add an end-to-end CLI regression test.
   - Add or adjust a `bob highlights-ref sync` integration test in `tests/cli.rs` with a linked Highlights sidecar
     containing a non-marker bullet comment after a quote.
   - Assert the generated note contains `> [comment] Support sase tool call replay?` and does not contain
     `> [comment] - Support sase tool call replay?`.

5. Update documentation if behavior is clarified.
   - In `docs/highlights-ref-sync.md`, update the generated body contract for linked sidecars to mention that comments
     exported as Markdown list items are normalized by stripping the list marker.

6. Verify.
   - Run `cargo fmt --check`.
   - Run focused tests: `cargo test highlights_ref`.
   - Run the real dry run again:
     `cargo run --quiet -- highlights-ref sync ~/bob/lib/papers/log_is_the_agent.pdf --dry-run --bob-dir ~/bob`.
   - If the focused tests pass and runtime is reasonable, run the broader CLI suite or full `cargo test`.

## Expected Outcome

After the fix, the real note should be considered stale until regenerated, and the page 2 comment should render as:

```md
> [comment] Support sase tool call replay?
```

The command should continue to treat first-page marker metadata list items as marker data, not as user comments.
