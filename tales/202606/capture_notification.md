---
create_time: 2026-06-19 21:35:12
status: wip
prompt: sdd/prompts/202606/capture_notification.md
---
# Plan: Beautiful macOS notifications for the `bob capture` keymap

## Goal

When the `⌃⇧⌘I` Hammerspoon keymap captures a task/note to the Obsidian vault (`~/bob/`) via `bob capture`, present a
**beautiful, informative, and concise** native macOS notification that confirms success or clearly reports failure.

## Key finding (scope correction)

The keymap **already** sends notifications today — they are just minimal and have real gaps. So this is a _redesign_,
not a from-scratch addition. Current state in `dot_hammerspoon/init.lua`:

- Success: `hs.notify.show("Captured task", routeLabel, body)` (line 449)
- Capture failure: `hs.notify.show("Task capture failed", "", detail)` (line 337)
- Picker failure: `hs.notify.show("Task target picker failed", "", detail)` (line 343)

Problems with the current notifications:

1. **Blank subtitle for the most common case.** For an inbox capture the CLI returns `route_label = ""` (it only fills
   `relative_target = "mac_inbox.md"`), so the subtitle is _empty_ whenever you capture to the inbox — i.e. almost
   always.
2. **Unfriendly destination labels.** When routed it shows a raw filename like `groceries.md` rather than a human label.
3. **No destination context** distinguishing inbox vs. an area/project.
4. **Not actionable.** Clicking the banner does nothing; there's no jump-to-note.
5. **No visual identity** tying the banner to Obsidian; long task text isn't trimmed.

## Design principles

- **Concise first.** A glanceable banner: a clear title, a one-line destination, and the captured text trimmed to a sane
  length.
- **Honest + informative.** Always say _where_ it went ("Inbox" / the note name) and, on failure, _why_ in one line.
- **Calm, not noisy.** Success is silent (rapid capture shouldn't beep); failure gets a subtle alert sound because it
  needs attention.
- **Actionable.** Clicking a success banner opens the captured note in Obsidian.
- **Native + tasteful.** Standard `hs.notify` banner, with the Obsidian app icon as the content image so the banner
  reads as "this landed in Obsidian."

## Architecture decision: keep notifications in Hammerspoon (no CLI change)

The notification stays in the Hammerspoon layer and `bob capture` is **not** modified.

- `bob` is a cross-platform Rust CLI used well beyond this Mac keymap; baking `osascript`/macOS-notification behavior
  into it would be the wrong layer (its only existing notifier, `bob notify`, is Linux `notify-send` for Pomodoro).
- The capture command already emits everything we need as JSON (`bob capture --format json`), which the keymap already
  decodes.

So all changes live in **`~/.local/share/chezmoi/home/dot_hammerspoon/init.lua`** (the chezmoi source for
`~/.hammerspoon/init.lua`).

## Data available to drive the banner

From `bob capture --format json` on success:

| Field                                            | Use                               |
| ------------------------------------------------ | --------------------------------- |
| `ok`                                             | success gate (already checked)    |
| `routed` (bool), `route` (string\|null)          | inbox vs. routed destination      |
| `route_label` (`"groceries.md"`, `""` for inbox) | fallback destination label        |
| `text`                                           | the captured body (banner detail) |
| `kind` (`"task"` \| `"bullet"`)                  | task vs. note wording             |
| `placement` (`created`/`inserted`/`appended`)    | optional nuance ("new note")      |
| `target` (absolute path)                         | click-to-open deep link           |

On failure: `{ ok: false, error: "<msg>" }`, plus stderr/exit code (already handled by the existing
`captureFailureDetail` helper).

For picker-driven captures we additionally know the chosen target's **display name** (`choice.text`) and **kind**
(`choice.kind`, area/project) in the chooser callback — we can thread these through so routed banners show the real
area/project name.

## The redesign

### Success banner

```
┌─────────────────────────────────────────────┐
│ ✓ Task captured                       [icon] │   title
│ Inbox                                         │   subtitle = destination
│ Pick up dry cleaning before 5pm               │   body = captured text (trimmed)
└─────────────────────────────────────────────┘
```

- **Title:** `✓ Task captured` for `kind == "task"`, `✓ Note captured` for `kind == "bullet"`.
- **Subtitle (destination):** a friendly label —
  - `routed == false` → `Inbox`
  - picker-driven → the chosen display name, optionally with kind, e.g. `Cash · Area` / `Q3 Planning · Project`
  - typed `@route` → prettified route (`route_label` minus `.md`, `mac_inbox` → `Inbox`).
- **Body:** `decoded.text`, trimmed to ~100 chars with an ellipsis for long input.
- **Content image:** the Obsidian app icon (`hs.image.imageFromAppBundle("md.obsidian")`, best-effort; omitted if
  unavailable).
- **Click action:** open the note in Obsidian via `obsidian://open?path=<url-encoded target>` (`hs.urlevent.openURL`).
  Requires switching this call site from `hs.notify.show(...)` to `hs.notify.new(callback, attributes):send()`.
- **Sound:** none (silent banner).
- A brand-new note (`placement == "created"`) can read `New note · <name>` for a small extra signal — optional polish.

### Failure banners

```
┌─────────────────────────────────────────────┐
│ ⚠ Capture failed                             │
│ <concise reason / first line of error>        │
└─────────────────────────────────────────────┘
```

- **Capture failure:** title `⚠ Capture failed`; body = concise error (first line of `captureFailureDetail(...)`,
  trimmed/length-capped).
- **Picker failure:** title `⚠ Capture target picker failed`; same body treatment.
- **Sound:** a subtle default alert so a failure isn't missed.
- **No click action.** The capture prompt already stays open on failure (text isn't lost), so retry is already one
  keystroke away — preserved exactly.

## Implementation overview (high level)

Localized changes in `dot_hammerspoon/init.lua`:

1. **Small presentation helpers** (near the existing `trimCaptureText` / `captureFailureDetail` block):
   - `captureDestinationLabel(decoded, pickedName, pickedKind)` → friendly destination string (handles inbox, picker
     name, typed route; the `mac_inbox`/`.md` cleanup).
   - `truncateForBanner(text, max)` → concise body text.
   - `obsidianOpenUrl(targetPath)` → builds the `obsidian://open?path=…` URL (`hs.http.encodeForQuery`).
   - `notifyCaptureSuccess(decoded, pickedName, pickedKind)` → builds and sends the success banner (title by `kind`,
     content image, click-to-open callback, silent).
   - Upgrade `notifyCaptureFailure` / `notifyTargetPickerFailure` to the new titles/body treatment and the subtle
     failure sound.

2. **Thread the picked target's name/kind** so routed banners show the real name: `showTaskCaptureChooser` →
   `runFinalCapture(text, route, pickedName, pickedKind)`; `runFinalCapture` passes them to `notifyCaptureSuccess`.
   Inbox/typed paths pass `nil` and fall back to label derivation. (The `@#section` bullet path can pass the picked name
   too.)

3. **Swap the success call site** from `hs.notify.show(...)` to the new `notifyCaptureSuccess(...)`, keeping the
   existing success gate (`exitCode == 0 and decoded.ok == true`) and the close-prompt-on-success behavior.

**Preserved invariants:** the live-task guard (`taskCaptureTask ~= task`), prompt stays open on failure, picker failures
surface explicitly (no silent inbox fallback), unchanged `bob` invocation and JSON contract.

## Edge cases

- **Inbox capture** (`routed == false`, empty `route_label`) → subtitle `Inbox` (fixes today's blank subtitle).
- **Missing/odd fields** → helpers default safely (empty text → no body; unknown kind → generic "Captured").
- **Obsidian not installed / app-icon lookup fails** → skip content image; click still attempts the URL (no crash).
- **Very long task text** → trimmed with ellipsis.
- **`md.obsidian` bundle id** assumed for the icon and is best-effort; verify on the Mac and adjust if the install uses
  a different id (icon is cosmetic only).

## Verification

This repo runs on Linux; Hammerspoon runs on the Mac, so verification is partly manual:

1. **Lua sanity:** `luac -p` / `luacheck` on the source if available (syntax only).
2. **Apply + reload on Mac:** `chezmoi apply` then reload Hammerspoon (auto-reload on save, or `hs.reload()`).
3. **Manual matrix** via `⌃⇧⌘I`:
   - Inbox capture → `✓ Task captured` / `Inbox` / text; click opens the note.
   - `@`-picker → pick an area and a project → real name + kind shown.
   - `@#section` bullet → `✓ Note captured`.
   - Force a failure (e.g. temporarily break `PATH`/route) → `⚠ Capture failed` with a concise reason and the prompt
     still open.

## Files touched

- `~/.local/share/chezmoi/home/dot_hammerspoon/init.lua` (chezmoi source for `~/.hammerspoon/init.lua`) — **only file
  changed**.
- No changes to the `bob-cli` Rust code.

## Open design choices (defaults chosen; easy to flip)

I've led with these defaults; call out if you'd prefer otherwise:

1. **Click-to-open in Obsidian** on success — _default: on_.
2. **Sound:** success silent, failure subtle alert — _default as stated_.
3. **Obsidian icon as content image** — _default: on, best-effort_.
4. **Destination label style:** `Cash · Area` / `Q3 Planning · Project` / `Inbox`; prettify route by stripping `.md` and
   `mac_inbox` → `Inbox` — _default as stated_.
5. **`New note` hint** when `placement == "created"` — _default: on_.
