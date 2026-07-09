---
create_time: 2026-06-05 10:19:32
status: wip
prompt: sdd/prompts/202606/eat_restaurant_migration.md
---
# Eat Restaurant Migration Plan

## Goal

Migrate the restaurants Bryan and Kelly have already tried from `~/bob/eat.md` into individual Markdown notes under
`~/bob/eat/`, without creating `eat.base` yet. The migrated notes should expose enough structured frontmatter for a
future Obsidian Bases table to sort, filter, group, and render useful restaurant data.

## Current Source Shape

- `~/bob/eat.md` is a converted Zorg note with generated metadata and aligned text tables.
- The tried restaurants are in these sections:
  - `RESTAURANTS LIKED`: 86 source rows.
  - `RESTAURANTS NOT LIKED`: 6 source rows.
- Total source restaurant rows: 92.
- Canonical restaurant count after obvious same-name merges: 90.
  - Merge duplicate `Garlic Rose` rows into one note.
  - Merge duplicate `Kitchen 27` rows into one note.
- Do not treat the `breakfast` and `coffee` definition rows at the top as restaurants.
- Do not migrate `~/bob/maybe_eat.md`; that file is a wishlist, not a tried-restaurant source.
- `~/bob/eat/` does not currently contain migrated files.

## Data Model

Create one note per canonical restaurant. Each note should have frontmatter shaped for a future `eat.base`:

```yaml
---
parent: "[[eat]]"
type: restaurant
title: "Restaurant Name"
status: liked
category: "Breakfast"
location: "Westfield"
source_group: union_county
lid: kitchen_27
companions:
  - "[[kelly]]"
source_note: "[[eat]]"
source_anchors:
  - z-251208-0j
source_dates:
  - "251208"
  - "250724"
---
```

Field intent:

- `parent`: required for new notes under `~/bob`; use `[[eat]]`.
- `type`: stable Bases filter (`type == "restaurant"`).
- `title`: display label for formula-backed table links.
- `status`: `liked` or `not_liked`.
- `category`: cuisine/type from the table, normalized enough to remove internal `[[eat#...|breakfast]]` links.
- `location`: location text from the table, preserving meaningful wiki links where present.
- `source_group`: `general`, `union_county`, `breakfast`, or `not_liked`; useful for initial grouping and audit.
- `lid`: original `LID::...` value when present.
- `companions`: include `[[kelly]]` because the source note describes restaurants Bryan and Kelly tried together.
- `source_note`, `source_anchors`, and `source_dates`: traceability back to original rows.

Avoid inventing ratings, prices, addresses, coordinates, or visit counts that are not present in the source.

## Note Body

Use a compact, consistent body:

- H1 with the restaurant name.
- `## Notes` with migrated footnotes/comments attached to that restaurant.
- `## Source` with the original source row(s), preserving enough raw text to audit the migration later.

Attach source footnotes by:

- Following explicit `[[eat#^z-...|N]]` references from restaurant rows.
- Including multi-line footnote continuations.
- Handling known named footnote references such as `[^kitchen_27]` by attaching the relevant note to the matching `lid`.

Preserve URLs from the original row or footnotes in the note body. Do not over-normalize internal wiki links during the
first migration; source fidelity is more important than perfect cross-link rewrites.

## Filenames

Use lowercase snake-case filenames under `~/bob/eat/`, derived from the restaurant title:

- Keep the displayed title in frontmatter and H1.
- Strip punctuation that is awkward in filenames.
- Convert `&` to `and`.
- Preserve leading numbers where useful, e.g. `30_burger.md`, `787_coffee.md`.
- For future duplicate title conflicts that are not the same restaurant, disambiguate with location.

Expected examples:

- `~/bob/eat/kitchen_27.md`
- `~/bob/eat/garlic_rose.md`
- `~/bob/eat/better_than_philly_cheesesteaks_wings.md`

## Source File Handling

Leave `~/bob/eat.md` intact in this migration pass. It is valuable as a legacy audit source, and existing anchor links
inside the vault may still depend on it. The future `eat.base` can query `file.path.startsWith("eat/")` and
`type == "restaurant"` without needing `eat.md` to be rewritten first.

## Implementation Steps

1. Parse `~/bob/eat.md` into source rows and footnotes.
2. Build canonical restaurant records, merging only clear same-name duplicates found in the current source.
3. Generate `~/bob/eat/` if needed.
4. Write one Markdown note per canonical restaurant with the frontmatter and body described above.
5. Validate:
   - 92 source rows parsed.
   - 90 restaurant notes created.
   - Every created note has `parent: "[[eat]]"` and `type: restaurant`.
   - Every source row anchor appears in exactly one created note.
   - Explicitly referenced footnotes are present in at least one relevant note.
6. Spot-check representative edge cases:
   - Duplicates: `Kitchen 27`, `Garlic Rose`.
   - Wiki-link title/location: `The Cranford Hotel`, `NYC`, `cranford`.
   - Missing `lid`: `Yellow Submarine`, `Wasai Bistro`, `Outta Hand Pizza`, `Garlic Rose` legacy row.
   - Not-liked records: all six rows.

## Out Of Scope

- Do not create `~/bob/eat.base`.
- Do not migrate `~/bob/maybe_eat.md`.
- Do not enrich with external restaurant metadata.
- Do not remove or rewrite the legacy source table in `~/bob/eat.md`.
