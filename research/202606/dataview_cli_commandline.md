---
create_time: 2026-06-03
status: research
topic: Running Obsidian Dataview queries from the command line
---
# Research: Dataview Queries from the Command Line

## Answer

Yes, but not through a native Dataview CLI. Dataview still has no official
standalone command-line runner; its real query engine depends on Obsidian's
plugin runtime and metadata cache. For exact Dataview behavior, the command must
run inside a live Obsidian desktop app. For true headless use, use a partial
Dataview-like reimplementation and accept reduced compatibility.

Best implementation for `bob-cli`: add a native `bob dataview` command that uses
the official Obsidian CLI `eval` command to call Dataview's own plugin API, with
an optional `ob sync` freshness step before the query. Keep a separate headless
fallback, probably `dynomark`, for cron/server workflows where desktop Obsidian
cannot run.

## Verified Local State

Vault/tooling observations on 2026-06-03:

- `~/bob` is the Obsidian vault.
- Dataview is enabled in `.obsidian/community-plugins.json`.
- Dataview plugin version is `0.5.68`.
- Local REST API is not enabled in the vault.
- `ob` from Obsidian Headless is installed at version `0.0.8`.
- `obsidian`, `node`, and `npm` are installed.
- In this non-GUI shell, `obsidian help` and `obsidian eval code="1+1"` failed
  with "The CLI is unable to find Obsidian. Please make sure Obsidian is running
  and try again." This means the `eval` path needs a running desktop Obsidian
  session; it is not a server/headless solution by itself.

`ob` is useful for Obsidian Sync freshness, but it is not a community-plugin
runtime. Obsidian's own docs distinguish the desktop-controlling `obsidian` CLI
from Obsidian Headless, which is a standalone Sync/services client.

## Core Constraint

The Dataview maintainer answered the CLI question directly in 2021: there was no
CLI, and the blocker was removing dependence on Obsidian APIs that are only
available when Dataview runs as a plugin. That still appears to be the ecosystem
constraint: Dataview's documented JavaScript APIs are in-Obsidian APIs, not a
standalone Node library.

Dataview exposes the useful query methods once it is loaded in Obsidian:

- `dv.pagePaths(source)` returns paths for a Dataview source expression such as
  `#tag`, `"folder"`, `[[note]]`, or source boolean combinations.
- `dv.tryQuery(query, originFile, settings)` executes full DQL and returns
  structured results.
- `dv.tryQueryMarkdown(query, originFile, settings)` executes full DQL and
  returns rendered Markdown.

Important distinction: `pagePaths()` takes only a Dataview source expression. A
full query such as `LIST FROM #project WHERE status = "active"` must use
`tryQuery()` or `tryQueryMarkdown()`.

## Recommended `bob-cli` Shape

Add a native subcommand:

```bash
bob dataview --query 'LIST FROM #project WHERE status = "active"'
bob dataview --format json --query 'TABLE file.path, status FROM #project'
bob dataview --format markdown --query-file query.dql
```

Suggested flags:

- `--query <DQL>`: query string.
- `--query-file <path>`: read query text from a file to avoid shell quoting.
- `--format paths|json|markdown`: default to `paths`, since the stated goal is
  "all notes that match".
- `--origin <vault-relative-path>`: origin file for `this` and relative links.
- `--vault <name-or-id>`: forwarded to Obsidian CLI as `vault=...`.
- `--sync`: run the existing `ob sync --path <vault>` gate before the query.
- `--strict-paths`: fail if a query result cannot be normalized to note paths.

Implementation outline:

1. Add `dataview` to the sorted `SUBCOMMANDS` table in `src/runner.rs` and route
   it to a native `NativeCommand::Dataview`.
2. Parse Dataview-specific flags inside a new native module rather than shelling
   through a script.
3. If `--sync` is set, reuse the existing `src/native/ob.rs` sync plumbing.
4. Spawn `obsidian` with arguments directly, not through a shell:

   ```bash
   obsidian vault=Bob eval code='<generated JavaScript>'
   ```

5. The generated JavaScript should:
   - find `app.plugins.plugins.dataview?.api ?? window.DataviewAPI`;
   - fail clearly if Dataview is disabled or the API is missing;
   - wait for `dataview:index-ready` on cold starts;
   - call `api.tryQuery(query, origin, { forceId: true })` for structured output;
   - call `api.tryQueryMarkdown(query, origin)` for Markdown output;
   - print one machine-readable JSON value to stdout.

Path extraction rules need to be explicit:

- For source-only input, `pagePaths(source)` is simplest and reliable.
- For `LIST`/`TABLE`, use `tryQuery(..., { forceId: true })` so Dataview keeps
  row identity where possible, then normalize Dataview links/ids to vault paths.
- For `TASK`, emit the task source paths and de-duplicate if the user asked for
  note paths rather than task rows.
- For grouped queries, `WITHOUT ID`, transformed rows, and some `CALENDAR`
  queries, there may not be a clean one-row-to-one-note meaning. In `paths`
  mode, either reject these under `--strict-paths` or return best-effort paths
  with warnings on stderr.

## Alternatives

### Local REST API

Prior research treated Local REST API as the best route for Dataview DQL. I would
not make that the default.

The current upstream Local REST API README/OpenAPI/source checked on
2026-06-03 documents `POST /search/` as JsonLogic search over note metadata and
does not contain a current `application/vnd.olrapi.dataview.dql+txt` handler.
The `dnvriend/obsidian-search-tool` project still assumes a Dataview `TABLE`
endpoint and documents significant limits: only `TABLE`, no `LIST`, `TASK`, or
`CALENDAR`, and no `GROUP BY` or `FLATTEN`.

This path is still worth testing if a specific Local REST API version supports
the Dataview DQL content type in Bryan's environment, but it should be treated as
an optional/pinned integration, not the base `bob-cli` design.

### `dynomark`

`k-lar/dynomark` is the strongest headless option. It is a Go binary that reads
Markdown directly and implements a Dataview-like query language. Its current
source reports version `0.2.1`; the README describes support for `LIST`, `TASK`,
`TABLE`, `TABLE NO ID`, `GROUP BY`, `LIMIT`, sorting, and metadata conditionals.

Use it when Obsidian cannot run. Do not assume exact Dataview compatibility.
Validate the specific query subset against known vault results before relying on
it for automation.

### In-Obsidian Export Plugins and Bases Tools

Dataview export/materialization plugins can write query results back into notes,
but they are not command-line query runners. Obsidian Bases-oriented tools such
as `mdbasequery` are also adjacent but not Dataview DQL.

## Recommendation

Implement `bob dataview` around Obsidian CLI `eval` first. It has the best
fidelity, uses the Dataview plugin already enabled in `~/bob`, and avoids adding
another Obsidian community plugin as a required dependency. Document that it
requires a running desktop Obsidian session.

For fully headless automation, do not promise "real Dataview". Add either:

- a `--engine dynomark` mode, clearly labeled as partial compatibility; or
- a small Bob-specific query subset in Rust if the real requirement is only
  "notes matching tags/frontmatter/inline fields".

Only revisit Local REST API after installing and testing the exact plugin version
against a `TABLE file.path FROM ...` smoke test, because the current upstream
source no longer verifies the DQL content-type claim from the earlier notes.

## Sources

- Dataview CLI discussion:
  https://github.com/blacksmithgu/obsidian-dataview/discussions/471
- Dataview JavaScript API reference:
  https://blacksmithgu.github.io/obsidian-dataview/api/code-reference/
- Dataview source expressions:
  https://blacksmithgu.github.io/obsidian-dataview/reference/sources/
- Obsidian CLI:
  https://obsidian.md/help/cli
- Obsidian Headless:
  https://obsidian.md/help/headless
- Local REST API:
  https://github.com/coddingtonbear/obsidian-local-rest-api
- `obsidian-search-tool`:
  https://github.com/dnvriend/obsidian-search-tool
- `dynomark`:
  https://github.com/k-lar/dynomark
