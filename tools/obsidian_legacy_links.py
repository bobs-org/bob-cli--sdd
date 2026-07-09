#!/usr/bin/env python3
"""Migrate legacy Zorg parent/shortcut links in the Obsidian vault."""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


LEGACY_PARENT_RE = re.compile(r"^# \^ = (?P<link>\[\[[^\]\n]+\]\])(?P<trailing>.*)$")
SHORTCUT_RE = re.compile(r"^# (?P<key>[A-Za-z0-9<>@]) = (?P<link>\[\[[^\]\n]+\]\])(?P<trailing>.*)$")
PARENT_FIELD_RE = re.compile(r"^parent:\s*(?P<value>.*)$")


@dataclass
class MigrationResult:
    path: Path
    original: str
    migrated: str
    parent: str
    generated: bool
    added_parent: bool
    removed_parent_lines: int
    related_notes: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vault",
        type=Path,
        default=Path("~/bob").expanduser(),
        help="Obsidian vault path.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write migrated files. Without this flag, only report what would change.",
    )
    parser.add_argument(
        "--diff",
        action="append",
        default=[],
        metavar="PATH",
        help="Print a unified diff for PATH. May be passed more than once.",
    )
    return parser.parse_args()


def affected_files(vault: Path) -> list[Path]:
    cmd = ["rg", "# \\^ = ", str(vault), "-l"]
    completed = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if completed.returncode == 1:
        return []
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"`{' '.join(cmd)}` failed")
    return [Path(line) for line in completed.stdout.splitlines() if line]


def split_frontmatter(lines: list[str], path: Path) -> tuple[int, int]:
    if not lines or lines[0].rstrip("\n") != "---":
        raise ValueError(f"{path}: missing YAML frontmatter")
    for index in range(1, len(lines)):
        if lines[index].rstrip("\n") == "---":
            return 0, index
    raise ValueError(f"{path}: unterminated YAML frontmatter")


def normalize_parent(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1].strip()
    return value


def find_frontmatter_parent(lines: list[str], start: int, end: int, path: Path) -> tuple[int | None, str | None]:
    parent_index = None
    parent_value = None
    for index in range(start + 1, end):
        match = PARENT_FIELD_RE.match(lines[index].rstrip("\n"))
        if not match:
            continue
        if parent_index is not None:
            raise ValueError(f"{path}: multiple parent fields in YAML frontmatter")
        parent_index = index
        parent_value = normalize_parent(match.group("value"))
    return parent_index, parent_value


def first_legacy_parent(lines: list[str], path: Path) -> str:
    for line in lines:
        match = LEGACY_PARENT_RE.match(line.rstrip("\n"))
        if match:
            return match.group("link")
    raise ValueError(f"{path}: no parseable legacy parent line")


def add_parent_field(lines: list[str], fm_start: int, fm_end: int, parent: str, path: Path) -> bool:
    parent_index, existing_parent = find_frontmatter_parent(lines, fm_start, fm_end, path)
    if parent_index is None:
        lines.insert(fm_end, f"parent: {parent}\n")
        return True
    if existing_parent != parent:
        raise ValueError(f"{path}: existing parent {existing_parent!r} conflicts with legacy parent {parent!r}")
    return False


def strip_parent_trailing_text(trailing: str) -> str:
    text = trailing.strip()
    if text.startswith("|") or text.startswith(":"):
        text = text[1:].strip()
    return text


def rewrite_normal_body(lines: list[str], body_start: int, path: Path) -> tuple[list[str], int, int]:
    block_end = body_start
    saw_parent = False
    while block_end < len(lines):
        line = lines[block_end]
        stripped = line.rstrip("\n")
        if stripped == "":
            if saw_parent:
                next_index = next_nonblank_index(lines, block_end + 1)
                if next_index is None:
                    break
                next_stripped = lines[next_index].rstrip("\n")
                if next_stripped != "#" and not next_stripped.startswith("# "):
                    break
            block_end += 1
            continue
        if LEGACY_PARENT_RE.match(stripped):
            saw_parent = True
            block_end += 1
            continue
        if stripped == "#" or stripped.startswith("# "):
            block_end += 1
            continue
        if saw_parent:
            break
        raise ValueError(f"{path}: unsupported line before normal-note legacy parent: {stripped!r}")

    block = lines[body_start:block_end]
    if not any(LEGACY_PARENT_RE.match(line.rstrip("\n")) for line in block):
        raise ValueError(f"{path}: normal-note legacy parent is outside the initial block")

    prefix: list[str] = []
    related: list[str] = []
    removed_parent_lines = 0

    for line in block:
        stripped = line.rstrip("\n")
        if stripped == "":
            prefix.append("\n")
            continue
        if stripped == "#":
            continue

        parent_match = LEGACY_PARENT_RE.match(stripped)
        if parent_match:
            removed_parent_lines += 1
            trailing_text = strip_parent_trailing_text(parent_match.group("trailing"))
            if trailing_text:
                prefix.append(f"{trailing_text}\n")
            continue

        shortcut_match = SHORTCUT_RE.match(stripped)
        if shortcut_match:
            link_text = shortcut_match.group("link") + shortcut_match.group("trailing").rstrip()
            related.append(f"- {link_text}\n")
            continue

        if stripped.startswith("# "):
            prefix.append(f"{stripped[2:]}\n")
            continue

        raise ValueError(f"{path}: unsupported legacy block line: {stripped!r}")

    replacement: list[str] = []
    replacement.extend(trim_blank_edges(prefix))
    if related:
        if replacement:
            replacement.append("\n")
        replacement.append("Related notes:\n")
        replacement.extend(related)

    return lines[:body_start] + replacement + lines[block_end:], removed_parent_lines, len(related)


def trim_blank_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and lines[start].strip() == "":
        start += 1
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    return lines[start:end]


def next_nonblank_index(lines: list[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def rewrite_generated_body(lines: list[str], path: Path, parent: str) -> tuple[list[str], int, int]:
    migrated: list[str] = []
    removed_parent_lines = 0
    for line in lines:
        match = LEGACY_PARENT_RE.match(line.rstrip("\n"))
        if match and match.group("link") == parent:
            removed_parent_lines += 1
            continue
        migrated.append(line)
    if removed_parent_lines == 0:
        raise ValueError(f"{path}: generated snapshot had no matching legacy parent line to remove")
    return migrated, removed_parent_lines, 0


def migrate_file(path: Path, vault: Path) -> MigrationResult:
    original = path.read_text()
    lines = original.splitlines(keepends=True)
    fm_start, fm_end = split_frontmatter(lines, path)
    parent = first_legacy_parent(lines, path)
    added_parent = add_parent_field(lines, fm_start, fm_end, parent, path)
    if added_parent:
        fm_end += 1

    generated = is_generated_snapshot(path, vault)
    if generated:
        migrated_lines, removed_parent_lines, related_notes = rewrite_generated_body(lines, path, parent)
    else:
        migrated_lines, removed_parent_lines, related_notes = rewrite_normal_body(lines, fm_end + 1, path)

    migrated = "".join(migrated_lines)
    return MigrationResult(
        path=path,
        original=original,
        migrated=migrated,
        parent=parent,
        generated=generated,
        added_parent=added_parent,
        removed_parent_lines=removed_parent_lines,
        related_notes=related_notes,
    )


def is_generated_snapshot(path: Path, vault: Path) -> bool:
    try:
        relative = path.relative_to(vault)
    except ValueError:
        return False
    return len(relative.parts) >= 2 and relative.parts[:2] == ("_generated", "queries")


def print_summary(results: list[MigrationResult], write: bool) -> None:
    changed = [result for result in results if result.original != result.migrated]
    print(f"mode: {'write' if write else 'dry-run'}")
    print(f"affected files: {len(results)}")
    print(f"changed files: {len(changed)}")
    print(f"normal notes: {sum(not result.generated for result in results)}")
    print(f"generated snapshots: {sum(result.generated for result in results)}")
    print(f"parent fields added: {sum(result.added_parent for result in results)}")
    print(f"existing matching parent fields kept: {sum(not result.added_parent for result in results)}")
    print(f"legacy parent lines removed: {sum(result.removed_parent_lines for result in results)}")
    print(f"related-note items created: {sum(result.related_notes for result in results)}")


def print_diffs(results: list[MigrationResult], diff_paths: list[str], vault: Path) -> None:
    if not diff_paths:
        return
    by_resolved_path = {result.path.resolve(): result for result in results}
    for requested in diff_paths:
        path = Path(requested).expanduser()
        if not path.is_absolute():
            path = vault / path
        result = by_resolved_path.get(path.resolve())
        if result is None:
            print(f"\n--- no diff: {path} was not affected ---")
            continue
        print()
        sys.stdout.writelines(
            difflib.unified_diff(
                result.original.splitlines(keepends=True),
                result.migrated.splitlines(keepends=True),
                fromfile=str(result.path),
                tofile=str(result.path),
                n=8,
            )
        )


def main() -> int:
    args = parse_args()
    vault = args.vault.expanduser().resolve()
    paths = affected_files(vault)

    results: list[MigrationResult] = []
    errors: list[str] = []
    for path in paths:
        try:
            results.append(migrate_file(path, vault))
        except Exception as exc:  # noqa: BLE001 - batch validation should report every offending file.
            errors.append(str(exc))

    if errors:
        print("aborting; migration validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print_summary(results, args.write)
    print_diffs(results, args.diff, vault)

    if args.write:
        for result in results:
            if result.original != result.migrated:
                result.path.write_text(result.migrated)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
