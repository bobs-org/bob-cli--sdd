---
create_time: 2026-07-11 09:28:56
status: done
prompt: .sase/sdd/plans/202607/prompts/next_transcluded_pomodoro_tasks.md
tier: tale
---
# Fix Next-status transcluded Pomodoro completion

## Goal

Make recursive Pomodoro completion treat the Obsidian Tasks Next status (`[*]`) as an open task that should be closed.
This must work both when Ctrl+Enter completes an open Pomodoro and when Ctrl+Enter is pressed directly on an embedded
transcluded task-link sub-bullet under an open Pomodoro.

The source of truth is the linked `bob-plugins` repository, specifically `plugins/task-status-cycler/main.js`. Do not
edit the deployed vault copy directly; deploy the tested source through `bob plugins sync` after implementation.

## Context and root cause

- The earlier Ctrl+Enter fix updated the generic direct open/done policy so Todo (`[ ]`) and Next (`[*]`) both become
  Done (`[x]`), while Done reopens to Todo. Its regression test covers an ordinary local Next task and the real Vim
  mapping.
- Pomodoro transclusions intentionally use a separate recursive forced-completion policy. That policy predates Next:
  - `isTranscludedCompletionTraversableStatus()` accepts Todo, In Progress (`[/]`), and Done, but not Next;
  - `isTranscludedCompletionClosableStatus()` accepts Todo and In Progress, but not Next.
- Both policies are required by the recursive flow. The traversable predicate gates resolution of root and descendant
  targets, while the closable predicate governs the write decision and the final forced-write revalidation.
- Therefore a Next root target is treated as unresolved and its entire embedded tree is skipped. A Next descendant is
  likewise not traversed or closed, and merely changing resolution would still leave the forced write rejected.
- The shared recursive path is used by both `completeActivePomodoroTask()` (Ctrl+Enter on the Pomodoro line) and
  `completeActivePomodoroTranscludedTaskLine()` (Ctrl+Enter on an embedded Pomodoro sub-bullet), so fixing the shared
  status policy covers both entry points without duplicating behavior.
- The current linked-plugin baseline is clean. Its complete test command passes 14 tests, and manifest validation passes
  for all 6 plugins.

## Behavioral contract

1. Recursive embedded-transclusion completion uses this status matrix:
   - Todo (`[ ]`) -> Done (`[x]`);
   - Next (`[*]`) -> Done (`[x]`);
   - In Progress (`[/]`) -> Done (`[x]`);
   - Done (`[x]`) remains Done but is still traversed for eligible descendants;
   - Canceled (`[-]`), unknown/custom statuses, non-task blocks, and unresolved links remain excluded.
2. Next is traversable as both a root and a descendant. Its embedded descendants must still be visited before or while
   the Next parent is closed, preserving the current recursive tree semantics.
3. Continue using the existing transcluded-source rewrite path. For `#task` source lines it must add or replace
   `[completion:: YYYY-MM-DD]`, preserve other task text/metadata, and keep the Obsidian block ID as the final token.
4. Preserve all existing recursion safeguards and resolution rules: embedded links only, origin rebasing for same-file
   descendants, cycle/duplicate suppression, depth/target caps, best-effort sibling processing, and line/block-ID
   revalidation before each write.
5. Do not broaden unrelated behavior. Generic direct toggles, task cycling, bare non-transcluded Pomodoro links,
   Pomodoro placeholder/carry-forward logic, cursor movement, and cancellation semantics retain their current policies.

## Implementation

1. Update the two recursive completion predicates in `plugins/task-status-cycler/main.js`.
   - Add `*` to the traversable set alongside space, `/`, and `x`.
   - Add `*` to the closable set alongside space and `/`.
   - Keep the existing separation from the generic `isOpenDoneTaskStatus()` policy; no resolver or writer special case
     should be needed because recursive resolution and forced-write validation already consume these predicates.
2. Review nearby comments so they accurately describe Todo, Next, and In Progress as closable states and Done as
   traversal-only. Avoid unrelated refactoring of the mature recursive orchestration.
3. Extend `scripts/test-task-status-cycler.cjs` with focused regression coverage.
   - Add a recursive-completion status truth table proving Todo/Next/In Progress are traversable and closable, Done is
     traversable-only, and Canceled remains excluded.
   - Use a small in-memory Obsidian app/vault/metadata-cache harness to exercise the actual recursive completion helper,
     not only exported predicates.
   - Cover a Next root source task closing to Done with completion metadata and its block ID preserved.
   - Cover a traversed parent with a nested Next descendant so the test fails if either root/descendant resolution or
     forced-write revalidation omits `*`. Include a Done-parent/Next-child case if that makes traversal-only behavior
     clearer in the harness.
   - Assert Canceled/custom targets remain unchanged and do not cause sibling completion to abort.
   - Exercise the shared recursive primitive or both Pomodoro entry points as appropriate to prove that completing a
     Pomodoro and directly completing its embedded sub-bullet inherit the same fixed policy, without duplicating large
     integration fixtures.
4. Keep the existing npm test wiring unless a separate test file is demonstrably clearer. If a new file is introduced,
   update `package.json` so the complete suite runs it; otherwise limit the code changes to the plugin and current test
   file.
5. Deploy only after all checks pass. Run `bob plugins sync` from the linked source workspace using the explicit source
   repository override when necessary, then compare the deployed `task-status-cycler/main.js` with the tested source
   byte-for-byte so the sync cannot silently use a different checkout.

## Verification

Run from the linked `bob-plugins` source repository:

```bash
node --check plugins/task-status-cycler/main.js
npm test
npm run validate
git diff --check
```

The automated tests should demonstrate:

- recursive status classification includes Next without admitting Canceled/custom statuses;
- a transcluded `[*] #task ... ^id` becomes `[x]`, receives deterministic completion metadata in the test harness, and
  retains `^id` as its final token;
- Next tasks close when encountered at the root and below a traversed parent;
- already-Done parents remain unchanged while eligible Next descendants close;
- existing direct Todo/Next/Done Ctrl+Enter tests still pass;
- unrelated navigation tests and every plugin manifest remain valid.

After syncing and reloading the plugin in Obsidian, smoke-test a daily note with an open Pomodoro containing an embedded
`![[note#^id]]` sub-bullet whose source is Next. First complete the Pomodoro line and confirm the source task becomes
Done; then repeat with Ctrl+Enter directly on the embedded sub-bullet and with a nested Next descendant. Confirm a
Canceled source target remains untouched.

## Expected outcome

Closing an open Pomodoro now recursively closes every eligible embedded source task whether it is Todo, Next, or In
Progress. A `[*]` root or descendant no longer disappears at the resolver boundary, and it is written through the same
metadata-preserving completion path as existing Todo/In-Progress targets. Done traversal, excluded statuses, generic
toggles, and Pomodoro restructuring behavior remain unchanged.
