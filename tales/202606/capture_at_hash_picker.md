---
create_time: 2026-06-19 15:49:03
status: done
prompt: sdd/prompts/202606/capture_at_hash_picker.md
---
# Plan: `@#section` Capture Picker Marker

## Context

The current capture stack has two separate responsibilities:

- `bob capture` owns the concrete write contract. It already parses tokens such as `@note#Ideas` and `@note#`, routes to
  `note.md`, captures an ordinary bullet, and inserts it into the selected non-`Tasks` Markdown section.
- Hammerspoon owns the GUI picker. The live capture prompt currently recognizes only a trailing whitespace-separated
  bare `@` marker, such as `follow up @`, as "open the area/project target picker". Plain text captures directly to
  inbox, and explicit `@route` / `@route#section` text is delegated to `bob capture` unchanged.

The missing behavior is the picker form of the same section syntax:

- `follow up @#Ideas` should open the same area/project picker as `follow up @`.
- After the user chooses a target, the final capture should behave as if the user had typed `@chosen#Ideas follow up` or
  `follow up @chosen#Ideas`: route to the chosen note, capture a bullet, and insert into the matching section.
- The marker must not be captured literally.

Required Obsidian memory was read with:

```bash
sase memory read obsidian.md --reason "Need Obsidian note-file workflow context before changing bob capture note reference parsing"
```

No new CLI subcommand or option is planned, so the `cli_rules.md` long-memory trigger does not apply.

## Current Findings

- In `src/native/capture.rs`, `parse_route_token("@foo#Ideas")` works because the route part before `#` is `foo`.
- `parse_route_token("@#Ideas")` currently returns `None` because the route part is empty. In plain CLI usage that is
  reasonable: `bob` is non-interactive and has no picker to ask for a route.
- In `/home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua`, `parseCaptureRequest()` only matches
  `^(.-)%s+@$`, so `task @#Ideas` falls through to `bob capture` as literal text and lands in inbox as a task.
- The picker finalization path currently calls `bob capture --route <choice> -- <text>`. That is correct for bare
  `task @`, but it cannot preserve a `#Ideas` bullet section marker because `--route` intentionally bypasses automatic
  `@route` parsing.

## Design

Keep the route-less picker marker in Hammerspoon, not in the non-interactive CLI.

Extend the Hammerspoon capture request parser to recognize two trailing, whitespace-separated picker markers after
trimming outer whitespace:

- `@` means "open picker and capture the stripped text as a normal task", unchanged from today.
- `@#<section-prefix>` means "open picker and capture the stripped text as a bullet routed to the chosen note".

Also accept bare `@#`, matching the existing concrete `@note#` behavior, as "open picker and use the first non-`Tasks`
section".

The parser should remain intentionally narrow:

- Match `task @#Ideas` and `task @#`.
- Do not match `task@#Ideas`, `task @ #Ideas`, `task @cash#Ideas`, or `task @#Ideas extra`.
- Preserve section-prefix case exactly, because the Rust parser already preserves the prefix and compares headings
  case-insensitively.
- If stripping the marker leaves empty text, keep the current empty-input behavior and do nothing.

## Final Capture Strategy

For a bare `@` picker selection, keep the current forced-route call:

```bash
bob capture --format json --route "$route" -- "$text"
```

That preserves the existing rule where selected picker route wins and any user-typed `@tokens` in the body remain
literal.

For an `@#...` picker selection, do not use `--route`. Instead synthesize a concrete Bob route token using the chosen
route from `bob capture-targets` and run the normal parser:

```text
@<chosen-route>#<section-prefix> <text>
```

Examples:

- User submits `jot note @#Ideas`, chooses `dev` -> final Bob input is `@dev#Ideas jot note`.
- User submits `jot note @#`, chooses `dev` -> final Bob input is `@dev# jot note`.
- User submits `@cash jot note @#Ideas`, chooses `dev` -> final Bob input is `@dev#Ideas @cash jot note`, so the
  selected picker target still wins and `@cash` stays literal in the captured body.

This reuses the already-tested `bob capture` `@route#section` implementation and avoids adding a new CLI option or an
interactive picker mode to `bob`.

## Files To Change

- `/home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua`
  - Update `parseCaptureRequest()` to return the stripped text, whether the picker was requested, and an optional bullet
    route suffix such as `#Ideas` or `#`.
  - Thread that optional suffix through `startTargetsStage()` and `showTaskCaptureChooser()`.
  - On chooser selection, run the current forced-route finalization for bare `@`, and run a synthesized
    `@route#prefix <text>` finalization for `@#...`.
  - Update comments around the picker trigger and finalization path.

Deployment after source edit:

- Apply the Hammerspoon target with chezmoi so `/home/bryan/.hammerspoon/init.lua` matches the source.

No source changes are expected in `src/native/capture.rs` unless implementation proves the existing concrete
`@route#section` path cannot support the synthesized input. Based on inspection, it can.

## Verification

Static checks:

```bash
luac -p /home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua
git -C /home/bryan/.local/share/chezmoi diff -- home/dot_hammerspoon/init.lua
chezmoi --source /home/bryan/.local/share/chezmoi apply ~/.hammerspoon/init.lua
cmp -s /home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua /home/bryan/.hammerspoon/init.lua
```

Scratch-vault CLI smoke for the synthesized final Bob input:

```bash
tmp="$(mktemp -d)"
mkdir -p "$tmp"
printf '## Ideas\n- existing\n' > "$tmp/dev.md"
BOB_DIR="$tmp" BOB_NOW=2026-06-19 bob capture --format json -- '@dev#Ideas jot note'
cat "$tmp/dev.md"
```

Expected result: `dev.md` contains `- jot note [created::2026-06-19]` under `## Ideas`.

Manual GUI smoke after Hammerspoon reload:

- `plain task` captures directly to `mac_inbox.md`, no picker.
- `plain task @` opens the area/project picker and creates a normal task in the chosen note.
- `jot note @#Ideas` opens the same picker and creates a bullet under the chosen note's matching `Ideas` section.
- `jot note @#` opens the same picker and creates a bullet in the first non-`Tasks` section.
- `jot note @cash#Ideas` bypasses the picker and still uses Bob's explicit concrete route syntax.
- `@cash jot note @#Ideas`, choosing `dev`, routes to `dev.md` and captures `@cash jot note` as the bullet body.
- Escape from the picker keeps the original prompt focused with the typed marker intact.

## Risks

- A loose Lua pattern could make ordinary text trigger the picker accidentally. Mitigation: require the picker marker to
  be the final whitespace-separated token.
- Using `--route` for `@#...` would drop the bullet section behavior. Mitigation: synthesize a concrete leading
  `@route#...` token and let Bob's existing parser own the capture semantics.
- A body that starts with an explicit `@route` could steal routing if the synthesized token were appended. Mitigation:
  put the synthesized route token first so the selected picker route wins by Bob's existing "leading route wins" rule.
- Chezmoi source and live Hammerspoon config can drift. Mitigation: edit source, apply only the Hammerspoon target, then
  compare source and live files.
