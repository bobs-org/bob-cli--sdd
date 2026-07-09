---
plan: sdd/tales/202606/block_id_rename_cache_only.md
---
 When updating a block ID using the special `^` trigger (placed after the last `]` in an Obsidian link), updating all existing references to that block ID can be slow. Can you help me make it much faster? Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
 

%xprompts_enabled:false
### Questions and Answers

#### Q1: Approach

> The block-ID rename slowness comes from a completeness safety net: on every rename the plugin reads ALL ~5,796 vault notes (~11.5 MB) from disk, sequentially, just to find which files reference the old block ID. Obsidian's metadata cache (backlinks + resolvedLinks) already gives the same candidate files instantly. How aggressive should the fix be?

- [ ] **Cache-only (max speed)** — Drop the full-vault disk scan entirely. Discover reference files purely from Obsidian's metadata cache (backlinks/resolvedLinks + source/destination). Turns ~5,796 reads into a handful. Idiomatic Obsidian pattern. Tiny risk: a reference in a note Obsidian hasn't re-indexed yet (e.g. just edited externally by bob-cli) could be missed.
- [ ] **Cache-first + bounded parallel safety scan** — Use the cache as the primary fast path, but still run the whole-vault scan as a backstop — parallelized with bounded concurrency (and read each file once). Much faster wall-clock, keeps disk-truth completeness (no reference ever silently missed), but still does O(vault) I/O per rename.
- [ ] **Parallelize only (lowest risk)** — Keep the exact current algorithm (scan every file) but make the disk reads concurrent instead of sequential. Zero behavior change, simplest diff, but still reads the whole vault every time.
- [x] **Other:** "Cache-only, but make sure to always check the current file (the one that I triggered the rename from) since I often rename block IDs right after they are auto-created (which Obsidian does automatically when linking to an unnnamed block)."

%xprompts_enabled:true