#!/usr/bin/env python3
"""Expand CC descriptions that encode discrete values into grouped entries.

Before:
  - name: Engage Preset A
    value: 10
    description: 'Value 0 = Do Nothing, 1 = On Press, 2 = On Release, ...'
    min: 0
    max: 10

After:
  - name: Engage Preset A
    value: 10
    description: ''
    group:
      - name: Do Nothing
        description: ''
        min: 0
        max: 0
      - name: On Press
        description: ''
        min: 1
        max: 1
      ...

Supports:
  - Inline: "Value 0 = A, 1 = B, 2 = C"
  - Multiline: "0 = A\\n1 = B"
  - Prefixed: "Values 0 = Off, 1 = On"
  - Sectioned: only the text after "CC Values:" when present

Skips continuous/range prose (ellipsis, dB/%, "and so on") and entries that
already have a group.

Usage:
  python3 expand_cc_description_groups.py
  python3 expand_cc_description_groups.py --write
  python3 expand_cc_description_groups.py --path data/brands/morningstarengineering/mc4pro.yaml --write
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from consolidate_duplicate_cc import coerce_midi_number, replace_cc_block

BRANDS_DIR = Path("data/brands")

# Multiline: optional bullet, optional "Value(s)" / "CC Value(s)" prefix.
LINE_PAIR_RE = re.compile(
    r"^\s*(?:[•\-\*]?\s*)?(?:(?:CC\s+)?Values?\s+)?"
    r"(\d+)\s*=\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Inline comma-separated pairs.
INLINE_PAIR_RE = re.compile(
    r"(?:(?:CC\s+)?Values?\s+)?"
    r"(\d+)\s*=\s*"
    r"([^,;]+?)"
    r"(?=(?:\s*,\s*(?:(?:CC\s+)?Values?\s+)?\d+\s*=)|\s*$|\s*;)",
    re.IGNORECASE,
)

CONTINUOUS_HINT_RE = re.compile(
    r"(\.\.\.|…|\b(?:dB|dBFS|inf|%|and so on|etc\.?)\b)",
    re.IGNORECASE,
)
CC_VALUES_SECTION_RE = re.compile(r"\bCC\s+Values?\s*:\s*", re.IGNORECASE)
CC_NUMBERS_SECTION_RE = re.compile(r"\bCC\s+Numbers?\s*:\s*", re.IGNORECASE)


def extract_enum_text(description: str) -> str | None:
    """Return the portion of description that lists discrete CC values, or None."""
    text = description.strip()
    if not text:
        return None

    if CONTINUOUS_HINT_RE.search(text):
        return None

    values_match = CC_VALUES_SECTION_RE.search(text)
    if values_match:
        return text[values_match.end() :].strip()

    # Documents other CC numbers, not discrete values for this control.
    if CC_NUMBERS_SECTION_RE.search(text):
        return None

    return text


def parse_value_pairs(description: str) -> list[tuple[int, str]]:
    """Parse discrete `N = label` pairs from a CC description."""
    if not isinstance(description, str):
        return []

    enum_text = extract_enum_text(description)
    if not enum_text:
        return []

    line_matches = list(LINE_PAIR_RE.finditer(enum_text))
    # Prefer line-oriented parsing when the description is multiline with several pairs.
    if enum_text.count("\n") >= 1 and len(line_matches) >= 2:
        raw_pairs = [(int(m.group(1)), m.group(2)) for m in line_matches]
    else:
        compact = " ".join(enum_text.split())
        raw_pairs = [
            (int(m.group(1)), m.group(2)) for m in INLINE_PAIR_RE.finditer(compact)
        ]

    pairs: list[tuple[int, str]] = []
    seen: set[int] = set()
    for number, label in raw_pairs:
        cleaned = label.strip().rstrip(";,").strip()
        cleaned = re.sub(r"^(?:Value|Values)\s+", "", cleaned, flags=re.IGNORECASE)
        if not cleaned or number in seen:
            continue
        if not (0 <= number <= 127):
            continue
        seen.add(number)
        pairs.append((number, cleaned))

    return pairs


def residual_description(description: str, pairs: list[tuple[int, str]]) -> str:
    """Parent description is cleared once values are expanded into the group."""
    return ""


def build_group_item(number: int, label: str) -> dict:
    return {
        "name": label,
        "description": "",
        "min": number,
        "max": number,
    }


def expand_cc_item(item: dict) -> tuple[dict | None, list[tuple[int, str]]]:
    """Return expanded item and pairs, or (None, []) if not expandable."""
    if not isinstance(item, dict):
        return None, []
    if "group" in item:
        return None, []

    description = item.get("description") or ""
    pairs = parse_value_pairs(description)
    if len(pairs) < 2:
        return None, []

    parent: dict = {
        "name": item.get("name") or "",
        "value": coerce_midi_number(item.get("value")),
        "description": residual_description(description, pairs),
    }
    if "type" in item:
        parent["type"] = item["type"]
    parent["group"] = [build_group_item(number, label) for number, label in pairs]
    return parent, pairs


def expand_cc_list(cc_list: list) -> tuple[list, list[dict]]:
    result: list = []
    changes: list[dict] = []

    for item in cc_list:
        expanded, pairs = expand_cc_item(item if isinstance(item, dict) else {})
        if expanded is None:
            # Still coerce numbers on untouched items when we rewrite the block.
            if isinstance(item, dict):
                updated = dict(item)
                for field in ("value", "min", "max"):
                    if field in updated:
                        updated[field] = coerce_midi_number(updated[field])
                result.append(updated)
            else:
                result.append(item)
            continue

        result.append(expanded)
        changes.append(
            {
                "name": expanded["name"],
                "value": expanded["value"],
                "count": len(pairs),
                "labels": [label for _, label in pairs],
            }
        )

    return result, changes


def process_file(path: Path, write: bool) -> tuple[bool, list[dict]]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return False, []

    cc_key = "cc" if "cc" in data else ("data" if "data" in data else None)
    if cc_key is None:
        return False, []

    cc_list = data[cc_key]
    if not isinstance(cc_list, list) or not cc_list:
        return False, []

    new_cc, changes = expand_cc_list(cc_list)
    if not changes:
        return False, []

    if write:
        path.write_text(replace_cc_block(text, cc_key, new_cc), encoding="utf-8")

    return True, changes


def discover_paths(explicit: str | None) -> list[Path]:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise SystemExit(f"Path not found: {path}")
        if path.is_dir():
            return sorted(path.glob("*.yaml"))
        return [path]
    if not BRANDS_DIR.is_dir():
        raise SystemExit(f"Brands directory not found: {BRANDS_DIR}")
    return sorted(BRANDS_DIR.glob("*/*.yaml"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Expand discrete value lists in CC descriptions into group entries."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite YAML files in place. Without this flag, only report changes.",
    )
    parser.add_argument(
        "--path",
        help="Optional single YAML file or brand folder to process.",
    )
    args = parser.parse_args()

    paths = discover_paths(args.path)
    touched = 0
    total = 0

    for path in paths:
        changed, changes = process_file(path, write=args.write)
        if not changed:
            continue
        touched += 1
        total += len(changes)
        action = "Updated" if args.write else "Would update"
        print(f"{action} {path} ({len(changes)} CC description(s) expanded)")
        for change in changes:
            labels = ", ".join(change["labels"][:5])
            more = "" if len(change["labels"]) <= 5 else f", … +{len(change['labels']) - 5}"
            print(
                f"  CC {change['value']} {change['name']!r}: "
                f"{change['count']} values -> {labels}{more}"
            )

    mode = "Wrote" if args.write else "Dry-run:"
    print(
        f"\n{mode} {touched} file(s), {total} CC description(s) "
        f"{'expanded' if args.write else 'to expand'}."
    )
    if not args.write and touched:
        print("Re-run with --write to apply changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
