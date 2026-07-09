---
create_time: 2026-06-16 09:20:05
status: done
prompt: sdd/prompts/202606/capture_target_picker_1.md
---
# Plan: Filterable Target Picker for Unrouted Captured Tasks

## Context

The **Capture Task** panel is an `hs.webview` prompt bound to a global Hammerspoon hotkey (configured in the chezmoi
repo, `home/dot_hammerspoon/init.lua`). On submit it delegates to bob:

```
bob capture --format json -- <text>
```

Routing is driven entirely by an `@token` in the text (bob's own parser, `parse_auto_route` in `src/native/capture.rs`):

- `@groceries buy milk` / `buy milk @groceries` → routes to `~/bob/groceries.md`.
- **No `@token` → silently appended to `~/bob/mac_inbox.md`** (the inbox; `INBOX_FILE` constant).

The unrouted path is a dead drop: the task lands in the inbox and Bryan later has to triage it by hand. The goal is to
turn the common "I know roughly where this belongs" case into a fast, **beautiful, filterable pick** from his **area**
and **active project** notes at submit time — instead of an inbox round-trip — while keeping the inbox as the friction-
free default.

## Goal

When the Capture Task panel is submitted **without** an explicit `@` target, present a filterable picker of the user's
**area notes** and **active project notes**. Selecting one routes the captured task to that note exactly as an `@token`
would. The explicit-`@` flow is unchanged. The inbox (`mac_inbox`) is the **pinned, default first choice** so a plain
`<enter>` keeps today's zero-friction behavior.

### Additional requirements (from the request)

- The **first and default** option — chosen on a bare `<enter>` with no typing/navigation — is `~/bob/mac_inbox.md`,
  shown as **`mac_inbox`**.
- The picker must make it **visually clear which rows are area notes vs project notes**.
- `mac_inbox` gets a distinct **icon / visual indicator** marking it as the default.

### Target UX flow

1. User triggers the panel, types a task, hits submit.
2. Hammerspoon asks bob whether the text is already routed — **reusing bob's own parser**, never re-implementing `@`
   detection in Lua (see contract below).
3. **Routed** (`@token` present) → capture immediately, no picker. _(Unchanged.)_
4. **Unrouted** → bob lists the routable inbox + area + active-project notes; Hammerspoon renders them in a native fuzzy
   picker (`hs.chooser`) with `mac_inbox` pinned first and flagged as the default.
5. The user filters/navigates and picks; the task is routed there. A bare `<enter>` selects `mac_inbox`.
6. Dismissing the picker (`Esc`) cancels cleanly without losing the typed text.

## Design decision: where the picker lives (I'm leading this call)

`bob` is a non-interactive CLI; a "beautiful filterable prompt" is a GUI concern. The clean split — which also mirrors
the already-shipped `bob capture` delegation pattern — is:

- **bob-cli (this repo — the deliverable here):** owns the _data_. It scans the vault, parses frontmatter, defines what
  counts as an "area" / "active project", enforces routability, and exposes the result over a stable JSON contract. This
  is tested Rust reusing existing scanning/parsing/styling infrastructure.
- **Hammerspoon / chezmoi (a separate Phase-2 plan, separate repo):** owns the _UI_. It consumes the JSON and renders
  `hs.chooser`, the native macOS fuzzy picker.

**Why `hs.chooser` rather than a custom HTML list in the webview:** it is the right tool for "beautiful" — native
rendering, built-in fuzzy filtering, keyboard navigation (`ctrl+n`/`ctrl+p`, arrows), per-row `subText` and `image`, and
`<enter>`-selects-first-row semantics for free. It is consistent with the existing Bob Pomodoro launcher UX, and it is
far less code/risk than hand-rolling filtering + key handling in JS. _(Alternative considered: extend the webview into a
custom filterable list with literal "Areas"/"Projects" section headers. It offers more layout control but cannot fuzzy-
filter and keep section headers visible, costs much more code, and reinvents what `hs.chooser` gives natively. Rejected;
the icon + `subText` + grouped ordering below deliver the "clear distinction" requirement within `hs.chooser`.)_

This plan ships the bob-cli command **in full** (independently testable) and pins down the **exact** Hammerspoon
contract so the chezmoi change can be executed as a focused Phase-2 plan — the same two-repo discipline used for the
original `bob capture` delegation. The chezmoi edits live in a different repo and are **out of scope for file changes
from this workspace**.

## What counts as a target (verified against the live vault)

- **Inbox / default:** `mac_inbox` → `~/bob/mac_inbox.md`. Derived from capture's existing `INBOX_FILE` constant so it
  stays single-sourced with the writer, and **always emitted first** even on an empty vault.
- **Area note:** frontmatter `type: "[[area]]"`. _(9 today: `cash`, `dev`, `gtd`, `gtd_daily`, `inbox`, `job`, `love`,
  `mac_inbox`, `recur`. `mac_inbox` is lifted out of this group and shown as the pinned default; `inbox` remains a
  normal area row.)_
- **Active project note:** frontmatter `type: "[[project]]"` **and** a non-terminal status. Single-sourced on the
  existing `ProjectStatus::is_terminal` (`done`/`canceled` are terminal; `wip`, `waiting`, unknown values, and the no-
  status default of `wip` are active). So "active" = `!status.is_terminal()`.
  - **Decision (overridable):** `waiting` projects are **included** — they're blocked, not finished, and remain valid
    capture targets. Flag if you'd rather hide them.

### Routability guard (correctness detail)

`bob capture` routes by writing to `<bob_dir>/<route>.md`, where the route token is **lowercased** and must match
`[A-Za-z0-9_-]`. A note is only safe to offer if routing back to it lands on the _same_ file, so a target must:

- live at the **vault root** (no subdirectory), **and**
- have a stem that is already lowercase and a valid route token.

This prevents a subtle data-loss bug (offering `Foo.md` would route to a freshly-created `foo.md`). Conveniently, the
"vault root only" half is enforced _structurally_: the command reads only the **top-level** directory entries (no
recursion), which also naturally drops `_templates/new_project.md`. The lowercase/charset half is checked explicitly;
anything failing it is **skipped, never mis-routed**, and surfaced as a `stderr` note. Every current note passes, so
this is mostly future-proofing.

## Deliverable (Phase 1, this repo): `bob capture-targets`

A new top-level, **read-only** subcommand that lists the routable inbox + area + active-project notes.

- **Name:** `bob capture-targets` — self-documenting, tied to the capture feature, fits the kebab-case multi-word
  convention (`move-done-tasks`, `bulk-git-commit`). _(Alternative `bob routes` is shorter but vaguer; open to it.)_
- **Wiring:**
  - new `NativeCommand::CaptureTargets` + `mod capture_targets;` + dispatch arm in `src/native.rs`;
  - new `src/native/capture_targets.rs`;
  - registered in the `runner.rs` `SUBCOMMANDS` table **alphabetically between `capture` and `dataview`** (satisfies the
    `subcommands_are_sorted_alphabetically` guard), with a one-line top-level `AFTER_HELP` example.
- **Reuse (keep semantics single-sourced — promote helpers to `pub(crate)` rather than duplicate):**
  - from `capture.rs`: `is_route_token` and the `mac_inbox.md`/route-label knowledge (the routability + inbox source of
    truth lives next to the writer);
  - from `projects.rs`: `ProjectStatus` (+ `parse`/`label`/`is_terminal`), the frontmatter helpers (`parse_frontmatter`,
    `frontmatter_value`, `trim_yaml_scalar`, `frontmatter_is_project`, plus a new sibling `frontmatter_is_area`), and
    `is_markdown_file`.
  - The scan itself is intentionally lean: read the **root dir only**, parse each `.md` file's frontmatter, classify by
    `type`, drop terminal projects, apply the routability guard. No need for the heavyweight `Project`/`^prj` machinery.
- **Options** (per `cli_rules.md`: alphabetical, every long option gets a short alias, colored output):
  - `-b, --bob-dir DIR` — vault root; defaults to `BOB_DIR` or `~/bob` (same as capture/projects).
  - `-f, --format human|json` — default `human` (same contract style as `bob capture`).
  - `-h, --help`.
- **Ordering (bob owns it, so it's testable):** `mac_inbox` (default) first → areas (alpha) → active projects (alpha).
  Hammerspoon renders rows in exactly this order, so a bare `<enter>` lands on `mac_inbox`.

### JSON output — the Hammerspoon contract (stable snake_case)

```json
{
  "ok": true,
  "bob_dir": "/home/bryan/bob",
  "count": 16,
  "targets": [
    {
      "route": "mac_inbox",
      "name": "mac_inbox",
      "label": "mac_inbox.md",
      "kind": "inbox",
      "is_default": true,
      "status": null,
      "relative_path": "mac_inbox.md"
    },
    {
      "route": "cash",
      "name": "cash",
      "label": "cash.md",
      "kind": "area",
      "is_default": false,
      "status": null,
      "relative_path": "cash.md"
    },
    {
      "route": "bob",
      "name": "bob",
      "label": "bob.md",
      "kind": "project",
      "is_default": false,
      "status": "wip",
      "relative_path": "bob.md"
    }
  ]
}
```

- `route` is exactly what is passed to `bob capture --route` (the inbox entry carries `route: "mac_inbox"` for display,
  but Hammerspoon maps it to the _unrouted_ capture — see contract).
- `kind` ∈ `inbox` | `area` | `project` drives the icon and grouping. `is_default` is `true` only for the inbox entry.
- `status` is non-null only for projects (`wip`/`waiting`/…), to color the project `subText`.
- Errors emit `{ "ok": false, "error": "..." }`, matching `bob capture`.

### Human output (beautiful, colored, scannable)

Run in a terminal, `bob capture-targets` prints a grouped, colored list reusing `style.rs` (`Styler`, `pad_right`,
`display_width`) and the exact project-status colors from `projects list` (wip=yellow, waiting=blue) — so the kinds are
unmistakable here too:

```
Capture targets · /home/bryan/bob

  Inbox
    ★ mac_inbox      mac_inbox.md   default

  Areas
    cash             cash.md
    dev              dev.md
    …

  Active projects
    bob              bob.md         wip
    sase             sase.md        waiting
    …

16 targets · 1 inbox · 9 areas · 6 active projects
```

Names cyan, file labels dim, the `★` default marker highlighted, project status colored. Colors auto-disable when piped
or under `NO_COLOR` (existing `Styler::detect`). An empty vault prints a friendly "no targets" line. Exit `0` on success
(including zero targets); scan errors go to `stderr` and exit `1`, matching `projects list`.

## Hammerspoon integration contract (Phase 2 — separate chezmoi plan)

Documented here so bob-cli ships the right surface; the Lua edit is executed later from the chezmoi context (precedent:
`sase_plan_hammerspoon_capture_delegation.md`).

1. On submit, run `bob capture --dry-run --format json -- <text>`. This **reuses bob's exact `@`-parser**; Lua never
   re-implements route detection.
2. `result.routed == true` → run the real `bob capture --format json -- <text>` and notify. _(Today's flow, unchanged.)_
3. `result.routed == false` → run `bob capture-targets --format json` and build an `hs.chooser` from `targets`, **in
   order** (so `mac_inbox` is row 1 and is selected by a bare `<enter>`). Per-row rendering:
   - **`text`** = `name` (pure, for clean fuzzy matching).
   - **`subText`** conveys the kind/default: inbox → `"Inbox · default · ⏎"`; area → `"Area"`; project →
     `"Project · " .. status`.
   - **`image`** = a per-kind icon for the "beautiful + clear distinction" requirement: inbox → an inbox/tray glyph (the
     **default marker**, e.g. SF Symbol `tray.and.arrow.down.fill` via `hs.image.imageFromName`, or a `📥` fallback);
     area → e.g. `square.stack.3d.up.fill` / `🗂️`; project → e.g. `folder.fill` / `📁`. _(Emoji-in-`subText` is the
     zero-asset fallback if images are fussy.)_
4. On choice:
   - inbox row (`is_default == true`, equivalently `kind == "inbox"`) → `bob capture --format json -- <text>`
     (**unrouted**, so placement stays byte-for-byte identical to today's inbox behavior);
   - any other row → `bob capture --format json --route <route> -- <text>`. Reuse the existing async / login-shell /
     `$1`-quoting / in-flight-task-guard patterns from the current capture runner.
5. On dismissal (`Esc`): cancel without losing the typed text.
6. _(Optional niceties for the Phase-2 plan: let a typed-but-unmatched query commit as a brand-new route to create a new
   note; briefly cache `capture-targets` to keep the picker instant.)_

**Decision (overridable):** routing the default through the _unrouted_ `bob capture` (step 4) deliberately preserves
today's append-to-end-of-file inbox placement, rather than `--route mac_inbox` (which would insert after the last task
block). Flag if you'd prefer the routed placement for consistency.

## Testing

- **Unit (`capture_targets.rs`):** routability guard (root-only is structural; lowercase + valid token enforced);
  active-project filter (`wip`/`waiting`/unknown in, `done`/`canceled` out); area detection; `mac_inbox` lifted to the
  pinned default and **not** duplicated in the areas group; ordering (inbox → areas alpha → projects alpha);
  `is_default` set only on inbox; stable JSON shape (snake_case keys, `kind`/`status` values).
- **Integration (`tests/cli.rs`, existing `TempDir` + `BOB_DIR` patterns):** mixed-note temp vault → grouped human
  output with no ANSI when piped; `--format json` parses to the expected ordered `targets` with `mac_inbox` first and
  `is_default:true`; empty vault → `count:0`, exit `0`, still lists the inbox default; a non-routable note (e.g.
  uppercase stem, or under a subdir) is skipped; `-b` override works.
- **Registration/help guards that must be updated** (adding a subcommand touches these):
  - `tests/cli.rs::all_top_level_subcommand_help_is_safe_and_plain` → add a `capture-targets` case;
  - `tests/cli.rs::public_help_surfaces_do_not_list_long_only_options` → add a `capture-targets` case;
  - `justfile` `install-smoke` → add `bob capture-targets --help`;
  - `--help` lists options alphabetically and is native-only (no script extraction), like the other subcommands.

## Verification

- `just all` (`cargo fmt --check`, `cargo clippy --all-targets --all-features`, `cargo test`).
- Manual smoke against a scratch vault: `BOB_DIR=<tmp> bob capture-targets` (human) and `--format json`, plus the end-
  to-end three-call sequence (`capture --dry-run` → `capture-targets` → `capture --route`) to confirm the contract.

## Risks & mitigations

- **Mis-routing via case/charset** → routability guard (structural root-only + explicit token check); covered by tests.
- **"Active" semantics drift** → single-sourced on `ProjectStatus::is_terminal`; documented and tested.
- **JSON contract drift breaking Hammerspoon** → stable snake_case schema with a shape test, same discipline as
  `bob capture`.
- **Default no longer behaves like today's inbox** → default maps to the _unrouted_ capture, preserving placement.
- **Two-repo coordination** → bob-cli ships first and is independently testable; the chezmoi/Hammerspoon change is a
  self-contained Phase-2 plan depending only on this command's JSON contract.

## Non-goals

- No interactive TUI/picker inside `bob` itself (the GUI picker is `hs.chooser`).
- No change to `@token` parsing, task formatting, or file-placement logic in `bob capture`.
- No change to what frontmatter marks a note as an area/project (consumed as-is).
- Resources/Archives and other note types are not offered as targets.
- The chezmoi/Hammerspoon edit is specified here but executed as a separate Phase-2 plan from the chezmoi context.
