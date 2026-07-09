---
plan: sdd/tales/202606/fix_move_done_tasks_link_repair.md
---
 When we run the `bob move-done-tasks` command, it moves done tasks from ~/bob/ note files to ~/bob/done/ note files. This command is supposed to also fix any and all block links in the ~/bob/ directory that point to those done tasks, but it doesn't seem to be doing that (see the ~/bob/2026/20260621.md file, for example, which contains block links that were broken by this command). Can you help me diagnose the root cause of this issue and fix it? Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
 

%xprompts_enabled:false
### Questions and Answers

#### Q1: Existing breakage

> I traced the root cause: the move-done-tasks link-repair scan does NOT exclude the _generated/ directory (unlike `bob projects`), so the auto-generated tag page _generated/tag_pages/topic/sase.md collides with the real sase.md. That makes the basename sase ambiguous, so NoteIndex::resolve returns None and links like [[sase#^auto-pair]] are silently skipped. This shadows MANY topic notes (ads, ai, api, code, day, etc). Separately, the already-broken links (in ~17 files like 2026/20260621.md) will NOT be healed by just fixing the bug, because link repair only fires for blocks moved in the SAME run, and those sase tasks are already archived. How should I handle the already-broken links?

- [x] **Self-healing redesign (recommended)** — Make link repair derive targets from current archive/source state each run: repair any [[source#^id]] where ^id is gone from the source note but present in the archive whose parent is that source. Heals all existing breakage on next run AND prevents recurrence; idempotent. Larger change.
- [ ] **Fix bug + one-time repair** — Fix the _generated exclusion so future moves work, and also run a one-time pass now to repair the ~17 files of existing broken links. Command stays move-coupled (only repairs current-run moves going forward).
- [ ] **Fix bug only** — Only fix the _generated exclusion. Future moves repair correctly, but the existing broken links stay broken (you fix them manually).

#### Q2: Resolution fix

> For the resolution fix itself, how broadly should I make basename resolution robust?

- [x] **Exclude generated/template dirs (recommended)** — Share/mirror projects.rs is_excluded_directory so the collect_done scan also skips _generated and _templates. Directly removes the false ambiguity; matches existing project convention.
- [ ] **Also add shortest-path disambiguation** — In addition, when a basename still collides, resolve to the shallowest path (Obsidian default) instead of giving up. Defense-in-depth for future collisions outside _generated/_templates.

%xprompts_enabled:true