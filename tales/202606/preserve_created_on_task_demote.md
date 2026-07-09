---
create_time: 2026-06-14 10:58:10
status: done
prompt: sdd/prompts/202606/preserve_created_on_task_demote.md
---

# Plan: Preserve Created Property When Demoting Obsidian Tasks

## Context

The affected behavior lives in the Bob Obsidian vault plugin:

- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`

The `<Ctrl+Shift+]>` / Vim toggle path now flows through `getObsidianTaskToggleDocumentPlan()`:

- It calls `getObsidianTaskToggle()` to compute the converted first line.
- If the active source line is a routing-eligible top-level dash item and both `Tasks` and `Future Work` sections exist,
  it moves the converted list-item block between sections.
- Otherwise it applies the converted first line in place.

The current demotion path is the source of the bug:

- `getDemoteObsidianTaskLineRewrite()` extracts the task body.
- It calls `collectObsidianTaskTokenRanges(body)`.
- That helper currently marks standalone `#task` plus every property in `OBSIDIAN_TASK_PROPERTY_KEYS` for removal.
- `OBSIDIAN_TASK_PROPERTY_KEYS` includes `created`, so `[created::YYYY-mm-dd]` is stripped before either the replace
  plan or move plan is applied.

Observed current output:

```md
- [ ] #task Follow up [created::2026-06-14] [due::2026-06-20] ^todo
```

currently demotes to:

```md
- Follow up ^todo
```

The requested behavior is:

```md
- Follow up [created::2026-06-14] ^todo
```

This is a conversion rule, not a section-routing rule. The same demotion rewrite is used whether the result stays in
place or moves to `Future Work`, so the fix should live in the demotion token-removal logic and let both document-plan
modes inherit it.

## Goal

When converting a proper Obsidian task into a normal bullet, preserve any existing `[created::...]` inline property.

Keep the rest of the current demotion behavior:

- Remove the checkbox marker.
- Remove standalone `#task`.
- Remove other built-in Obsidian Tasks properties such as `[completion::...]`, `[due::...]`, `[scheduled::...]`,
  `[start::...]`, `[cancelled::...]`, `[priority::...]`, `[repeat::...]`, `[id::...]`, `[dependsOn::...]`, and
  `[onCompletion::...]`.
- Preserve custom inline fields, links, normal text, and trailing block IDs.
- Preserve current promotion behavior, including adding `[created::YYYY-MM-DD]` only when no created field exists.
- Preserve current routing behavior, including the top-level dash eligibility rule.

## Behavior Specification

### Demotion

Examples that should preserve `created`:

```md
- [ ] #task Follow up [created::2026-06-14]
```

becomes:

```md
- Follow up [created::2026-06-14]
```

```md
- [ ] #task Follow up [created:: 2026-06-14] [due::2026-06-20] ^todo
```

becomes:

```md
- Follow up [created:: 2026-06-14] ^todo
```

The preservation rule should apply equally to:

- In-place demotion when routing sections are missing.
- In-place demotion for non-routing-eligible lines, such as indented tasks.
- Move-plan demotion from `Tasks` to `Future Work`.

### Promotion

Promotion should continue to use `lineHasCreatedField()` / `addCreatedFieldToObsidianTaskLine()`:

- A bullet without a created field gets `[created::<today>]`.
- A bullet with an existing `[created::...]` field keeps that field and does not get a duplicate.
- Block IDs remain last.

## Implementation

Edit only:

- `/home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`

Implementation steps:

1. Split "all known task properties" from "properties removed during demotion".
   - Keep `CREATED_FIELD_RE` unchanged for promotion duplicate detection.
   - Replace the current removal regex with a removal-specific list that excludes `created`, for example
     `DEMOTED_OBSIDIAN_TASK_PROPERTY_KEYS` or `REMOVABLE_OBSIDIAN_TASK_PROPERTY_KEYS`.
   - Build the removal regex from that list so `collectObsidianTaskTokenRanges()` still removes non-created task
     properties.

2. Update `collectObsidianTaskTokenRanges(bodyText)` to use the removal-specific property regex.
   - It should still collect standalone `#task`.
   - It should no longer collect `[created::...]`.
   - It should still collect all other task properties already listed above.

3. Leave routing and editor-application code unchanged.
   - `getObsidianTaskToggleDocumentPlan()` already uses `toggle.lineText` as the converted first line for both replace
     and move plans.
   - Once `getDemoteObsidianTaskLineRewrite()` preserves created, both paths should behave correctly without special
     cases in `applyObsidianTaskReplacePlan()` or `applyObsidianTaskMovePlan()`.

4. Keep exports stable unless a new helper is genuinely useful.
   - Existing exported helpers such as `demoteObsidianTaskLine`, `getObsidianTaskToggle`, and
     `getObsidianTaskToggleDocumentPlan` are enough for focused assertions.

## Validation

1. Static checks:
   - `node -c /home/bryan/bob/.obsidian/plugins/task-status-cycler/main.js`
   - `git -C /home/bryan/bob diff --check -- .obsidian/plugins/task-status-cycler/main.js`
   - `git -C /home/bryan/bob status --short -- .obsidian/plugins/task-status-cycler/main.js`

2. Focused Node helper assertions with a mocked `obsidian` module:
   - `demoteObsidianTaskLine("- [ ] #task Follow up [created::2026-06-14]")` returns
     `"- Follow up [created::2026-06-14]"`.
   - Demotion preserves `[created:: 2026-06-14]` spacing inside the property.
   - Demotion preserves `[created::...]` while still removing `[due::...]`, `[scheduled::...]`, `[completion::...]`,
     `[cancelled::...]`, `[repeat::...]`, and standalone `#task`.
   - Demotion keeps trailing block IDs after the preserved created field.
   - Indented task demotion stays in-place through `getObsidianTaskToggleDocumentPlan()` and preserves created.
   - Top-level dash task demotion in a document with `Tasks` and `Future Work` returns a move plan whose moved line
     preserves created.
   - Promotion of a bullet that already has `[created::2026-06-14]` does not append a duplicate created field.
   - Promotion of a bullet without created still appends the supplied test date.

3. Manual smoke test after reloading Obsidian or toggling `task-status-cycler`:
   - In a scratch note with both `Tasks` and `Future Work`, demote a top-level task containing `[created::...]`; it
     moves to `Future Work` with `[created::...]` intact.
   - Demote an indented task containing `[created::...]`; it converts in place with `[created::...]` intact.
   - Promote both bullets back to tasks and confirm no duplicate created field is added.

## Risks

- `collectObsidianTaskTokenRanges()` is exported as a helper, so its output will intentionally change for created
  fields. This is acceptable because its practical role is demotion cleanup, and the user has changed that cleanup
  contract.
- Removing only `created` from the demotion-removal set preserves existing cleanup for transient scheduling/completion
  fields. A broader "preserve all metadata" change would conflict with the existing toggle behavior and is out of scope.
- The vault has unrelated dirty files and prior uncommitted changes in `task-status-cycler/main.js`. The implementation
  should be a small incremental diff on top of the current working tree and should not revert unrelated work.
