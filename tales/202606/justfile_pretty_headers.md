---
create_time: 2026-06-02 08:33:59
status: done
prompt: sdd/prompts/202606/justfile_pretty_headers.md
---
# Justfile Quality Header Redesign

## Context

The `justfile` recently gained an `all: fmt lint test` aggregate target, and each of `fmt`, `lint`, and `test` prints a
plain header before running:

```
fmt:
    @printf '==> format\n'
    cargo fmt --check
```

The resulting output (`==> format`, `==> lint`, `==> test`) is functional but visually flat and hard to scan, especially
in `just all` where three sections scroll past in a single stream. The user asked me to lead the design and make the
headers genuinely beautiful.

This plan is scoped strictly to the _presentation_ of the section headers in `justfile`. No command behavior, target
graph, or auxiliary recipe changes beyond what's needed to render the new headers.

## Goals

1. Replace the flat `==> format` style with a polished, scannable section banner for `fmt`, `lint`, and `test`.
2. Keep the exact underlying commands unchanged (`cargo fmt --check`, `cargo clippy --all-targets --all-features`,
   `cargo test`) and the `all: fmt lint test` ordering.
3. Factor the banner styling into a single reusable helper so the look is defined once, not copy-pasted three times.
4. Degrade gracefully: rich color/styling on an interactive terminal, clean plain text when output is piped or
   redirected (logs, CI).
5. Keep the `justfile` idiomatic and small; do not touch packaging/release recipes.

## Design (I am leading this)

### Visual language

Each step gets a three-part banner:

- a blank line for breathing room,
- a **bold, colored title** with a themed icon, and
- a thin colored rule beneath it to separate the section from the command output that follows.

Color + icon are themed per step so the three sections are instantly distinguishable when scanning `just all`:

| Step   | Color  | Icon | Title    |
| ------ | ------ | ---- | -------- |
| format | blue   | 🎨   | `FORMAT` |
| lint   | yellow | 🔍   | `LINT`   |
| test   | green  | 🧪   | `TEST`   |

Rendered (interactive terminal — colors shown here as plain text):

```

🎨  FORMAT
────────────────────────────────────────────────
cargo fmt --check
   ...cargo output...

🔍  LINT
────────────────────────────────────────────────
cargo clippy --all-targets --all-features
   ...cargo output...

🧪  TEST
────────────────────────────────────────────────
cargo test
   ...cargo output...

  ✓  ALL CHECKS PASSED

```

The closing `✓ ALL CHECKS PASSED` banner is printed only by `all`, and only after `fmt lint test` have all succeeded
(the shell runs with `-e`, so reaching `all`'s body means every dependency passed). It gives the aggregate workflow a
satisfying, unambiguous finish.

### Implementation approach (DRY + graceful degradation)

Define the style once in a private helper recipe rather than repeating `printf` in every target:

- A `justfile` variable holds the rule string (single source for width/character).
- A private `_banner color icon label` recipe renders the header. Private (`_`-prefixed) recipes are hidden from
  `just --list`, so the helper won't clutter the recipe menu.
- `fmt`, `lint`, and `test` invoke it via **parameterized dependencies** so the banner prints before the body:

  ```
  fmt: (_banner "34" "🎨" "FORMAT")
      cargo fmt --check
  ```

- `_banner` checks `[[ -t 1 ]]`: if stdout is a TTY it emits ANSI bold + color; otherwise it emits the same layout as
  plain text (icon, title, rule) with no escape codes — so piped logs and CI output stay clean and readable.
- `all` keeps `all: fmt lint test` and gains a small body that prints the success banner with the same TTY-aware
  treatment.

This centralizes the design: changing the rule, colors, or layout later is a one-line edit in `_banner`.

### Why this over alternatives

- **Boxed/framed titles** (`┌──┐ │ │ └──┘`) look nice but require padding math that breaks with variable-length labels
  and double-width emoji. A title + underline rule is robust to any label and width.
- **Inline `printf` per recipe** (today's approach) duplicates styling three times and drifts over time; the helper
  keeps it consistent.
- **Always-on ANSI** corrupts redirected logs with escape sequences; the TTY check avoids that.

## Validation

After editing `justfile`:

1. `just --summary` / `just --list` — target graph valid, `all/fmt/lint/test` present, `_banner` hidden.
2. `just fmt` — blue 🎨 FORMAT banner renders; `cargo fmt --check` still runs and passes.
3. `just lint` — yellow 🔍 LINT banner renders; clippy still passes.
4. `just test` — green 🧪 TEST banner renders; tests still pass.
5. `just all` — all three sections render in order, followed by the `✓ ALL CHECKS PASSED` banner.
6. `just all | cat` — confirms the non-TTY path emits clean plain text with no raw escape codes.

If any validation command fails due to pre-existing code issues (not the header change), preserve the `justfile` change
and report the exact failure rather than broadening scope.

## Prototype status

The mechanism was verified in a throwaway justfile with `just 1.51.0`: parameterized dependencies fire the banner before
the body, the `_`-prefixed helper is hidden from `just --list`, and the non-TTY branch prints clean plain text. The
design rests on confirmed-working behavior.
