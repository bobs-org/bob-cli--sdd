---
plan: .sase/sdd/plans/202607/file_scoped_task_dependency_ids.md
---
 #fork:61 Did we make sure to handle the `id` property (and corresponding `dependsOn` property values) to external files properly so block IDs only need to be unique within the file they are defined in? If not, can you use your /sase_plan skill to make this happen using the `<parent_file_path>__<id>` syntax, where `<parent_file_path>` has any `/` (for note files that live in subdirectories) replaced with `__` and `<id>` is the block ID of the dependency note?