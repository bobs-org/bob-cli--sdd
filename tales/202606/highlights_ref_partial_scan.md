---
create_time: 2026-06-04 10:27:50
status: done
prompt: sdd/prompts/202606/highlights_ref_partial_scan.md
---
# Make highlights-ref scan continue past bad PDFs

## Goal

Change the recursive Highlights reference sync workflow so a validation failure or PDF write failure for one PDF does
not prevent unrelated PDFs from being processed. The command should still return a non-zero exit code when any PDF
fails, but successful PDFs should be fully planned and, for non-dry-run scans, written.

The user referred to `bob highlights-ref sync` in the prompt, but the described "all PDFs that the command tries to
process" behavior maps to the multi-PDF `bob highlights-ref scan` path. The single-PDF `sync <pdf>` command should keep
failing normally for its one target.

## Current behavior

`src/native/highlights_ref/mod.rs` has a single-PDF path:

- `run_sync -> sync_pdf`
- `sync_pdf` plans one PDF, prints one report, runs `ensure_safe_to_write`, then `execute_pdf_sync`
- Any error exits with `bob highlights-ref: ...` and status 1

The multi-PDF path is:

- `run_scan -> scan_library`
- `scan_library` collects PDFs, validates output collisions, plans all PDFs with `plan_pdfs`, aggregates planning
  errors, and currently returns `scan failed before writes` if any plan fails
- If all planning succeeds, it prints all plan entries, optionally runs one global `ensure_safe_to_write`, then executes
  each plan sequentially
- The write loop uses `execute_pdf_sync(config, plan)?`, so any write-time error aborts the remaining PDFs

This gives strong all-or-nothing behavior, but it is too strict for independent per-PDF validation and write failures.

## Desired behavior

For `bob highlights-ref scan`:

- Keep deterministic path-order planning and reporting, including `--jobs` behavior.
- For each PDF whose planning succeeds, print the normal per-PDF plan entry.
- For each PDF whose planning fails, print a per-PDF failure entry that includes the PDF path and error.
- On dry run, finish reporting every PDF and summarize both planned PDFs and failed PDFs. Exit 1 if any PDF failed;
  otherwise exit 0.
- On write runs, write all PDFs whose plans are valid and whose targets pass global safety checks. If `execute_pdf_sync`
  fails for one PDF, record that failure and continue executing the remaining valid plans.
- Exit 1 after the write summary if any per-PDF planning or write failure occurred.
- Keep `sync <pdf>` behavior unchanged.

## Safety boundaries to preserve

Some checks should remain global and should still prevent all writes:

- Library discovery errors (`collect_pdf_paths`) should abort because the command does not know the full input set.
- Output target collisions (`validate_output_collisions`) should abort before writes because two PDFs could write the
  same note.
- Dirty target preflight (`ensure_safe_to_write`) should remain global over all successfully planned write targets and
  abort before writes if it finds unsafe dirty files. This preserves the existing Git safety contract and avoids
  partially writing after discovering an unsafe tracked target.

Per-PDF failures that should no longer abort the whole scan include:

- Missing or malformed marker note.
- Missing required marker fields or unsupported marker/frontmatter values.
- Unsupported sidecar format for one PDF.
- Per-PDF note validation failures, such as a target note missing the managed Highlights region.
- Per-PDF `--write-pdf` refusal during scan planning.
- Write-time races or PDF write failures for one PDF, such as `reference note changed during sync; rerun`,
  `PDF changed during sync; rerun`, temporary PDF save failure, or atomic note write failure.

## Implementation plan

1. Introduce a small scan result model in `src/native/highlights_ref/mod.rs`.
   - Represent per-PDF planning outcomes as either a `PdfSyncPlan` or `{ pdf, error }`.
   - Represent per-PDF write outcomes as either a `SyncWriteReport` or `{ pdf, error }`.
   - Keep errors paired with the original PDF path and preserve the sorted `pdfs` order.

2. Refactor `scan_library`.
   - Keep `collect_pdf_paths` and `validate_output_collisions` as hard errors.
   - Replace the current `errors` early return after `plan_pdfs` with collection of valid plans and per-PDF planning
     failures.
   - Print the standard scan config report once.
   - Print `pdf_count` as the total number of discovered PDFs, not only valid plans. Add focused summary fields for
     failures so users can see why the command exits non-zero.
   - Print normal plan entries for valid plans and explicit error entries for failed plans.
   - For dry runs, print the normal dry-run summary for valid plans plus failure counts, `writes: none`, then return an
     error only after all output is printed if failures exist.
   - For write runs, run `ensure_safe_to_write(config, valid_plans.iter())` before any writes. If it fails, keep the
     existing hard failure behavior.
   - Execute valid plans sequentially as today, but collect `execute_pdf_sync` errors and continue with the next plan.
   - Print the write summary for successful writes plus failure counts, then return an error if any per-PDF planning or
     write errors occurred.

3. Keep existing deterministic output properties.
   - `plan_pdfs` already returns results in input order; use that order for valid entries and failure entries.
   - Do not make write execution parallel in this change. Sequential writes keep race/debug behavior easier to reason
     about and reduce blast radius.

4. Update user-facing docs.
   - Update `docs/highlights-ref-sync.md` scan behavior from all-or-nothing per-PDF planning to best-effort per-PDF
     processing.
   - Clarify that collisions and dirty-target preflight remain hard global failures before writes.
   - Add or update troubleshooting language so validation/PDF write errors explain that other valid PDFs may still have
     been processed, while the final command status remains non-zero.

5. Update tests in `tests/cli.rs`.
   - Adjust existing scan planning-error tests that expect `scan failed before writes` to expect non-zero status, a
     per-PDF failure report, and no note for the invalid PDF.
   - Add a mixed dry-run test with one valid PDF and one invalid PDF. Assert the valid PDF appears in the plan summary,
     the invalid PDF appears in failure output, `writes: none` is printed, no notes are created, and exit status is 1.
   - Add a mixed write test with one valid PDF and one invalid PDF. Assert exit status is 1, the valid note is
     created/updated, the invalid note is not created, and failure output names the invalid PDF.
   - Add or adapt a write-time failure test if practical using a target note/PDF mutation scenario or filesystem
     permission failure. Assert a later valid PDF is still processed after one `execute_pdf_sync` failure.
   - Keep the collision test asserting no notes are written when duplicate outputs exist.
   - Keep the `--jobs 1` vs `--jobs 4` deterministic dry-run test passing for all-success scans.

6. Validate.
   - Run `cargo fmt --check`.
   - Run `cargo clippy --all-targets --all-features`.
   - Run targeted tests around `highlights_ref_scan`.
   - Run full `cargo test` if targeted tests pass.

## Risks and mitigations

- Output compatibility risk: existing tests and scripts may look for `scan failed before writes`. Mitigation: update the
  documented contract and use stable, grep-friendly failure lines such as `scan_failures: N` and
  `result: partial-failure` or similar.
- Safety risk: continuing after failures could accidentally bypass dirty-file protection. Mitigation: keep dirty
  preflight global and before any writes for all successfully planned write targets.
- Ambiguity risk: `pdf_count` currently counts plans, not discovered PDFs. Mitigation: make it count discovered PDFs and
  add separate counts for planned/failed PDFs.
- Atomicity expectation risk: users may assume non-zero means nothing was written. Mitigation: docs and summary must
  state successful writes clearly when partial failures occur.
