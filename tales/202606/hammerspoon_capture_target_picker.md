---
create_time: 2026-06-16 09:44:13
status: done
prompt: sdd/prompts/202606/hammerspoon_capture_target_picker.md
---
# Plan: Hammerspoon Capture Target Picker Integration

## Finding

I did not update the Hammerspoon target picker in the chezmoi repo during the previous implementation. That run shipped
the Bob CLI data side only: `bob capture-targets` was added to the bob-cli repo and committed as `8575053`.

The live failure matches the current Hammerspoon code:

- Chezmoi source: `/home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua`
- Live file: `/home/bryan/.hammerspoon/init.lua`
- Those two files are byte-identical right now.
- The capture panel still runs `exec bob capture --format json -- "$1"` directly.
- There is no `bob capture --dry-run`, no `bob capture-targets`, and no `hs.chooser` target picker in the Hammerspoon
  flow.

There is a second deployment blocker: the checked-out bob-cli repo contains `capture-targets`, but the installed
`/home/bryan/.cargo/bin/bob` does not yet recognize that subcommand. Hammerspoon uses the installed `bob` from PATH, so
the binary must be updated before or along with the Hammerspoon change.

The chezmoi repo also has unrelated dirty work:

- `bin/executable_install_sase_github`
- `../tests/bash/install_sase_github_test.sh` from git status
- additional chezmoi status drift outside Hammerspoon

The implementation must leave those unrelated changes alone.

One naming detail to preserve unless Bryan explicitly asks otherwise: the file currently binds the prompt to
`{ "cmd", "shift", "ctrl" }, "i"` even though the reported physical keymap is `<ctrl+shift+alt+i>`. This plan changes
the capture behavior behind the existing binding, not the binding itself.

## Goal

Make the existing Hammerspoon "Capture Task" panel use the new picker contract:

- If submitted text already has an explicit Bob route (`@route` prefix/suffix), capture immediately with today's
  behavior and do not show a picker.
- If submitted text is unrouted, fetch `bob capture-targets --format json` and show a filterable native `hs.chooser`
  picker.
- Keep `mac_inbox` first and default. A bare picker Enter should choose it.
- Choosing `mac_inbox` should run the unrouted capture path, preserving today's append-to-inbox behavior.
- Choosing any other target should run `bob capture --format json --route <route> -- <text>`.
- Dismissing the picker should leave the original prompt open with the typed text intact.

## Scope

Planned implementation files/actions:

- Edit only `/home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua`.
- Apply only the Hammerspoon target with chezmoi after the source edit.
- Reinstall the current bob-cli binary from `/home/bryan/.local/state/sase/workspaces/bbugyi200/bob-cli/bob-cli_11` so
  `/home/bryan/.cargo/bin/bob capture-targets` is available to Hammerspoon.

Out of scope:

- No bob-cli source changes unless verification finds the committed `capture-targets` contract is broken.
- No changes to vault notes, Obsidian hotkeys, memory files, or unrelated chezmoi dirty files.
- No key chord change unless requested separately.

## Implementation Approach

1. Update the installed Bob CLI before relying on the picker.

   Use the current bob-cli checkout, which is at commit `8575053`, and reinstall the binary with the repo's locked
   dependency set:

   ```bash
   cargo install --path /home/bryan/.local/state/sase/workspaces/bbugyi200/bob-cli/bob-cli_11 --locked --force
   ```

   Then verify:

   ```bash
   bob capture-targets --format json
   bob capture --dry-run --format json -- "foo bar baz"
   ```

2. Replace `submitCapturedTask`'s direct write path with a staged async flow.

   Keep the existing webview HTML, focus restore, notification handling, and shell-safety pattern. Continue passing task
   text as a positional shell parameter, never interpolated into the shell script.

   New staged flow:
   - Submit captures a snapshot of the current prompt text.
   - Run `bob capture --dry-run --format json -- "$1"`.
   - Decode JSON and inspect `routed`.
   - If `routed == true`, run the final capture immediately: `bob capture --format json -- "$1"`.
   - If `routed == false`, load picker rows with `bob capture-targets --format json`.
   - If any stage fails, notify and keep the prompt open.

3. Add target picker state.

   Add a `taskCaptureChooser` variable alongside the existing `taskCaptureTask`. Closing/canceling the prompt should
   terminate any running task and close any open chooser. Stale callbacks should keep using the current task-object
   guard so late async responses cannot close or modify a dismissed prompt.

4. Build `hs.chooser` choices from the CLI JSON contract.

   Preserve the order emitted by `bob capture-targets`, because `mac_inbox` is already pinned first by bob-cli.

   Row mapping:
   - `text`: target `name`
   - `subText`: `Inbox - default`, `Area`, or `Project - <status>`
   - `image`: best-effort per-kind Hammerspoon image when available, with the textual `subText` distinction as the
     fallback
   - private fields on each choice: `route`, `kind`, `is_default`

   On chooser selection:
   - no choice: dismiss the chooser and refocus the existing prompt
   - default inbox choice: run final capture without `--route`
   - other choice: run final capture with `--route "$2"`

5. Preserve the existing final-capture JSON handling.

   The final capture callback can keep the current success behavior:
   - require `exitCode == 0`, JSON decode success, and `ok == true`
   - notify `Captured task` with `route_label` and `text`
   - close the prompt only after successful final capture
   - on failure, notify `Task capture failed` with JSON `error`, stderr, stdout, or a fallback message

6. Make missing picker support obvious.

   If `bob capture-targets` is unavailable or returns invalid JSON, show a specific notification such as
   `Task target picker failed` and keep the prompt open. Do not silently fall back to inbox, because that would recreate
   the behavior Bryan just observed.

## Verification

Automated/local checks:

```bash
luac -p /home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua
git -C /home/bryan/.local/share/chezmoi/home diff -- dot_hammerspoon/init.lua
chezmoi --source /home/bryan/.local/share/chezmoi apply ~/.hammerspoon/init.lua
cmp -s /home/bryan/.local/share/chezmoi/home/dot_hammerspoon/init.lua /home/bryan/.hammerspoon/init.lua
bob capture-targets --format json
```

Scratch-vault CLI smoke before trusting Hammerspoon:

```bash
tmp="$(mktemp -d)"
BOB_DIR="$tmp" bob capture --dry-run --format json -- "foo bar baz"
BOB_DIR="$tmp" bob capture-targets --format json
BOB_DIR="$tmp" bob capture --format json --route mac_inbox -- "foo bar baz"
```

Manual GUI smoke after Hammerspoon reloads:

- Press the existing capture hotkey, submit `foo bar baz`, and confirm the target picker appears instead of writing
  immediately.
- Press Enter in the picker without typing and confirm the task lands in `~/bob/mac_inbox.md`.
- Submit another unrouted task, choose a non-inbox area/project, and confirm the task lands in that target note.
- Submit an explicit route such as `@cash foo bar baz` and confirm no picker is shown.
- Dismiss the picker with Escape and confirm the original prompt remains with its text.

## Risks and Mitigations

- Old installed Bob CLI: reinstall and verify `bob capture-targets` before the Hammerspoon change is considered
  complete.
- Silent inbox fallback: treat picker failure as an error notification, not as a successful capture.
- Shell quoting: continue passing text and route as positional parameters.
- Async race/stale callback: keep task-object guards and terminate/clear state on prompt close.
- Hammerspoon API differences: keep image usage best-effort and rely on text and subText for the required visual
  distinction.
- Unrelated chezmoi changes: inspect diffs before and after, and apply only the Hammerspoon target.

## Success Criteria

- The managed Hammerspoon source calls the dry-run and capture-targets contract.
- The live Hammerspoon file matches the managed source after apply.
- `/home/bryan/.cargo/bin/bob capture-targets --format json` works.
- Unrouted captures open a picker before writing.
- `mac_inbox` remains the first/default selection.
- Explicit `@route` captures still bypass the picker.
