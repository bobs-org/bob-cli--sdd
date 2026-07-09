---
create_time: 2026-06-05 09:21:43
status: done
prompt: sdd/prompts/202606/move_done_tasks_dirty_git.md
---
# Plan: Stop Refusing Dirty move-done-tasks Candidates

## Context

`/var/tmp/bob_nightly.log` shows `bob nightly` successfully syncing the Bob vault, then `bob move-done-tasks` planning
valid task/archive/link-repair updates and refusing before mutation because candidate files already had uncommitted Git
changes.

That behavior comes from `src/native/collect_done.rs`: after building the collection plan, `prepare_git()` detects a Git
worktree, computes the paths the command will touch, runs `git status --porcelain` for those paths, and returns a
`DirtyCandidateFiles` error if any are dirty. The command then exits before writing anything. Existing integration tests
assert that refusal for dirty source files, archive files, metadata-only candidates, and link-repair notes.

The requested behavior is different: `move-done-tasks` should not inspect or refuse pre-existing uncommitted Git
changes. It should still scope its own Git staging to the paths it rewrites, and unrelated dirty files should remain
untouched.

## Implementation Approach

1. Remove the dirty-candidate gate from `move-done-tasks`.
   - Delete the `GitPrepareError::DirtyCandidateFiles` variant and its `run_collection()` handling.
   - Delete the `dirty_candidate_paths()` helper and the `git status --porcelain` call from `prepare_git()`.
   - Keep Git worktree detection, non-Git warnings, touched-path calculation, path-scoped `git add`, path-scoped commit,
     and push behavior unchanged.

2. Preserve current file-content semantics.
   - The collection plan is built from the current on-disk vault contents, so existing local edits in a source, archive,
     or link-repair note should be preserved unless they are part of the task block/link text being intentionally
     transformed.
   - If a dirty file is one of the touched paths, the command will stage and commit that file's final contents. That is
     the natural consequence of not checking/refusing dirty candidates while keeping the existing path-scoped commit
     model.

3. Update tests to cover the new contract.
   - Replace dirty-candidate refusal tests with success tests showing dirty source/archive/link-repair/metadata
     candidates are rewritten successfully and retain unrelated local text.
   - Keep the existing test that unrelated dirty files outside the touched set are not committed.
   - Update the `nightly` failure-and-continue test so it no longer depends on dirty candidate refusal. Use a different
     real failure mode for `move-done-tasks` while still proving later `bulk-git-commit` runs.

4. Update user-facing documentation.
   - Remove README language saying `move-done-tasks` refuses dirty candidate files or that smoke testers should expect
     dirty candidates to be skipped.
   - Keep documentation that the command does not run `ob sync`, uses scoped staging/commit/push in Git worktrees, and
     leaves non-Git vaults uncommitted.

## Verification

1. Run focused integration tests for `move-done-tasks` and affected `nightly` behavior.
2. Run a broader CLI test pass if the focused tests are clean.
3. Build the updated binary.
4. Run the updated `bob move-done-tasks` command against the real Bob vault as requested, then inspect/report the
   result.
