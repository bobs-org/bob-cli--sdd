---
plan: sdd/tales/202606/highlights_ref_nested_lib_1.md
---
  I don't think the `bob highlights-ref` command supports markdown files in nested `~/bob/lib/` directories (it only searches one directory level). If that is the case, can you help me fix that? These PDF files will actually be in files of the form `~/bob/lib/<ref_type>/<pdf_basename>.md`. Furthermore, we should start adding a new `ref_type` frontmatter property to the new ref note file that uses `<ref_type>` as its value.

Think this through thoroughly and create a plan using your `/sase_plan` skill. Submit your plan with the `sase plan`
command (as the skill instructs) before making any file changes.
