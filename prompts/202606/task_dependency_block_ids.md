---
plan: sdd/tales/202606/task_dependency_block_ids.md
---
 When I use the Obsidian task `[dependsOn::<id>]` property in Obsidian, the `[id::<id>]` property is generated for the target task if one doesn't already exist using a hash for `<id>`. I'd like for us to start using the task's block ID, if one exists, instead for `<id>`. Can you help me make this change, if it is possible, using your /sase_plan skill?

### Additional Requirements

- Do NOT patch the local tasks installation. This solution needs to be repreducible on other machines (that sync this vault using Obsidian Sync).