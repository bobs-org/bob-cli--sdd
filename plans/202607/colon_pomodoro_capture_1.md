---
create_time: 2026-07-10 16:35:25
status: done
prompt: .sase/sdd/plans/202607/prompts/colon_pomodoro_capture_1.md
tier: tale
---
# Plan: Make colon the Pomodoro capture discriminator

## Objective

Replace the redundant bang in the Pomodoro-linked capture syntax with a colon-based grammar across `bob capture` and the
chezmoi-managed Hammerspoon task panel. A complete request should use `@<route>:<block-id>`, while omitted pieces in the
Hammerspoon shorthand should determine which prompts are needed. Preserve the existing routing, section, schedule,
validation, failure-atomicity, and prompt-state guarantees.

The colon is sufficient as the discriminator: ordinary task routing accepts `@route`, bullet routing accepts
`@route#section`, and route names themselves cannot contain `:`. Reserving a terminal `@route:block-id` token for
Pomodoro-linked capture therefore adds no ambiguity to either existing route grammar.

## Product behavior

- Make `@<route>:<block-id>` the canonical `bob capture` marker in either supported terminal position. For example, both
  `@dev:focus-123 Write the design` and `Write the design @dev:focus-123` create the same Pomodoro-linked task.
- In the Hammerspoon panel, recognize the following trailing, whitespace-delimited forms:

  | Marker           | Note prompt | Block-ID prompt |
  | ---------------- | ----------- | --------------- |
  | `@dev:focus-123` | no          | no              |
  | `@dev:`          | no          | yes             |
  | `@:focus-123`    | yes         | no              |
  | `@:`             | yes         | yes             |

  The `@:focus-123` form completes the grammar symmetrically and lets a user who knows the block ID choose only the
  destination note.

- Keep route and block-ID validation unchanged: each non-empty component permits only `A-Z`, `a-z`, `0-9`, `_`, and `-`,
  and routes are normalized to lowercase. Hammerspoon-only incomplete forms must never be passed to the CLI.
- Continue recognizing the just-introduced `@!<route>:<block-id>`, `@!<route>`, and `@!` forms as compatibility aliases,
  but remove them from canonical examples and generated requests. This avoids breaking an already deployed shortcut
  while making `!` unnecessary for all new input.
- Preserve the existing meaning of `@`, `@route`, `@#`, `@#prefix`, `@route#`, and `@route#prefix`. A colon marker is
  special only in a leading or trailing route position; a middle token remains literal, and `--route` continues to keep
  `@tokens` literal.
- Treat a terminal colon marker with an invalid non-empty route or block ID as a clear usage/validation error rather
  than silently capturing it as ordinary text. Marker-only input remains an empty-body no-op in Hammerspoon and a
  missing-text error in the CLI.
- Preserve scheduled capture ordering: `s:N` may remain immediately before or after a complete terminal colon marker,
  with the block ID still rendered as the final task token.
- Preserve staged Hammerspoon values on block-ID validation errors and `bob capture` failures. Picker cancellation must
  return focus to the task prompt without leaking route or ID state into the next invocation.

## Implementation

1. **Adopt the colon grammar in `bob-cli`.**
   - Generalize the special route-token parser so canonical `@route:block-id` tokens produce the existing Pomodoro
     capture kind, while the bang-prefixed form remains an accepted compatibility alias.
   - Detect malformed terminal colon markers explicitly, validate the route and block-ID halves independently, and
     update route-marker recognition so scheduled offsets work in both terminal orders.
   - Keep leading-route precedence, middle-token literal behavior, forced-route literal behavior, and the existing
     two-note preflight/write transaction unchanged.
   - Update command help, README examples, syntax descriptions, and error messages to teach `@<route>:<block-id>` as
     canonical and describe the Hammerspoon prompt forms without presenting `!` as required.

2. **Generalize the pure-Lua Hammerspoon request model in the linked chezmoi repository.**
   - Replace the bang-specific request parser with a colon-marker descriptor that can carry an optional normalized route
     and optional validated block ID.
   - Model the four prompt combinations explicitly so picker-backed, ID-prompted, and fully specified requests all
     converge on one final request constructor.
   - Generate only the canonical leading `@route:block-id` token when invoking `bob capture`; retain parsing of the old
     bang shorthands as aliases at the boundary.
   - Keep marker recognition terminal and whitespace-delimited, and leave all existing note/section descriptors and
     route normalization behavior intact.

3. **Adapt the Hammerspoon panel state transitions.**
   - Route `@:` through the existing target chooser and then the block-ID prompt; route `@dev:` directly to the same
     block-ID stage.
   - Route `@:focus-123` through the target chooser and submit immediately after a valid target is selected; allow a
     complete `@dev:focus-123` request to capture without either prompt.
   - Reuse the existing asynchronous guards, chooser rows, prompt reconfiguration, positional shell invocation, and
     success/failure notification paths. Clear staged values only through the existing panel-close lifecycle.
   - Keep the `cmd+shift+ctrl+i` binding unchanged.

4. **Expand regression coverage in both repositories.**
   - In `bob-cli`, cover canonical leading/trailing markers, route normalization, schedule ordering, malformed/empty
     components, marker-only input, middle and forced-route literals, compatibility aliases, and unchanged atomic
     failure behavior.
   - In the Hammerspoon pure-Lua suite, cover all four colon forms, legacy aliases, invalid components, empty bodies,
     picker cancellation/invalid transitions, state retention, and convergence on canonical synthesis.
   - Retain explicit regression cases for every existing `@`, `#`, and ordinary route mode so colon parsing cannot steal
     those requests.

## Verification

- Run the focused Rust parser and CLI integration tests, then the complete `bob-cli` test/check suite.
- Run the Hammerspoon Busted suite and the linked chezmoi aggregate test recipe.
- Run Rust formatting checks, `luac -p` on the changed Hammerspoon Lua files, Stylua in check mode for those files, and
  `git diff --check` in both repositories.
- Audit the final diffs to confirm documentation and errors use the canonical colon syntax, generated requests contain
  no bang, legacy aliases remain tested, the hotkey is unchanged, shell arguments remain positional, and no live vault
  or generated deployment files were modified.
