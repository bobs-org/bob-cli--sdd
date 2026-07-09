---
create_time: 2026-06-20 12:13:23
status: wip
prompt: sdd/prompts/202606/bob_cli_8_closeout.md
---
# bob-cli-8 Closeout Verification Cleanup

## Goal

Finish the remaining verification work needed to safely close `bob-cli-8`.

## Plan

1. Normalize the repository formatting expected by the current `cargo fmt --check` target.
2. Fix the clippy warnings currently blocking `cargo clippy --all-targets --all-features` without changing behavior.
3. Re-run `just all` and confirm the plugin-specific smoke checks still pass.
4. Update `sdd/epics/202606/bob_plugins_repo.md` frontmatter to `status: done`.
5. Close epic bead `bob-cli-8` with `sase bead close`.
6. After the epic is closed, run `just pyvision` if that recipe is available and address any actionable unused-code
   findings.
