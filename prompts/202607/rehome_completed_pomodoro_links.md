---
plan: .sase/sdd/tales/202607/rehome_completed_pomodoro_links.md
---
 The `bob mark-next-tasks` command currently maintains which Obsidian tasks have the `[*]` task status by checking which block links exist on open pomodoros in today's daily file (see recent, related git commits). Can you help me also start checking for any block links in that daily note's open pomodoros that point to done/complete Obsidian tasks?

- If any exist, we should ensure that they are both transcluded and that they are sub-bullets of the current pomodoro (the open one with that has a time range--there should be at most one of these).
- If they are not transcluded, you should make them so by putting an exclamation point before the block link. If they are sub bullets of a future Pomodoro, you should move them to be a sub bullet of the current Pomodoro. 
- If there is no current Pomodoro, you should move them to the last completed Pomodoro in today's daily file. If no pomodoro is completed in today's daily file, just leave the transcluded block link sub-bullet where it is.

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the
`sase plan propose` command (as the skill instructs) before making any file changes.
 