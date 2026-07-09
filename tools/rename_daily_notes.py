#!/usr/bin/env python3
"""Migrate Bob daily notes from YYYYMMDD_day.md to YYYYMMDD.md."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


VAULT_DEFAULT = Path.home() / "bob"
DAILY_RE = re.compile(r"^(?P<year>\d{4})/(?P<date>\d{8})_day\.md$")
BARE_RE = re.compile(r"^\d{4}/\d{8}\.md$")
POMS_RE = re.compile(r"^\d{4}/\d{8}_poms\.md$")
HABIT_RE = re.compile(r"^\d{4}/\d{8}_habit\.md$")
FULL_DAY_LINK_RE = re.compile(r"^(?P<year>\d{4})/(?P<date>\d{8})_day(?P<ext>\.md)?$")
SAME_FOLDER_DAY_LINK_RE = re.compile(r"^(?P<date>\d{8})_day(?P<ext>\.md)?$")
WIKI_LINK_RE = re.compile(r"(!?)\[\[([^\]\n]+)\]\]")


@dataclass(frozen=True)
class RenameAction:
    source: str
    target: str
    action: str
    source_dirty: bool
    target_dirty: bool


@dataclass(frozen=True)
class Blocker:
    source: str
    target: str
    reason: str


def vault_relative(path: Path, vault: Path) -> str:
    return path.relative_to(vault).as_posix()


def markdown_files(vault: Path) -> list[Path]:
    return sorted(path for path in vault.rglob("*.md") if path.is_file())


def daily_source_files(vault: Path) -> list[Path]:
    files = []
    for path in vault.glob("[0-9][0-9][0-9][0-9]/*_day.md"):
        rel = vault_relative(path, vault)
        match = DAILY_RE.match(rel)
        if match and match.group("date").startswith(match.group("year")):
            files.append(path)
    return sorted(files)


def inventory_counts(vault: Path) -> dict[str, int]:
    counts = {
        "daily_day": 0,
        "bare": 0,
        "poms": 0,
        "habit": 0,
    }
    for path in vault.glob("[0-9][0-9][0-9][0-9]/*.md"):
        rel = vault_relative(path, vault)
        if DAILY_RE.match(rel):
            counts["daily_day"] += 1
        if BARE_RE.match(rel):
            counts["bare"] += 1
        if POMS_RE.match(rel):
            counts["poms"] += 1
        if HABIT_RE.match(rel):
            counts["habit"] += 1
    return counts


def git_dirty_paths(vault: Path) -> dict[str, str]:
    result = subprocess.run(
        ["git", "-C", str(vault), "status", "--porcelain=v1", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    if result.returncode != 0:
        return {}

    entries = result.stdout.decode("utf-8", errors="replace").split("\0")
    dirty = {}
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:]
        dirty[path] = status
        if status[0] in {"R", "C"} or status[1] in {"R", "C"}:
            index += 1
    return dirty


def date_parts_from_rel(rel: str) -> tuple[str, str] | None:
    match = DAILY_RE.match(rel)
    if not match:
        return None
    return match.group("year"), match.group("date")


def target_for_source(rel: str) -> str:
    year, date = date_parts_from_rel(rel) or ("", "")
    return f"{year}/{date}.md"


def iso_date(date_text: str) -> str:
    return f"{date_text[:4]}-{date_text[4:6]}-{date_text[6:8]}"


def frontmatter_bounds(text: str) -> tuple[int, int] | None:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    offset = len(lines[0])
    for line in lines[1:]:
        next_offset = offset + len(line)
        if line.strip() in {"---", "..."}:
            return 0, next_offset
        offset = next_offset
    return None


def is_generated_all_day_hub(path: Path, target_rel: str) -> bool:
    date_text = Path(target_rel).stem
    text = path.read_text(encoding="utf-8", errors="replace")
    bounds = frontmatter_bounds(text)
    if not bounds:
        return False

    frontmatter = text[bounds[0] : bounds[1]]
    body = text[bounds[1] :]
    if "generated_from_zorg: true" not in frontmatter:
        return False
    if f'zorg_source: "{target_rel.removesuffix(".md")}.zo"' not in frontmatter:
        return False

    nonempty_body_lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not nonempty_body_lines:
        return False
    if nonempty_body_lines[0] != f"All journal / log files from {iso_date(date_text)}":
        return False
    if "Related notes:" not in nonempty_body_lines:
        return False
    if "- [[zot/all_day_logs.zot]]" not in nonempty_body_lines:
        return False

    allowed_exact = {
        f"All journal / log files from {iso_date(date_text)}",
        "Related notes:",
    }
    return all(
        line in allowed_exact or re.fullmatch(r"- \[\[[^\]\n]+\]\]", line)
        for line in nonempty_body_lines
    )


def rewrite_link_path(path_text: str) -> str:
    match = FULL_DAY_LINK_RE.match(path_text)
    if match and match.group("date").startswith(match.group("year")):
        return f"{match.group('year')}/{match.group('date')}{match.group('ext') or ''}"

    match = SAME_FOLDER_DAY_LINK_RE.match(path_text)
    if match:
        return f"{match.group('date')}{match.group('ext') or ''}"

    return path_text


def rewrite_wiki_link_inner(inner: str) -> str:
    target_with_subpath, separator, alias = inner.partition("|")
    target_path, hash_separator, subpath = target_with_subpath.partition("#")
    next_target_path = rewrite_link_path(target_path)
    if next_target_path == target_path:
        return inner
    return f"{next_target_path}{hash_separator}{subpath}{separator}{alias}"


def rewrite_wiki_links(text: str) -> tuple[str, int]:
    replacements = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal replacements
        inner = match.group(2)
        next_inner = rewrite_wiki_link_inner(inner)
        if next_inner == inner:
            return match.group(0)
        replacements += 1
        return f"{match.group(1)}[[{next_inner}]]"

    return WIKI_LINK_RE.sub(replace, text), replacements


def rewrite_daily_metadata(text: str, year: str, date_text: str) -> str:
    month_rel = f"{year}/{date_text[:6]}"
    text = re.sub(
        rf"(?m)^id:\s*['\"]?{re.escape(date_text)}_day['\"]?\s*$",
        f"id: {date_text}",
        text,
    )
    text = re.sub(
        rf"(?m)^parent:\s*(['\"]?)\[\[(?:{re.escape(year)}/)?{re.escape(date_text)}\]\]\1\s*$",
        f"parent: [[{month_rel}]]",
        text,
    )
    text = text.replace(
        'moment(query.file.filenameWithoutExtension, "YYYYMMDD[_day]")',
        'moment(query.file.filenameWithoutExtension, "YYYYMMDD")',
    )
    return text


def transform_daily_source(text: str, source_rel: str) -> tuple[str, int]:
    parts = date_parts_from_rel(source_rel)
    if not parts:
        return rewrite_wiki_links(text)
    year, date_text = parts
    text, replacements = rewrite_wiki_links(text)
    return rewrite_daily_metadata(text, year, date_text), replacements


def build_plan(vault: Path) -> tuple[dict[str, object], list[RenameAction], list[Blocker]]:
    dirty_paths = git_dirty_paths(vault)
    actions: list[RenameAction] = []
    blockers: list[Blocker] = []

    for source in daily_source_files(vault):
        source_rel = vault_relative(source, vault)
        target_rel = target_for_source(source_rel)
        target = vault / target_rel
        source_dirty = source_rel in dirty_paths
        target_dirty = target_rel in dirty_paths

        if not target.exists():
            actions.append(
                RenameAction(source_rel, target_rel, "rename", source_dirty, False)
            )
            continue

        if target_dirty:
            blockers.append(Blocker(source_rel, target_rel, "target path is dirty"))
            continue

        if is_generated_all_day_hub(target, target_rel):
            actions.append(
                RenameAction(
                    source_rel,
                    target_rel,
                    "replace_generated_hub",
                    source_dirty,
                    False,
                )
            )
            continue

        blockers.append(
            Blocker(source_rel, target_rel, "target is not a generated all-day hub")
        )

    summary = {
        "vault": str(vault),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inventory": inventory_counts(vault),
        "dirty_paths": dirty_paths,
        "actions": {
            "rename": sum(1 for action in actions if action.action == "rename"),
            "replace_generated_hub": sum(
                1 for action in actions if action.action == "replace_generated_hub"
            ),
        },
        "source_dirty_count": sum(1 for action in actions if action.source_dirty),
        "blocker_count": len(blockers),
    }
    return summary, actions, blockers


def changed_link_files(vault: Path, source_rels: set[str], target_rels: set[str]) -> int:
    changed = 0
    for path in markdown_files(vault):
        rel = vault_relative(path, vault)
        if rel in target_rels:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if rel in source_rels:
            next_text, _ = transform_daily_source(text, rel)
        else:
            next_text, _ = rewrite_wiki_links(text)
        if next_text != text:
            changed += 1
    return changed


def write_report(
    report_path: Path | None,
    summary: dict[str, object],
    actions: list[RenameAction],
    blockers: list[Blocker],
    link_rewrite_file_count: int,
) -> None:
    payload = {
        **summary,
        "link_rewrite_file_count": link_rewrite_file_count,
        "planned_actions": [action.__dict__ for action in actions],
        "blockers": [blocker.__dict__ for blocker in blockers],
    }
    output = json.dumps(payload, indent=2, sort_keys=True)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(output + "\n", encoding="utf-8")
    print(output)


def apply_migration(vault: Path, actions: list[RenameAction]) -> dict[str, int]:
    source_rels = {action.source for action in actions}
    target_rels_to_replace = {
        action.target for action in actions if action.action == "replace_generated_hub"
    }
    transformed_files = 0
    rewritten_links = 0

    for path in markdown_files(vault):
        rel = vault_relative(path, vault)
        if rel in target_rels_to_replace:
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        if rel in source_rels:
            next_text, link_count = transform_daily_source(text, rel)
        else:
            next_text, link_count = rewrite_wiki_links(text)

        if next_text != text:
            path.write_text(next_text, encoding="utf-8")
            transformed_files += 1
            rewritten_links += link_count

    renamed = 0
    replaced = 0
    for action in actions:
        source = vault / action.source
        target = vault / action.target
        if action.action == "replace_generated_hub":
            target.unlink()
            replaced += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        renamed += 1

    return {
        "transformed_files": transformed_files,
        "rewritten_links": rewritten_links,
        "renamed_daily_notes": renamed,
        "replaced_generated_hubs": replaced,
    }


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename Bob daily notes from *_day.md to bare date notes.",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=VAULT_DEFAULT,
        help=f"Bob vault path (default: {VAULT_DEFAULT})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Write audit JSON to this path.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the migration. Without this flag, only audit.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    vault = args.vault.expanduser().resolve()
    if not vault.is_dir():
        print(f"vault does not exist: {vault}", file=sys.stderr)
        return 2

    summary, actions, blockers = build_plan(vault)
    source_rels = {action.source for action in actions}
    target_rels_to_replace = {
        action.target for action in actions if action.action == "replace_generated_hub"
    }
    link_rewrite_file_count = changed_link_files(vault, source_rels, target_rels_to_replace)
    write_report(args.report, summary, actions, blockers, link_rewrite_file_count)

    if blockers:
        print("migration blocked; see blockers in audit report", file=sys.stderr)
        return 1

    if not args.apply:
        return 0

    result = apply_migration(vault, actions)
    print(json.dumps({"applied": result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
