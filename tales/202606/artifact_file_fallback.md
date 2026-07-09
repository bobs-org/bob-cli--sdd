---
create_time: 2026-06-03 08:12:28
status: wip
prompt: sdd/prompts/202606/artifact_file_fallback.md
---
# Plan: SASE Artifact Viewer Raw-File Fallback

## Objective

Make SASE agent artifacts viewable regardless of artifact file type. Today the artifact terminal viewer only accepts
image, PDF, and Markdown modes; unknown file/kind pairs return `unsupported_artifact_kind` and the tmux artifact pane
surfaces "Unsupported artifact type". The desired behavior is that unsupported/fallback artifacts open in the artifact
tmux panel with `bat` when available, or `cat` otherwise, while preserving the existing artifact picker `y` and `Y`
keymaps.

The implementation target is the editable SASE repo at `/home/bryan/projects/github/sase-org/sase`, not this `bob-cli`
checkout. I inspected the target repo instructions and read `long/tui_jk_baseline.md` via `sase memory read` because the
change touches ACE TUI behavior. This is presentation/TUI glue; it does not require a Rust core backend change and does
not add CLI subcommands or options.

## Current Behavior

- `src/sase/ace/tui/graphics/_viewer_render.py`
  - `artifact_view_mode()` returns only `image`, `pdf`, `markdown`, or `None`.
  - `render_artifact_pages()` returns `unsupported_artifact_kind` when mode is `None`.
- `src/sase/ace/tui/graphics/_viewer_loop.py`
  - The sequence loop assumes every artifact can become one or more image pages rendered through `kitten icat`.
- `src/sase/ace/tui/graphics/_viewer_tmux.py`
  - The tmux pane launches `python -m sase.ace.tui.graphics.viewer ...`; the unsupported-kind failure happens inside
    that child viewer process.
- `src/sase/ace/tui/modals/agent_artifacts_modal.py`
  - `y` is already a modal keymap for copying highlighted Markdown contents.
  - `Y` is already a modal keymap for copying the highlighted artifact display path.
  - `y` is intentionally excluded from selector letters so the copy key remains usable.

## Design

1. Add a raw-file display path alongside the existing rendered-page path.
   - Keep the image/PDF/Markdown render flow unchanged.
   - Add a small viewer-strategy helper that classifies an artifact as either page-rendered or raw-file fallback.
   - Unknown kinds/suffixes should choose the raw-file fallback instead of surfacing `unsupported_artifact_kind` from
     the user-facing viewer flow.
   - Preserve direct render-helper semantics where they are specifically about producing image pages; the sequence
     viewer should own the fallback decision.

2. Implement a raw-file viewer command helper.
   - Prefer `bat` when `shutil.which("bat")` is non-None.
   - Fall back to `cat` when `bat` is unavailable.
   - Return a structured warning only if no usable fallback command exists or the command exits non-zero.
   - Run the command from the Python viewer process rather than replacing the process. This keeps the artifact pane
     alive after `cat` prints and preserves existing pane tracking, close-signal cleanup, and `q` close behavior.
   - Use shell-free subprocess argument lists with the artifact path as one argument.

3. Integrate fallback files into the artifact sequence loop.
   - When the current artifact is raw fallback:
     - Clear the pane.
     - Print the same artifact header, with artifact position metadata for multi-artifact sequences.
     - Run `bat`/`cat` in the pane.
     - Show a compact prompt for available viewer controls.
   - Keep existing controls where they make sense:
     - `n` / `p` navigate between artifacts.
     - `r` reruns `bat`/`cat`.
     - `<tab>` focuses the SASE TUI if the return pane id is available.
     - `q` clears/exits the artifact viewer.
   - Do not offer image-only controls such as page `j`/`k` or zoom `z` for raw files.
   - For mixed artifact sequences, switching between rendered artifacts and raw files should not leak stale page index
     state.

4. Preserve and clarify `y` / `Y` keymap behavior in the artifact picker.
   - Do not allow selector assignment to steal `y` or `Y`; these remain modal actions.
   - Keep `Y` path-copy usable for all artifact kinds.
   - Extend or adjust `y` only if implementation confirms the current Markdown-only restriction is part of the
     unsupported-file UX being reported. If changed, `y` should copy readable text artifacts with UTF-8 replacement and
     continue to avoid unsafe binary clipboard behavior.
   - Update modal hints/tests only if the behavior changes.

5. Keep documentation surfaces in sync only where behavior is surfaced.
   - No default config keymap changes are expected.
   - No `sase ace` CLI option changes are expected, so the help popup only needs updating if the artifact viewer
     key-hint text changes materially.
   - The artifact pane prompt should mention raw-file controls accurately.

## Test Plan

Add focused tests under `tests/ace/tui/artifact_viewer/`:

- Rendering/strategy tests:
  - Unknown file kinds no longer produce a user-facing unsupported viewer failure.
  - Existing image/PDF/Markdown mode classification remains unchanged.
  - Missing files still report `artifact_not_found`, not a raw fallback command failure.

- Raw command tests:
  - `bat` is preferred when available.
  - `cat` is used when `bat` is unavailable.
  - Non-zero fallback command exits return a structured warning.

- Sequence-loop tests:
  - A raw artifact runs the fallback command and stays in the viewer until `q`.
  - Raw `r` reruns the fallback command.
  - Mixed raw/rendered artifacts support `n`/`p` navigation.
  - `<tab>` still focuses the SASE TUI from a raw artifact pane when return-pane tracking is available.

- Tmux launch tests:
  - The tmux pane still launches the module entry point with the original artifact path/kind.
  - A raw artifact launched through the module does not fail with `unsupported_artifact_kind`.

- Modal keymap tests if touched:
  - `Y` continues copying paths for non-Markdown/fallback artifacts.
  - `y` behavior is explicitly covered for `.txt`/`.json` artifacts if broadened.
  - Selector keys still reserve `y` so the keymap remains usable.

## Verification

After implementation in `/home/bryan/projects/github/sase-org/sase`:

1. `just install`
2. Targeted pytest first, for example:
   - `pytest tests/ace/tui/artifact_viewer/test_rendering.py tests/ace/tui/artifact_viewer/test_sequence_loop.py tests/ace/tui/artifact_viewer/test_tmux.py`
   - plus `tests/ace/tui/modals/test_agent_artifacts_modal_copy.py` if modal keymap behavior changes.
3. `just check` before final response, because the SASE repo instructions require it after file changes.

## Risks And Mitigations

- `cat` can emit binary bytes. The user specifically requested `cat` fallback, so the implementation should not reject
  binary-looking files just because they are unsupported. Keep the subprocess direct and let the user close the pane
  with `q` after output returns.
- `bat` may invoke a pager. That is acceptable in the artifact pane; after the pager exits, the SASE viewer prompt
  should remain available.
- Raw files do not have page navigation. The prompt should only show controls that actually work for the current
  artifact.
- Avoid broad TUI repaint changes. This work is not on the j/k hot path, and the sequence-loop changes should stay local
  to artifact viewer process behavior.
