---
create_time: 2026-06-02
status: research
topic: Relative line numbers in Obsidian (vim-style)
---
# Research: Relative Line Numbers in Obsidian

## Question

Bob's Obsidian vault runs in Vim mode and would benefit from Vim-style **relative line
numbers** (the cursor line shows its absolute number; every other line shows its distance
from the cursor) so that motions like `13k` / `5j` are easy to aim. What is possible, and
what should we adopt?

## Current Vault State (observed)

From `/home/bryan/bob/.obsidian/`:

- `app.json` → `"vimMode": true`, `"showLineNumber": true`. So Vim mode is on and the
  **absolute** line-number gutter is already enabled.
- `community-plugins.json` enables: `dataview`, `obsidian-tasks-plugin`,
  `templater-obsidian`, `quickadd`, `task-status-cycler`, `mrj-jump-to-link`,
  `bob-navigation-hotkeys`, `bob-ledger-tools`.
- We already **author and ship custom CodeMirror 6 plugins** in this vault. Per
  `sdd/tales/202606/bold_ledger_time_ranges.md`, `bob-ledger-tools/main.js` already
  imports `@codemirror/state` and `@codemirror/view`, so a CM6 gutter extension is well
  within our existing tooling.
- No relative-line-number plugin and no `obsidian-vimrc-support` are currently installed.

## Key Findings

### 1. There is no native Obsidian setting for relative line numbers

Obsidian's only built-in option is the binary "Show line number" toggle (absolute only).
Relative numbering has been an open community feature request since the early forum days
(thread #621) and is still **not** built in as of mid-2026. Everything below is either a
community plugin or a DIY CodeMirror 6 extension.

### 2. The vimrc / `:set relativenumber` route does NOT work

A natural guess is to install `esm7/obsidian-vimrc-support` and add `set relativenumber`.
This does not produce relative numbers in Obsidian: the line-number **gutter is rendered by
Obsidian itself** (its own CM6 gutter), not by the embedded `codemirror-vim` addon, so the
vim option has nothing to drive. The vimrc plugin is great for remaps and `set` options
that codemirror-vim actually honors, but relative numbering is not one of them. A dedicated
gutter plugin is required.

### 3. Community plugin options

| Plugin | Editor / CM | Last release | Store | Notes |
| --- | --- | --- | --- | --- |
| **nadavspi/obsidian-relative-line-numbers** | Live Preview (CM6) + legacy; needs "Show line number" ON | 3.1.0, Dec 2023 (~105k downloads, 216★) | Yes (canonical) | Most popular and widely referenced, but stale; has open compatibility issues (see below). |
| **hezeao/obsidian-relativenumber** | CM6 / current Obsidian; needs "Show line number" ON | v3.141, Mar 2025 | Status unclear (GitHub release; may need manual/BRAT install) | Active fork of nadavspi. Collapses the dual-column layout into a single column matching Obsidian's native gutter styling and monospace font. Current-Obsidian maintenance. |
| EndlessReform/obsidian-relative-line-numbers | CM6 (uses jsjoeio's `codemirror-line-numbers-relative`) | v1.0.0, Feb 2022 | Unknown | Early CM6 experiment; effectively superseded. Author defers to nadavspi for legacy. |
| thisdotrob/obsidian-relativenumber-plugin | Live Preview + legacy | v1.0.0, Feb 2022 (13★) | Unknown | Requires "Show line numbers" **disabled**; stale, few commits, open issues. |

**Health of the canonical nadavspi plugin.** Despite its popularity, the open-issue list
shows real friction on modern Obsidian:

- `#32` (May 2025) relative numbers appear oddly inside Live-Preview tables.
- `#34` (Jun 2025) heading folding breaks line-number display.
- `#33` (May 2025) gutter column alignment problems.
- `#28` (Oct 2024) relative numbers "freeze" during a vim **visual line** selection.
- `#21` (Nov 2023) misbehaves with the 1.5.0 markdown table editor.
- `#20` (Aug 2023) standing request for "smart" numbers: relative in Normal mode, absolute
  in Insert mode — i.e. the genuinely Vim-correct behavior, not implemented.

The basic feature still works for everyday editing; the issues bite around folding, tables,
and visual mode. The hezeao fork addresses the layout/styling complaints and is more
recently maintained.

### 4. DIY: a small CM6 gutter extension (best fit for our setup)

Because we already ship CM6 plugins (`bob-ledger-tools`, `bob-navigation-hotkeys`),
relative numbering is a modest, fully-controllable addition. CodeMirror 6 exposes a
`lineNumbers({ formatNumber })` gutter; combined with an `EditorView.updateListener` (or a
`StateField` tracking the cursor line) the formatter returns `0`/absolute for the cursor
line and the `Math.abs(line - cursorLine)` distance elsewhere. Registering it via the
Obsidian plugin's `registerEditorExtension(...)` makes it apply everywhere.

This path is more work than a one-click install, but it:

- removes any dependency on a stale community plugin and its open bugs;
- lets us implement the **"smart" Normal-vs-Insert behavior** (read the vim mode off
  `cm.cm?.state.vim` / the `vim-mode-change` event) that no community plugin does well;
- keeps styling consistent with our existing gutter and folds cleanly into a plugin we
  already maintain and test (`node -c main.js`, stubbed-module helper checks).

## Trade-offs

- **Install canonical (nadavspi):** zero effort, one-click from the store, most battle-
  tested for plain editing — but stale and buggy around folds/tables/visual mode, no smart
  mode.
- **Install active fork (hezeao):** current, cleaner native-matching single-column gutter,
  better maintenance — but may not be in the official store (BRAT or manual install), so it
  sits slightly outside the normal update flow.
- **DIY CM6 extension:** most control, no third-party rot, unlocks smart Normal/Insert mode
  and exact styling — but it's code we own, write, and maintain, and we'd track Obsidian/CM6
  API drift ourselves.

## Recommended Solution

**Adopt in two steps:**

1. **Start now with the active community plugin — `hezeao/obsidian-relativenumber`.** Keep
   `"showLineNumber": true` (it builds on the existing gutter), install the plugin, add it
   to `community-plugins.json`, and confirm the cursor line shows absolute while neighbors
   show distance. It is the most current option, matches Obsidian's native gutter styling,
   and avoids the layout/staleness problems of the canonical nadavspi build. If you would
   rather stay strictly inside the official community store, install **nadavspi** instead
   and simply accept the known fold/table rough edges.

2. **If the "smart" behavior or any of the fold/table/visual-mode bugs bother you, fold a
   ~40-line CM6 relative-line-number gutter into our own plugin** (a small new plugin, or an
   extension registered from `bob-ledger-tools`). This is squarely within the CM6 tooling we
   already use, eliminates the third-party dependency, and is the only route that delivers
   true Vim semantics: relative numbers in Normal/Visual mode, absolute in Insert mode.

Net: install the hezeao fork today for an immediate win; graduate to a small owned CM6
extension if we want Vim-exact "smart" numbers or hit the community plugins' folding/table
limitations.

## Sources

- [nadavspi/obsidian-relative-line-numbers (GitHub)](https://github.com/nadavspi/obsidian-relative-line-numbers)
- [nadavspi plugin README](https://github.com/nadavspi/obsidian-relative-line-numbers/blob/main/README.md)
- [nadavspi open issues](https://github.com/nadavspi/obsidian-relative-line-numbers/issues)
- [Relative Line Numbers on Obsidian Stats](https://www.obsidianstats.com/plugins/obsidian-relative-line-numbers)
- [hezeao/obsidian-relativenumber (active fork, GitHub)](https://github.com/hezeao/obsidian-relativenumber)
- [EndlessReform/obsidian-relative-line-numbers (CM6 experiment)](https://github.com/EndlessReform/obsidian-relative-line-numbers)
- [thisdotrob/obsidian-relativenumber-plugin](https://github.com/thisdotrob/obsidian-relativenumber-plugin)
- [esm7/obsidian-vimrc-support](https://github.com/esm7/obsidian-vimrc-support)
- [Obsidian forum feature request: Relative line numbers (#621)](https://forum.obsidian.md/t/relative-line-numbers/621)
