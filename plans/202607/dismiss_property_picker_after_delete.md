---
create_time: 2026-07-10 11:04:01
status: done
prompt: .sase/sdd/prompts/202607/dismiss_property_picker_after_delete.md
tier: tale
---
# Dismiss the Bullet Property Picker After Deletion

## Goal

Make the Obsidian bullet-property workflow opened by `Ctrl+Shift+P` close its picker automatically after `Ctrl+D`
successfully removes the selected property. Preserve the existing inline-property edit, cursor restoration, notice, and
keyboard-event handling, while leaving the picker available when no deletion occurred so the user can recover or choose
another action.

## Context and Root Cause

- The source of truth is the linked `bob-plugins` repository, in `plugins/bob-navigation-hotkeys/main.js`; `bob-cli`
  itself does not implement the picker.
- Obsidian already maps `Ctrl+Shift+P` to `bob-navigation-hotkeys:set-bullet-property`, and the deployed plugin
  currently matches the linked repository, so neither the hotkey configuration nor deployment drift causes the bug.
- `BulletPropertyPickerModal.handleKeydown` correctly reserves `Ctrl+D` for the first (property-selection) stage and
  prevents the event from leaking to Obsidian.
- `deleteSelectedProperty` calls the plugin mutation successfully, but then rebuilds the property-selection stage. That
  refresh is why the modal remains visible after the property has been removed. By contrast, the picker's other
  completed actions use a success result to close the modal.

## Implementation

1. In the `bob-navigation-hotkeys` property picker, make the delete action clearly report whether it completed. Treat
   only a confirmed `deleted: true` result from `deleteBulletPropertyValue` as success.
2. Have the `Ctrl+D` keydown path close the modal when that success result is returned. Remove the now-unnecessary
   successful-delete stage refresh, since no refreshed menu should be displayed after the terminal action.
3. Preserve the current non-success behavior:
   - An undefined selected property shows its existing notice and keeps the picker open.
   - A guarded, stale, or failed editor mutation keeps the picker open for retry or dismissal.
   - `Ctrl+D` remains scoped to the property-selection stage, and its default behavior/propagation remain suppressed.
   - Value selection, local-task dependency stages, `Enter`, and `Escape` retain their existing close semantics.
4. Keep the change limited to modal control flow in `plugins/bob-navigation-hotkeys/main.js`. No hotkey, CSS, README, or
   manifest change is expected for this focused behavior correction.

## Verification and Deployment

1. Run `npm run validate` in the linked `bob-plugins` repository to validate manifests and syntax-check every plugin.
2. Run `bob plugins sync` as required by the repository instructions so the corrected source is deployed to the Bob
   vault.
3. Smoke-test in Obsidian on a bullet with a configured inline property:
   - Open the picker with `Ctrl+Shift+P`, highlight a defined property, press `Ctrl+D`, and confirm the property is
     removed, the existing removal notice appears, and the modal closes without an extra `Escape`.
   - Reopen the picker, highlight an undefined property, press `Ctrl+D`, and confirm the existing not-set notice appears
     while the modal stays open.
   - Confirm `Ctrl+D` does not delete from value/local-task stages and that normal `Enter` and `Escape` behavior is
     unchanged.
4. Confirm the synced vault copy matches the edited plugin source after deployment.

## Expected Files

- Linked `bob-plugins` repository: `plugins/bob-navigation-hotkeys/main.js`
- No `bob-cli` production-code changes.
