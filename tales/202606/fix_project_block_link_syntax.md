---
create_time: 2026-06-14 07:33:59
status: done
prompt: sdd/prompts/202606/fix_project_block_link_syntax.md
---
# Fix Project Block Link Syntax

## Context

The project-promotion flow in the Obsidian navigation hotkeys plugin rewrites backlinks that point at a source task
block ID after that task is promoted into a project note. The created project note seeds the promoted task at the `^prj`
block ID.

For Markdown links, the rewrite already emits the correct block-link form:

```md
[label](project.md#^prj)
```

For wiki links, the current rewrite emits:

```md
[[project^prj]]
```

That is not valid Obsidian block-link syntax for a note target. It should emit:

```md
[[project#^prj]]
```

This is isolated to `/home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`, specifically
`rewriteBlockIdLinkOriginal()`, which is exported through `module.exports.helpers` and used by
`applyBlockIdLinkRewrites()`.

The vault currently has unrelated dirty and untracked note files. They should be left untouched.

## Goal

Update project-promotion backlink rewrites so wiki-style links to the original task block are rewritten to valid
Obsidian note block links targeting the promoted project task:

```md
[[old-note#^old-id]] -> [[new-project#^prj]]
```

Aliases and embeds should continue to be preserved:

```md
![[old-note#^old-id|alias]] -> ![[new-project#^prj|alias]]
```

Markdown-link behavior should remain unchanged.

## Proposed Approach

1. Change the wiki-link branch of `rewriteBlockIdLinkOriginal()` to insert `#^prj` after the new project basename,
   preserving the existing embed prefix and optional alias.

2. Keep the existing Markdown-link rewrite unchanged because it already uses `project.md#^prj`.

3. Add focused validation for `rewriteBlockIdLinkOriginal()` covering:
   - plain wiki link: `[[source#^abc]] -> [[project#^prj]]`
   - wiki link with alias: `[[source#^abc|Task]] -> [[project#^prj|Task]]`
   - embedded wiki link: `![[source#^abc]] -> ![[project#^prj]]`
   - Markdown link remains: `[Task](source.md#^abc) -> [Task](project.md#^prj)`
   - malformed or unsupported originals still return `null`

4. Add or reuse a small mocked-`obsidian` Node test harness instead of requiring a live Obsidian session, matching the
   previous validation style for this plugin file.

5. Run static checks:
   - `node --check /home/bryan/bob/.obsidian/plugins/bob-navigation-hotkeys/main.js`
   - `git -C /home/bryan/bob diff --check -- .obsidian/plugins/bob-navigation-hotkeys/main.js`

6. Review the final diff and confirm only the plugin source changed, leaving unrelated vault notes untouched.

## Risks and Notes

- The change is intentionally narrow: only the generated replacement syntax changes for wiki backlinks. Existing
  backlink discovery, source-task retention on rewrite failure, and source-task deletion sequencing should not change.
- Obsidian link targets can include aliases and embeds; these are already captured by the existing regex and should
  continue to be preserved.
- This plan does not require adding or changing any CLI commands, so `memory/long/cli_rules.md` is not relevant.
