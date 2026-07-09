---
plan: sdd/tales/202606/project_note_default_filenames.md
---
 If an Obsidian task in a `~/bob/foo_bar.md` file is promoted to a project note file using the existing
`<ctrl+shift+alt+n>` keymap and it doesn't have a block ID, then we currently do not give the new project note file a
default name. Can you help me make it so we use `~/bob/foo_bar_<X>.md` for the project filename by default in this case,
where `<X>` is the first all-lowercase, alphanumeric sequence such that the `~/bob/foo_bar_<X>.md` file does not already
exist?

- We should start at `~/bob/foo_bar_0.md` and end at `~/bob/foo_bar_z.md`.
- Then `<X>` should iterate through all possible 2-letter variations. then 3-letter variations, etc...
- Make the same improvement to the `<ctrl+shift+n>` keymap (i.e. use a default project file name of `~/bob/<current_filename>_<X>.md`), which is used to create new project note files from scratch (i.e. without promoting an existing task).

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
