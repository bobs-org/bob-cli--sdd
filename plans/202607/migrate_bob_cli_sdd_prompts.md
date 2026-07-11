---
create_time: 2026-07-11 18:02:02
status: done
prompt: .sase/sdd/plans/202607/prompts/migrate_bob_cli_sdd_prompts.md
tier: tale
---
# Migrate bob-cli's SDD Companion Store to Nested Prompt Layout

## Motivation

sase commit `71effb320` ("feat(sdd): nest prompt snapshots with monthly plans") changed the canonical SDD
prompt-snapshot location from a top-level `prompts/<YYYYMM>/` tree to `plans/<YYYYMM>/prompts/`, so each month's plans
and their prompt snapshots live together. The sase repo's own companion store has already been migrated. bob-cli's SDD
companion repo (`bobs-org/bob-cli--sdd`) still uses the legacy top-level layout and should be migrated the same way.

The migration machinery already exists and is idempotent: `sase sdd init` detects a legacy layout, `git mv`s every
snapshot into its nested month directory, rewrites all references across the store's markdown files, refreshes the
generated README guides, and commits + pushes the companion repo in a single scoped commit. No new application code is
required — this plan is an operational rollout plus verification, with one tiny pre-existing data repair.

## Current State (verified inventory)

bob-cli's SDD companion store (checked out at `.sase/sdd/`, remote `git@github.com:bobs-org/bob-cli--sdd.git`):

- **279 prompt snapshots** in the legacy layout: 243 in `prompts/202606/`, 36 in `prompts/202607/`.
- **No legacy `specs/` directory** (some older stores have one; this store does not).
- `plans/` already has both month directories (`202606/`, `202607/`) plus the generated `plans/README.md`. No
  `plans/*/prompts/` directories exist yet.
- **Reference forms present in the store** (all covered by the migration's rewriter, which handles the `""`, `"sdd/"`,
  and `".sase/sdd/"` prefixes):
  - ~280 root-relative frontmatter links (`prompt: prompts/<month>/<name>.md`) in plan files.
  - 27 `.sase/sdd/prompts/...` references.
  - Zero `](../prompts/...)` markdown-relative links (unlike the sase store).
- **Companion checkout is clean** and synchronized with its upstream.
- **Baseline validation**: 1 error + 8 warnings.
  - The error: `plans/202606/home_2_completion_1.md` has frontmatter
    `prompt: sdd/prompts/202606/home_2_completion_1.md`. Companion git history (`git log --all`) shows that snapshot
    **never existed in any commit**, and nothing else in the store references it. This is a pre-existing dangling link,
    not something the migration can fix (the rewriter only remaps links whose target file is actually moved).
  - The 8 warnings are all `unpaired-file` (plans that legitimately have no prompt counterpart) and are expected to
    persist unchanged after migration.

The bob-cli primary repo itself has **zero references** to SDD prompt paths (code, docs, or justfile), and its `just`
targets are pure Rust gates — so this migration touches only the companion store, not the primary repo.

**Toolchain prerequisite**: the installed `sase` CLI is a uv-tool _editable_ install backed by a dev checkout that is
currently 3 commits behind its `origin/master`, whose tip is exactly `71effb320`. The installed CLI therefore does
**not** yet contain `sase.sdd._prompt_migration` — running `sase sdd init` today would not migrate anything. The dev
checkout is clean and on `master`, so `sase update` (which fast-forwards clean editable checkouts to upstream and
reinstalls the tool set) is the canonical way to deliver the migration code.

## Plan

### Phase 1 — Update the sase toolchain

1. Run `sase update` to fast-forward the clean sase dev checkout to `origin/master` and reinstall the editable uv tool
   set.
2. Verify the migration code is live: `sase.sdd._prompt_migration` imports successfully under the tool's interpreter,
   and the dev checkout's HEAD includes `71effb320`.

Note: `sase update` also reconciles the other editable sase plugins (sase-github, sase-telegram, sase-core) as one
atomic set; its dry run shows the non-core checkouts skip fast-forward but reinstall cleanly. No action needed beyond
confirming the update summary is healthy.

### Phase 2 — Repair the pre-existing dangling prompt link

3. In the companion store, remove the dangling `prompt: sdd/prompts/202606/home_2_completion_1.md` frontmatter line from
   `plans/202606/home_2_completion_1.md` (first try `sase sdd repair-links` in case it can resolve it automatically;
   otherwise edit the single line by hand). The referenced snapshot never existed, so there is no correct target to
   point at.
4. Commit this one-line repair to the companion repo as its own commit, before the migration, so the migration's
   before/after validation comparison is clean (baseline becomes 0 errors + 8 warnings).

### Phase 3 — Run the migration

5. From the bob-cli repo root, run `sase sdd init`. Expected behavior (matching the sase-store rollout):
   - `git mv` of all 279 snapshots into `plans/202606/prompts/` and `plans/202607/prompts/`.
   - Rewrite of every `prompts/...`, `sdd/prompts/...`, and `.sase/sdd/prompts/...` reference across the store's
     markdown (plan frontmatter, beads, legends, etc.).
   - Refresh of the generated guides (top-level `README.md` and `plans/README.md`) with the nested-layout documentation.
   - A **single** scoped companion commit that includes both sides of the renames (the scoped-commit fix for staged
     `git mv` renames shipped in `71effb320`), followed by a push.

Note on self-reference: this plan's own prompt snapshot will be written by the _current_ (stale) CLI into the legacy
`prompts/202607/` location when the plan is proposed. The migration will relocate it along with everything else, so the
expected post-migration count for `plans/202607/prompts/` is **37** (36 + this plan's snapshot), and its frontmatter
link should be verified as rewritten.

### Phase 4 — Verify

6. Structural checks:
   - Top-level `prompts/` directory is gone.
   - `plans/202606/prompts/` has 243 files; `plans/202607/prompts/` has 37 (see self-reference note).
7. Referential checks:
   - `sase sdd validate --show-warnings`: **0 errors**, and exactly the same 8 pre-existing `unpaired-file` warnings.
   - `grep` confirms no remaining references to the old top-level prompt paths in any store markdown.
   - Spot-check that both reference forms found in the inventory (`prompt: prompts/...` frontmatter and
     `.sase/sdd/prompts/...`) were rewritten to their nested equivalents.
8. Behavioral checks:
   - `sase sdd list` plan listing does not include nested prompt snapshots as plans.
   - This plan resolves in plan search to the plan file, not its nested prompt snapshot.
9. Repo hygiene checks:
   - Companion checkout is clean (`git status` empty), pushed, and exactly synchronized with its upstream (ahead/behind
     0).
   - The migration landed as a single commit (plus the separate Phase 2 repair commit).

## Risks and Mitigations

- **Concurrent writers**: other bob-cli agent workspaces have independent companion clones; an agent still running a
  stale sase could push a legacy-layout prompt after migration. The migration is idempotent — a later `sase sdd init`
  re-nests strays — and legacy read compatibility means nothing breaks in the interim. Accept and note.
- **Concurrent remote update mid-migration**: the companion push helper fetches and rebases before pushing (observed
  working during the sase-store rollout). No force pushes.
- **Generated-guide drift**: if a concurrent stale-sase `sase sdd init` rewrites the READMEs with old content after
  migration (as happened once during the sase-store rollout), re-run `sase sdd init` to refresh and recommit the guides.
- **Rollback**: the companion store is plain git — reverting the migration commit restores the legacy layout, and sase
  retains read compatibility for both layouts.

## Out of Scope

- Any sase source changes (the migration feature already shipped in `71effb320`).
- The bob-cli primary repo (no references exist; nothing to change).
- Any other SDD companion stores (e.g. other repos' stores) — this plan covers only `bobs-org/bob-cli--sdd`.
- The sase `sdd-directory-map.png` asset refresh (tracked as a sase-repo follow-up).

## Success Criteria

1. `sase --version` toolchain includes the nested-prompt migration code.
2. Top-level `prompts/` no longer exists in the bob-cli companion store; all 280 snapshots (279 existing + this plan's
   own) live under `plans/<YYYYMM>/prompts/`.
3. `sase sdd validate` reports 0 errors; warnings unchanged at the 8 pre-existing `unpaired-file` entries.
4. No store markdown references any old-layout prompt path.
5. Companion checkout is clean and synchronized with `origin`, with the migration as a single scoped commit plus one
   small preceding link-repair commit.
