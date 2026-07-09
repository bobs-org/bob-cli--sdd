---
create_time: 2026-06-09 09:56:36
status: wip
prompt: sdd/prompts/202606/metadata_menu_property_suggestions.md
---
# Plan: Metadata Menu Property Suggestions

## Goal

Configure Obsidian Metadata Menu for Bryan's `~/bob` vault so common frontmatter properties with small accepted value
sets get curated suggestions in the editor, without over-constraining legacy notes or fields that are still free-form.

## Context Gathered

- Obsidian vault: `~/bob`.
- Required memory says new Markdown notes in `~/bob` should include a `parent` frontmatter link.
- Local `~/bob/.obsidian/community-plugins.json` does not yet list `metadata-menu`, and
  `~/bob/.obsidian/plugins/metadata-menu/` is absent. This conflicts with the user's statement that Metadata Menu was
  installed, so the first implementation step must verify Obsidian Sync/plugin installation before writing plugin
  configuration.
- Existing Bases already define different semantics for the same `status` property:
  - `eat.base`: restaurant verdicts are `liked` and `not_liked`.
  - `refs.base`: reference workflow statuses include `unread`, `collect_fleeting_notes`, `review_fleeting_notes`,
    `review_lit_notes`, `wip`, `read`, and `abandoned`.
- Metadata Menu docs confirm the right primitives:
  - FileClasses live as notes in the configured class files folder.
  - FileClasses can map by explicit `fileClass`, tag, folder path, bookmark group, query, or global fallback.
  - `Select`, `Multi`, and `Cycle` fields can present predefined values.
  - Field types are not meant to be changed in place after creation.

For inventory, I treated "non-legacy" as notes outside `old_lib/`, `_zorg_templates/`, and `_generated/`, without
`generated_from_zorg: true`, and without `status: legacy`. In that active frontmatter set, the strongest enum-like
properties are:

- `type`: `restaurant` 91, `[[ref]]` 22, `daily` 10, `[[done]]` 7, `[[day]]` 3, `monthly` 2, `inbox` 1, `project` 1,
  `yearly` 1.
- `status` by type:
  - restaurant: `liked` 84, `not_liked` 7.
  - ref: `wip` 10, `read` 7, `abandoned` 4.
  - project: `active` 1.
- `ref_type`: `chat` 15, `papers` 3, `docs` 2, `blogs` 1.
- restaurant `source_group`: `union_county` 45, `general` 27, `breakfast` 12, `not_liked` 6.

Fields such as restaurant `category` and `location` should not be strict selects yet: `category` has many
near-duplicates and typos that need taxonomy cleanup first, and `location` mixes plain text with aliased/block
wikilinks.

## Recommended Configuration Strategy

Use scoped FileClasses, not global field definitions.

Do not set Metadata Menu's `fileClass` field alias to `type` initially. The vault's `type` values are existing domain
data used by Bases/templates and are not a clean FileClass namespace. Using `type` as the Metadata Menu class field
would be brittle for values such as `[[ref]]` and would make future cleanup harder. Prefer FileClass folder/query
mapping, with no new `fileClass` property inserted into existing notes during the first pass.

Use inline value lists inside FileClass field definitions rather than separate allowed-values notes at first. Separate
Markdown lookup notes conflict with the vault convention that new notes include frontmatter, and Metadata Menu's
line-based option notes may treat every line as an option. FileClass-local option lists are simpler, versionable, and
adequate for the current small sets.

## Implementation Plan

1. Verify Metadata Menu installation state.
   - Re-check `~/bob/.obsidian/community-plugins.json`.
   - Re-check `~/bob/.obsidian/plugins/` for the actual plugin id/path.
   - If Metadata Menu is still absent locally, stop before vault edits and ask the user to open/sync the same `~/bob`
     vault or confirm the install target.
   - If present, inspect the plugin's `manifest.json` and `data.json` so any direct config edits match the installed
     version.

2. Configure Metadata Menu baseline settings.
   - Scope: frontmatter only.
   - Class files path: `_meta/metadata-menu/classes/` with the trailing slash Metadata Menu expects.
   - No global FileClass for the first pass.
   - No `fileClass` alias override for the first pass.
   - Exclude obvious non-working-note areas from indexing/mapping: `old_lib/`, `_zorg_templates/`, and `_generated/`.
   - Keep field options in a modal/context submenu rather than expanding every field into the context menu, to avoid
     clutter on notes with many generated metadata fields.

3. Create the first FileClass: restaurant.
   - FileClass note: `_meta/metadata-menu/classes/restaurant.md`.
   - Include `parent: [[Bob Home]]` or the closest existing `_meta` parent to satisfy vault note conventions.
   - Map it to `eat/` using Metadata Menu's folder path mapping.
   - Fields:
     - `type`: `Select`, values: `restaurant`.
     - `status`: `Select`, values: `liked`, `not_liked`.
     - `source_group`: `Select`, values: `union_county`, `general`, `breakfast`, `not_liked`.
     - Leave `title`, `category`, `location`, `lid`, and source tracking fields as unmanaged/free-form in the first
       pass.
   - Verify against `eat.base` so the Base views still render unchanged.

4. Create the second FileClass: reference.
   - FileClass note: `_meta/metadata-menu/classes/reference.md`.
   - Include a `parent` link.
   - Prefer a Metadata Menu fileClass query that targets active reference notes: folder `ref/`, `type == [[ref]]`, and
     `status != legacy`.
   - If query mapping cannot be made reliable in the installed plugin version, fall back to folder mapping for `ref/`
     but avoid bulk inserting fields into legacy notes.
   - Fields:
     - `type`: `Select`, values: `[[ref]]`.
     - `status`: `Select`, values: `unread`, `collect_fleeting_notes`, `review_fleeting_notes`, `review_lit_notes`,
       `wip`, `read`, `abandoned`.
     - `ref_type`: `Select`, values: `chat`, `papers`, `docs`, `blogs`.
   - Do not manage PDF/highlight pipeline fields through Metadata Menu; they are generated automation metadata.

5. Defer lower-confidence classes until the first two work.
   - Daily/monthly/yearly notes: defer because `type` currently mixes `daily` and `[[day]]`; first decide whether the
     canonical day type is `[[day]]`.
   - Done notes: low value; `type: [[done]]` is fixed and not often edited.
   - Project/inbox notes: too little current sample data to define accepted values safely.
   - Restaurant `category`: defer until a separate cleanup maps near-duplicates such as `Barfood`/`Bar Food`,
     `Cheesesteaks`/`Cheeseteaks`, and singular vs plural variants.

6. Add a lightweight validation/audit backstop after suggestions are working.
   - Use Dataview first, since it is already installed.
   - Create or update one `_meta` note with DQL/DataviewJS checks for:
     - restaurant notes whose `status` is not `liked` or `not_liked`;
     - restaurant notes whose `source_group` is outside the configured set;
     - active reference notes whose `status` or `ref_type` is outside the configured set.
   - This should report drift only; do not auto-fix frontmatter in the first pass.

7. Verification.
   - Run the same metadata inventory after configuration and confirm no existing notes were unintentionally rewritten.
   - In Obsidian, open one `eat/` note and one active `ref/` note and verify the Metadata Menu button/modal offers the
     expected Select choices.
   - Confirm `eat.base` and `refs.base` still show the same note sets and badges.
   - Confirm legacy reference notes are not made noisy by the new active reference FileClass.
   - Check `git status` in `~/bob` and report every changed file explicitly.

## Risks and Mitigations

- Metadata Menu is not present in the local synced vault yet.
  - Mitigation: make installation verification a hard gate before writing vault config.
- Hand-editing plugin `data.json` may be version-sensitive.
  - Mitigation: inspect the installed plugin data first; prefer FileClass notes and plugin-supported settings over
    speculative JSON edits.
- A global `status` definition would break because `status` is context-specific.
  - Mitigation: only define `status` inside scoped FileClasses.
- Reference legacy notes could appear invalid if folder-mapped too broadly.
  - Mitigation: prefer query mapping for active refs, and do not bulk insert fields into legacy notes.
- Strict restaurant category/location fields could prematurely encode messy data.
  - Mitigation: defer them until after a dedicated taxonomy cleanup.

## Sources

- Metadata Menu settings: https://mdelobelle.github.io/metadatamenu/settings/
- Metadata Menu FileClasses: https://mdelobelle.github.io/metadatamenu/fileclasses/
- Metadata Menu fields: https://mdelobelle.github.io/metadatamenu/fields/
