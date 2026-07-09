---
create_time: 2026-06-03 08:03:34
status: done
prompt: sdd/prompts/202606/highlights_ref_scan_speedup.md
---
# Make `bob highlights-ref scan` WAY Faster

## Goal

`bob highlights-ref scan` walks the configured Highlights library, and for **every** PDF it parses the PDF, reads the
sidecar, reads the reference note, and computes a sync plan. On a real library (hundreds of PDFs, some large) this is
slow. The command should run dramatically faster — ideally several times faster on a multi-core machine and roughly 2x
faster from I/O alone — **without changing the command's output, write behavior, or correctness guarantees**.

## Context Reviewed

- Read project short memory (`memory/short/sase.md`): work only inside this ephemeral `bob-cli_<N>` workspace clone and
  its isolated environment; don't run commands against other directories.
- Read long memory `long/cli_rules.md` via the audited `sase memory read` command (planning a possible new CLI flag):
  keep `-h/--help` excellent, keep subcommands/options **sorted alphabetically**, and prefer colored output where it
  improves readability.
- Code lives in `src/native/highlights_ref/mod.rs` (~3.4k lines). Dispatch: `run() → run_scan → scan_library`
  (`mod.rs:265`, `:273`, `:340`).
- Tests: `tests/cli.rs` `highlights_ref_scan_recurses_dry_runs_and_writes_multiple_pdfs` (`:678`) and siblings. They
  assert on `pdf_count`, `notes_create*`, `writes:` and note contents using `.contains(...)`, so **output ordering is
  not asserted** — order-independent assertions, which gives us room to parallelize.

## Root Cause — Why Scan Is Slow

`scan_library` (`mod.rs:340`) is a plain **sequential** loop calling `plan_pdf_sync` once per PDF. Each `plan_pdf_sync`
(`mod.rs:385`) does redundant, fully-serial, whole-file work per PDF:

1. **`read_pdf_marker` (`mod.rs:2316`) → `lopdf::Document::load(path)`** — parses the **entire** PDF into memory (xref
   tables, all objects, object streams) just to locate the _first_ standalone `/Text` annotation. This is the single
   most expensive step and scales with PDF size.
2. **`pipeline_metadata` (`mod.rs:2090`) → `sha256_file(pdf)` (`mod.rs:2874`)** — reads the **whole PDF file from disk a
   second time** to hash it. So every PDF is fully read from disk at least twice per scan.
3. Sidecar + note reads (cheap relative to the above).

Two structural problems compound:

- **No concurrency.** The loop is single-threaded; on an N-core box we waste N-1 cores while each scan is heavily I/O-
  and parse-bound. lopdf's own `rayon` feature is even disabled here (`Cargo.toml:24`, `default-features = false`), so
  individual parses are single-threaded too.
- **Each PDF is read from disk twice** (once by lopdf, once by the hasher) instead of once.

The write phase (`mod.rs:376-381`) is also a sequential loop, and `write_pdf_marker` (`mod.rs:2401`) re-loads the PDF a
_third_ time — but writes only happen for the subset of PDFs whose frontmatter changed, so it is a secondary concern.

## Plan

### Phase 1 — Read each PDF from disk once (≈2x fewer whole-file reads)

Collapse the duplicate whole-file reads so a PDF's bytes are read exactly once and reused for both parsing and hashing.

- Read the PDF bytes once (`fs::read`), compute the SHA-256 from that buffer, and parse via
  `lopdf::Document::load_mem(&bytes)` (confirmed available in lopdf 0.40, `reader.rs:344`) instead of
  `Document::load(path)` + a separate `sha256_file`.
- Thread the resulting sha (and/or the bytes) through `plan_pdf_sync` so `pipeline_metadata` reuses the already-computed
  hash rather than re-reading the file. Keep `sha256_file` for any remaining standalone callers, but ensure the scan hot
  path no longer reads each PDF twice.
- High-level shape: introduce a small "loaded PDF" notion (bytes-hash + parsed `Document`, or just the hash passed
  alongside the existing marker read) so the marker read and the metadata hash share one disk read. Keep the public
  behavior of `read_pdf_marker` / `pipeline_metadata` identical.

This is pure I/O reduction with no behavioral change and benefits `sync` and `doctor` paths too where they share code.

### Phase 2 — Parallelize the per-PDF planning across PDFs (the headline win)

`plan_pdf_sync` is a **pure, read-only** computation over an independent `&Config` and one PDF path; nothing is shared
mutably between PDFs. This is embarrassingly parallel.

- Compute the plans concurrently across the (already sorted) `pdfs` vector, collecting results into an
  **order-preserving** `Vec<Result<PdfSyncPlan>>` so reporting output stays identical/deterministic regardless of
  completion order.
- Preserve the existing "fail before any writes" contract: collect all per-PDF errors exactly as today and return the
  same aggregated `scan failed before writes:` error. Error message text and the set of reported errors must be
  unchanged (sort/join errors in a stable order).
- Implementation choice (to decide during implementation): add the lightweight `rayon` crate and use
  `par_iter().map(...).collect()`, **or** a small fixed std-thread pool to avoid a new dependency. Leaning `rayon` for
  simplicity and a maintained work-stealing scheduler, but I'll confirm against repo dependency norms before adding it.
  If `rayon` is added, scope its use to this module.
- Default degree of parallelism = available cores. Optionally also parallelize the write loop (`execute_pdf_sync` over
  distinct note/PDF paths, which collisions preflight has already proven disjoint) — writes touch independent files so
  this is safe, but it's a smaller, optional win and will be gated on measured benefit.

### Phase 3 — Optional CLI control: `--jobs/-j`

To make parallelism tunable and tests deterministic if ever needed:

- Add an alphabetically-sorted `--jobs <N>` (`-j`) option to `with_scan_args` (`mod.rs:1682`), defaulting to "all
  available cores", with `--jobs 1` forcing the current sequential behavior. Update `-h/--help` to document it clearly,
  matching the existing option style (per `cli_rules`).
- This is the only CLI surface change; everything else is internal. If we prefer zero CLI change, parallelism can simply
  default to core count with no flag — I'll confirm the preference before adding the flag.

### Phase 4 (stretch / follow-up) — Incremental skip of unchanged PDFs

The biggest real-world win for _repeated_ scans: avoid the expensive `Document::load` for PDFs that have not changed
since the last sync. The note frontmatter already stores `source_pdf_sha256` and `highlights_marker_hash`. On rescan we
can hash the file (one cheap sequential read, no full parse) and, when the sha matches the stored value, the PDF bytes —
and therefore the marker projection — are provably unchanged, so the full lopdf parse can be skipped and the stored
marker hash reused.

This is correctness-sensitive (it changes the data flow for the "unchanged" case and must still produce byte-identical
plans/output), so I'm scoping it as a **separate follow-up** rather than bundling it with the safe Phase 1–2 speedups.
I'll flag it for a dedicated change once Phases 1–2 land and are validated.

## Out of Scope / Non-Goals

- No change to the sync decision logic, rendered note/marker format, frontmatter fields, or any printed lines.
- No change to collision/dirty preflight semantics or the "no writes if any error" guarantee.

## Validation

- `cargo build` and `cargo clippy` clean in the workspace.
- `cargo test` — existing scan tests must pass unchanged (`highlights_ref_scan_*` in `tests/cli.rs`), confirming
  identical output and write behavior.
- Add a focused test (or extend an existing one) with several PDFs to confirm output remains complete and
  order-independent under parallel execution, and that `--jobs 1` (if added) matches multi-job output.
- Manual timing on a representative library (`time bob highlights-ref scan --dry-run`) before vs. after, to confirm the
  speedup and report the measured factor.

## Risks & Mitigations

- **Output nondeterminism under parallelism** → collect into an order-preserving vector; assertions are already
  order-independent, and we keep printing in sorted-path order.
- **Error-reporting differences** → aggregate and sort errors deterministically to match today's message.
- **New dependency (`rayon`)** → confirm against repo norms; fall back to a small std-thread pool if undesirable; scope
  usage to this module.
- **Over-subscription** (our cross-PDF parallelism vs. lopdf's internal rayon) → keep lopdf `default-features = false`
  so only our outer parallelism is active.
