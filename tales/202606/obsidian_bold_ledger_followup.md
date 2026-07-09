---
title: Obsidian Bold Ledger Follow-Up Plan
create_time: 2026-06-02 12:26:50
status: done
prompt: sdd/prompts/202606/obsidian_bold_ledger_followup.md
---

# Goal

Finish the Obsidian-side follow-through for bold Pomodoro ledger ranges. Confirm that every Obsidian keymap surface
still points at the correct command/template after the bold-range change, update future daily-note generation, and
migrate today's daily Pomodoro ranges to the canonical bold clock atom without disturbing unrelated vault edits.

Canonical Pomodoro ledger range:

```markdown
(**HHMM-HHMM** [t:: Nm])
```

The bolding applies only to the clock range, not the parentheses, duration field, or task text.

# Context Reviewed

- Project short memory says this is an ephemeral `bob-cli_<N>` workspace.
- Obsidian long memory was read through the audited command:
  `sase memory read long/obsidian.md --reason "Need Obsidian vault layout, daily note, template, plugin, and keymap context before planning updates for Pomodoro bold ledger ranges"`.
- `/home/bryan/bob` is the Obsidian vault.
- Vault `AGENTS.md` requires:
  - inspect `git status` before editing;
  - preserve unrelated pre-existing changes;
  - stage and commit only files changed for this task;
  - commit vault changes with `/sase_git_commit` before finishing.
- Current vault status already has dirty notes, including `/home/bryan/bob/2026/20260602_day.md`. Those edits must be
  treated as user/sync changes and preserved.
- The prior vault commit `572fb55 feat: bold Pomodoro ledger ranges` changed only:
  - `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`;
  - `/home/bryan/bob/_templates/schedule.md`.
- The prior work updated the schedule Templater snippet and Bob ledger plugin parsing/formatting, but did not update:
  - `/home/bryan/bob/_templates/daily.md`;
  - existing Pomodoro entries in today's daily note;
  - any Obsidian hotkey JSON/config files.

# Files And Keymap Surfaces To Audit

Audit these before making implementation edits:

- `/home/bryan/bob/.obsidian/hotkeys.json`
  - Current relevant hotkey: `templater-obsidian:_templates/schedule.md` mapped to `Alt+P`.
  - Confirm no stale command ID/path exists for an old schedule template name.
  - Decide whether `bob-ledger-tools:expand-ledger-time-range-snippet` needs an explicit global hotkey entry or should
    remain covered by the plugin's editor-local `Tab` keymap.

- `/home/bryan/bob/.obsidian/plugins/templater-obsidian/data.json`
  - Current relevant registry: `enabled_templates_hotkeys` includes `_templates/schedule.md`.
  - Confirm the schedule template remains enabled for the `Alt+P` hotkey.
  - Keep the existing file shape unless the template path is missing or stale.

- `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`
  - Editor-local CodeMirror keymap: `Tab` expands Bob snippets.
  - Vim mappings: `\\`, `\p`, `\P`, `\o`, `\O`.
  - These mappings likely do not need command/key changes because the command surfaces did not change, but verification
    should prove each mapped behavior now generates or rewrites bold ranges.

- `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
  - Confirm this is unrelated navigation behavior and do not edit unless the audit finds a direct Pomodoro/keymap
    dependency.

# Implementation Plan

1. Re-check vault status immediately before editing.
   - Record the dirty baseline.
   - Treat the existing dirty notes as user/sync edits.

2. Audit keymap/config consistency.
   - Validate `.obsidian/hotkeys.json` contains the expected `templater-obsidian:_templates/schedule.md` hotkey.
   - Validate Templater `enabled_templates_hotkeys` contains `_templates/schedule.md`.
   - Search `.obsidian` for stale references to old Pomodoro template paths, old command IDs, unbolded schedule
     examples, or duplicate keymap entries.
   - If the audit finds keymap/config drift, patch only the affected JSON entries.
   - If the audit shows the keymaps are already correct, leave those files unchanged and report that explicitly.

3. Update the daily template for future notes.
   - Change the Pomodoro starter line in `/home/bryan/bob/_templates/daily.md` from a bare blank task to a neutral
     placeholder task: `- [ ] () `
   - Rationale: the Bob ledger plugin already recognizes `()` placeholders and can replace `(se<Tab>)` with the
     canonical bold range. This makes new daily notes ready for the bold-range workflow without inserting a fake
     timestamp at note creation.
   - Leave the Pomodoros Dataview duration heading unchanged.

4. Update today's daily note carefully.
   - In `/home/bryan/bob/2026/20260602_day.md`, migrate only Pomodoro range atoms from `(HHMM-HHMM [t:: Nm])` to
     `(**HHMM-HHMM** [t:: Nm])`.
   - Preserve checkbox status, task text, wiki links, embeds, the heading query, and every other line.
   - Ensure the file ends with a newline if editing touches the final line.

5. Verify plugin/keymap behavior.
   - Run syntax checks:
     - `node -c /home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`
     - `jq '.' /home/bryan/bob/.obsidian/hotkeys.json`
     - `jq '.' /home/bryan/bob/.obsidian/plugins/templater-obsidian/data.json`
     - `jq '.' /home/bryan/bob/.obsidian/daily-notes.json`
   - Run focused Node helper assertions with stubbed Obsidian/CodeMirror modules to verify:
     - `se<Tab>` still expands through the plugin's Tab path to `(**HHMM-HHMM** [t:: Nm])`;
     - placeholder expansion works for `(se<Tab>)`;
     - `parseTimeRange` accepts today's migrated bold lines;
     - `changePomodoroLineUnits` represents the `\p`/`\P` mappings and keeps output bold;
     - `offsetPomodoroLineRange` represents the `\o`/`\O` mappings and keeps output bold;
     - jump target selection still finds the active or latest completed Pomodoro line after migration.

6. Verify template and daily-note content.
   - Search the relevant files for old unbolded Pomodoro range atoms:
     - `/home/bryan/bob/_templates/daily.md`
     - `/home/bryan/bob/_templates/schedule.md`
     - `/home/bryan/bob/2026/20260602_day.md`
     - `/home/bryan/bob/.obsidian/plugins/bob-ledger-tools/main.js`
   - Confirm today's Pomodoro entries use bold clock ranges.
   - Confirm `_templates/daily.md` contains the placeholder starter line and `_templates/schedule.md` still emits bold
     ranges.

7. Commit vault changes if implementation edits were made.
   - Stage and commit only task-related files with `/sase_git_commit`.
   - Likely files:
     - `/home/bryan/bob/_templates/daily.md`
     - `/home/bryan/bob/2026/20260602_day.md`
     - plus `.obsidian/hotkeys.json` or Templater data only if the keymap audit requires edits.
   - Leave unrelated dirty notes untouched.

# Expected Outcome

- All Obsidian keymap surfaces are either confirmed current or patched where stale.
- Future daily notes start with a Pomodoro placeholder compatible with the bold-range snippet workflow.
- Today's Pomodoro entries use `(**HHMM-HHMM** [t:: Nm])`.
- Schedule template and plugin behavior remain aligned with the prior bold ledger change.
- Vault changes are committed in an isolated commit if any implementation files are changed.

# Risks And Mitigations

- Risk: today's daily note is already dirty and may contain user/sync edits.
  - Mitigation: edit only the Pomodoro range atoms, preserve all surrounding text, and inspect the diff before commit.

- Risk: adding a global hotkey for the Bob ledger plugin could create duplicate behavior with the editor-local `Tab`
  keymap.
  - Mitigation: do not add a new global hotkey unless audit shows an actual stale or missing required keymap; report "no
    keymap file change needed" when existing mappings are correct.

- Risk: the daily template placeholder `()` changes future-note ergonomics.
  - Mitigation: use the existing plugin-supported placeholder rather than generating a timestamp during template
    creation.
