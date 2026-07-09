---
plan: sdd/tales/202606/obsidian_delete_tab_keymaps_fix_1.md
---
 #fork:00n This didn't work. Can you help me diagnose the root cause of this issue and fix it? Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
 

%xprompts_enabled:false
### Questions and Answers

#### Q1: Chord scheme

> The bare chords d< / d> / dD cannot work in Obsidian: CodeMirror Vim resolves d as the delete operator on the first keystroke, so any normal-mode mapping starting with d never fires (this is why nothing happened). Your Neovim maps are actually leader-prefixed (<leader>d<, <leader>d>, <leader>do). Which replacement chord scheme should I use in the Obsidian vimrc?

- [x] **\d< \d> \do (backslash leader)** — RECOMMENDED. \ is unbound in CodeMirror Vim (and is your Neovim localleader), so it works reliably. Mnemonic: d=delete, < left / > right / o others — mirrors your Neovim <leader>do for others.
- [ ] **\d< \d> \dD** — Same safe backslash prefix, but keep the previous D for others instead of o.
- [ ] **<Space>d< etc. (space leader)** — Space as leader. Riskier: Space may be bound as a motion in CodeMirror Vim, which could reintroduce the same first-key problem. Would need empirical confirmation.
- [ ] **Use Obsidian global hotkeys instead** — Bind via .obsidian/hotkeys.json so they always work, but they would also fire in insert/reading mode, not just Vim normal mode (the original plan rejected this).

%xprompts_enabled:true