---
plan: sdd/tales/202606/ref_status_standardization.md
---
  Can you help me standardize the `status` field that is used for ref note files? We should
only support the following statuses:

- unread
- wip
- done
- abandoned
- legacy

All note files in the ~/bob/ref/ai/ directory should be given a status of `legacy` (I've either already read them, but
on my remarkable or am unlikely to ever read them). Make sure to preserve the old status via some other frontmatter
property though. Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
