---
create_time: 2026-06-07 09:14:41
status: done
---
# Rename Bob Daily Notes to Bare Date Paths

## Goal

Move Bob daily notes from `~/bob/YYYY/YYYYMMDD_day.md` to `~/bob/YYYY/YYYYMMDD.md`, and update the note-creation,
navigation, editor, and CLI surfaces that still assume the `_day` suffix. The migration should preserve existing note
content and backlinks, avoid clobbering unrelated dirty vault state, and leave historical `_poms.md` / `_habit.md`
archives intact unless a later task explicitly retires them.

## Current Findings

- The audited Obsidian memory says `~/bob` is the Bob Obsidian vault and new Markdown notes need a `parent` field.
- The live Daily Notes config is `/home/bryan/bob/.obsidian/daily-notes.json` with `format: "YYYY/YYYYMMDD[_day]"` and
  template `_templates/daily`.
- `/home/bryan/bob/_templates/daily.md` still parses `tp.file.title` as `YYYYMMDD[_day]`, emits `_day` prev/next links,
  and uses that same suffix-aware format in the Tasks scheduled-date filter.
- Bob Ledger Tools falls back to `DEFAULT_DAILY_NOTES_FORMAT = "YYYY/YYYYMMDD[_day]"`.
- Bob Navigation Hotkeys recognizes new daily-note paths with `YYYY/YYYYMMDD_day.md`.
- `bob-cli` native and script Pomodoro defaults point at `YYYY/YYYYMMDD_day.md`, and their day-date parsers only accept
  `_day.md`.
- Neovim Bob config has a daily-note helper that formats `YYYY/YYYYMMDD_day.md`; its tests assert that path.
- Vault inventory from this planning pass:
  - 794 files match `YYYY/YYYYMMDD_day.md`;
  - 874 files already match `YYYY/YYYYMMDD.md`;
  - 637 daily-note rename targets already exist, mostly generated legacy "all journal / log files from DATE" hub notes;
  - 157 daily-note rename targets do not currently exist;
  - 188 historical `_poms.md` files and 826 historical `_habit.md` files still exist.
- Current June 2026 daily notes are `20260601_day.md` through `20260607_day.md`; none currently have bare `202606DD.md`
  collisions.
- The vault is already dirty. Relevant dirty files are `_templates/daily.md` and `2026/20260607_day.md`; many unrelated
  vault files are also dirty and must not be reverted or staged as part of this task.

## Migration Policy

1. The canonical daily-note path after this task is `YYYY/YYYYMMDD.md`.
2. Existing daily notes should become the canonical bare date notes.
3. Existing bare date hub notes are not canonical daily notes. For collision cases, classify them before changing them:
   - If a target bare note is a generated all-day-log hub with no manual content, replace it with the daily note.
   - If a target bare note contains manual/non-generated content or is dirty, stop for review or merge the non-redundant
     content explicitly rather than overwriting it.
4. Do not rename, delete, or otherwise migrate historical `_poms.md` / `_habit.md` files in this task. Update links that
   point to renamed daily notes so those archives keep valid references.
5. Do not rewrite `zorg_source`, `zorg_source_abs`, or other source-provenance strings that name historical `.zo` files.
   Only rewrite actual Obsidian links and daily-note metadata that should track the new Markdown path.

## Implementation Plan

1. Re-audit immediately before implementation.
   - Run `git -C /home/bryan/bob status --short`.
   - Recount daily, bare, `_poms`, and `_habit` files.
   - Recompute the collision list from every `YYYY/YYYYMMDD_day.md` to `YYYY/YYYYMMDD.md`.
   - Save the collision/no-collision audit output under the bob-cli workspace or `/tmp` for review during the run.

2. Add a focused migration helper.
   - Prefer a small Python helper under `sdd/tools/` in this repo for deterministic inventory, collision classification,
     link rewriting, and validation.
   - Make it support a dry-run/audit mode and an apply mode.
   - Keep the rewrite rules targeted:
     - rename `YYYY/YYYYMMDD_day.md` files to `YYYY/YYYYMMDD.md`;
     - rewrite wiki links like `[[YYYY/YYYYMMDD_day]]`, `[[YYYY/YYYYMMDD_day#...]]`, `[[YYYY/YYYYMMDD_day|...]]`,
       `![[...]]`, and same-folder `[[YYYYMMDD_day]]` references;
     - update daily frontmatter `id: YYYYMMDD_day` to `id: YYYYMMDD`;
     - update daily frontmatter parents that point to the old same-date hub so they point to the nested month note, for
       example `[[2026/202606]]`;
     - update daily prev/next links to bare date targets.

3. Switch future Obsidian daily-note creation.
   - Change `/home/bryan/bob/.obsidian/daily-notes.json` to `format: "YYYY/YYYYMMDD"`.
   - Update `/home/bryan/bob/_templates/daily.md` to parse `YYYYMMDD`, emit bare prev/day/next links, and use
     `moment(query.file.filenameWithoutExtension, "YYYYMMDD")` in Tasks filters.
   - Preserve the existing dirty template improvements already present in the working tree, including `parent`,
     `created`, and `type: "[[day]]"`.

4. Update Obsidian plugin configuration/code.
   - In Bob Ledger Tools, change the default daily-note fallback format to `YYYY/YYYYMMDD` while still relying on the
     configured Daily Notes plugin when present.
   - In Bob Navigation Hotkeys, recognize `YYYY/YYYYMMDD.md` as a daily-note creation path for template selection.
   - Consider accepting legacy `YYYY/YYYYMMDD_day.md` in recognition logic during the transition, but do not generate
     legacy paths.
   - Run syntax checks on changed plugin JavaScript.

5. Update CLI and script integrations.
   - Change native `bob pomodoro` default path generation to `YYYY/YYYYMMDD.md`.
   - Change the shell fallback `scripts/bob_pomodoro` default path similarly.
   - Update both native and shell day-date parsers to accept the new bare filename and, for compatibility with explicit
     `BOB_DAY_FILE`, continue accepting legacy `_day.md`.
   - Update README documentation for the default path.
   - Add or adjust tests so native and script fallbacks prove they read the new default daily file when `BOB_DIR` and
     `BOB_NOW` are set.

6. Update editor integration configuration.
   - Update Neovim's Bob daily-note helper to return `YYYY/YYYYMMDD.md`.
   - Keep non-daily helpers such as done/habit paths unchanged unless this task is expanded.
   - Update Neovim tests that assert daily paths.

7. Apply the vault migration carefully.
   - For collision-free daily notes, use path-preserving renames from `_day.md` to bare `.md`.
   - For generated bare hub collisions, remove the generated hub and move the daily note into its bare path.
   - For non-generated or dirty collisions, pause and resolve explicitly rather than overwriting.
   - Preserve ongoing edits in `2026/20260607_day.md` by transforming the current file content, then renaming it to
     `2026/20260607.md`.
   - Keep unrelated dirty vault files untouched.

8. Verification.
   - `git -C /home/bryan/bob diff --check` over changed vault paths.
   - `rg -n '\[\[[0-9]{4}/[0-9]{8}_day(?:[#|\]])|\[\[[0-9]{8}_day(?:[#|\]])' /home/bryan/bob` should find no remaining
     Obsidian links to renamed daily notes, excluding intentionally historical prose only if explicitly justified.
   - `find /home/bryan/bob -maxdepth 2 -regex '.*/[0-9]{4}/[0-9]{8}_day\.md'` should return no canonical daily-note
     files after the full migration.
   - Confirm `/home/bryan/bob/.obsidian/daily-notes.json` has `YYYY/YYYYMMDD`.
   - Confirm today's daily note path is `2026/20260607.md` and contains the current dirty Pomodoro/task content.
   - Run `cargo fmt --check`, `cargo test`, and the relevant script checks for bob-cli.
   - Run available Neovim Bob keymap tests if the local test runner is available.
   - Run `node --check` on changed Obsidian plugin JavaScript files.

## Risk Management

- The main risk is overwriting existing bare date hub notes. Mitigation: classify collisions first and only replace
  generated hub notes automatically.
- Obsidian Sync may create or delete daily files while implementation is in progress. Mitigation: re-audit immediately
  before applying changes and avoid long pauses between audit and migration.
- The vault has unrelated dirty state. Mitigation: use explicit path lists for staging and never revert unrelated files.
- Link rewriting is broad because the vault has thousands of daily backlinks. Mitigation: target only Obsidian link
  syntax and verify that no `_day` wiki-link targets remain.
- Historical `_poms.md` and `_habit.md` files remain as archives. Mitigation: update their links to renamed daily notes
  but do not otherwise change them.

## Acceptance Criteria

- New daily notes are created at `~/bob/YYYY/YYYYMMDD.md`.
- Existing daily notes have been migrated from `_day.md` to bare `.md` without losing current daily content.
- Bare generated date hub collisions have been handled intentionally, and no non-generated collision was overwritten
  silently.
- Templates, Obsidian plugin code/config, bob-cli, README, and Neovim daily helpers all agree on the bare daily path.
- Obsidian backlinks to renamed daily notes resolve to the new bare targets.
- Unrelated dirty vault files remain untouched.
