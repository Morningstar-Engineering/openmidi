#!/usr/bin/env python3
"""Ensure every cc entry in data/brands/**/*.yaml has a type.

Missing type values are filled with the default (variable). Existing values
are left unchanged. Pass file paths as arguments to limit the run; with no
arguments every brand YAML is processed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BRANDS_DIR = Path("data/brands")
DEFAULT_CC_TYPE = "variable"
TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:")
LIST_ITEM = re.compile(r"^( *)- ")


def discover_yaml_files() -> list[Path]:
    if not BRANDS_DIR.is_dir():
        return []
    return sorted(BRANDS_DIR.glob("*/*.yaml"))


def find_cc_section(lines: list[str]) -> tuple[int, int] | None:
    for index, line in enumerate(lines):
        match = TOP_LEVEL_KEY.match(line)
        if not match or match.group(1) not in ("cc", "data"):
            continue
        for end in range(index + 1, len(lines)):
            if TOP_LEVEL_KEY.match(lines[end]):
                return (index, end)
        return (index, len(lines))
    return None


def item_has_type(item_lines: list[str], key_indent: int) -> bool:
    type_re = re.compile(rf"^( {{{key_indent}}})type\s*:")
    for index, line in enumerate(item_lines):
        if index == 0:
            after = LIST_ITEM.match(line)
            if after and re.match(r"type\s*:", line[after.end() :]):
                return True
            continue
        if type_re.match(line.rstrip("\n")):
            return True
    return False


def ensure_item_type(item_lines: list[str], item_indent: int) -> tuple[list[str], bool]:
    key_indent = item_indent + 2
    if item_has_type(item_lines, key_indent):
        return item_lines, False

    insert_at = len(item_lines)
    while insert_at > 0 and not item_lines[insert_at - 1].strip():
        insert_at -= 1

    item_lines = list(item_lines)
    item_lines.insert(insert_at, f"{' ' * key_indent}type: {DEFAULT_CC_TYPE}\n")
    return item_lines, True


def process_cc_body(body: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    added = 0
    index = 0

    while index < len(body):
        line = body[index]
        match = LIST_ITEM.match(line)
        if not match:
            out.append(line)
            index += 1
            continue

        item_indent = len(match.group(1))
        item_lines = [line]
        index += 1
        while index < len(body):
            next_line = body[index]
            next_match = LIST_ITEM.match(next_line)
            if next_match and len(next_match.group(1)) == item_indent:
                break
            item_lines.append(next_line)
            index += 1

        updated, changed = ensure_item_type(item_lines, item_indent)
        if changed:
            added += 1
        out.extend(updated)

    return out, added


def process_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        text += "\n"
    lines = text.splitlines(keepends=True)

    section = find_cc_section(lines)
    if section is None:
        return 0

    start, end = section
    new_body, added = process_cc_body(lines[start + 1 : end])
    if added == 0:
        return 0

    new_text = "".join(lines[: start + 1] + new_body + lines[end:])
    path.write_text(new_text, encoding="utf-8")
    return added


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    paths = [Path(arg) for arg in args] if args else discover_yaml_files()

    if not paths:
        print("No brand YAML files found.")
        return 1

    files_changed = 0
    items_added = 0

    for path in paths:
        if not path.is_file():
            print(f"SKIP: {path} (not a file)")
            continue
        added = process_file(path)
        if added:
            files_changed += 1
            items_added += added
            print(f"UPDATED: {path} (+{added} type)")

    print(
        f"\n{files_changed} file(s) updated, "
        f"{items_added} missing type(s) set to {DEFAULT_CC_TYPE!r}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
