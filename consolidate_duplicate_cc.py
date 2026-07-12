#!/usr/bin/env python3
"""Consolidate duplicate CC values in data/brands/**/*.yaml into grouped entries.

Before:
  - name: Bypass pedal
    value: '102'
    description: ''
    min: 0
    max: '0'
  - name: Engage pedal
    value: '102'
    description: ''
    min: '127'
    max: 127

After:
  - name: Bypass pedal / Engage pedal
    value: 102
    description: ''
    group:
      - name: Bypass pedal
        description: ''
        min: 0
        max: 0
      - name: Engage pedal
        description: ''
        min: 127
        max: 127

`value`, `min`, and `max` are always written as integers when numeric.

Usage:
  python3 consolidate_duplicate_cc.py              # dry-run report
  python3 consolidate_duplicate_cc.py --write      # rewrite files in place
  python3 consolidate_duplicate_cc.py --path data/brands/alexander/nowweareghosts.yaml --write
"""

from __future__ import annotations

import argparse
import sys
from collections import OrderedDict
from pathlib import Path

import yaml

BRANDS_DIR = Path("data/brands")
GROUP_ITEM_FIELDS = ("name", "description", "min", "max", "type")


class IndentListDumper(yaml.SafeDumper):
    """Indent list items under their parent key for readability."""


def _represent_str(dumper: yaml.Dumper, data: str):
    # Quote empty strings and values that look ambiguous as YAML.
    if data == "" or data.strip() != data or data.lower() in {"null", "true", "false", "yes", "no", "on", "off"}:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def _represent_none(dumper: yaml.Dumper, _data):
    return dumper.represent_scalar("tag:yaml.org,2002:null", "")


def _represent_list(dumper: yaml.Dumper, data):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=False)


def _represent_dict(dumper: yaml.Dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data, flow_style=False)


IndentListDumper.add_representer(str, _represent_str)
IndentListDumper.add_representer(type(None), _represent_none)
IndentListDumper.add_representer(list, _represent_list)
IndentListDumper.add_representer(dict, _represent_dict)
IndentListDumper.add_representer(OrderedDict, _represent_dict)


def increase_indent(self, flow=False, indentless=False):
    return super(IndentListDumper, self).increase_indent(flow, False)


IndentListDumper.increase_indent = increase_indent


def coerce_midi_number(value: object) -> object:
    """Return an int when value is a numeric MIDI byte; otherwise leave unchanged."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return value
        try:
            return int(stripped, 10)
        except ValueError:
            return value
    return value


def normalize_cc_value(value: object) -> str | None:
    """Normalize CC values so '102' and 102 group together."""
    coerced = coerce_midi_number(value)
    if isinstance(coerced, int):
        return str(coerced)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value) if value is not None else None


def join_names(names: list[str]) -> str:
    seen: list[str] = []
    for name in names:
        cleaned = name.strip() if isinstance(name, str) else str(name)
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return " / ".join(seen)


def join_descriptions(descriptions: list[object]) -> str:
    seen: list[str] = []
    for description in descriptions:
        if not isinstance(description, str):
            continue
        cleaned = description.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return "; ".join(seen)


def build_group_item(item: dict) -> dict:
    group_item: dict = {}
    for field in GROUP_ITEM_FIELDS:
        if field == "description":
            group_item["description"] = item.get("description") or ""
            continue
        if field not in item:
            continue
        if field in ("min", "max"):
            group_item[field] = coerce_midi_number(item[field])
        else:
            group_item[field] = item[field]
    return group_item


def normalize_cc_item_numbers(item: dict) -> tuple[dict, bool]:
    """Coerce value/min/max (and nested group min/max) to ints. Return (item, changed)."""
    changed = False
    updated = dict(item)

    if "value" in updated:
        coerced = coerce_midi_number(updated["value"])
        if coerced != updated["value"]:
            updated["value"] = coerced
            changed = True

    for field in ("min", "max"):
        if field not in updated:
            continue
        coerced = coerce_midi_number(updated[field])
        if coerced != updated[field]:
            updated[field] = coerced
            changed = True

    group = updated.get("group")
    if isinstance(group, list):
        new_group = []
        for nested in group:
            if isinstance(nested, dict):
                normalized, nested_changed = normalize_cc_item_numbers(nested)
                new_group.append(normalized)
                changed = changed or nested_changed
            else:
                new_group.append(nested)
        updated["group"] = new_group

    return updated, changed


def consolidate_cc_list(cc_list: list) -> tuple[list, list[dict], bool]:
    """Return (new_cc_list, change_summaries, numbers_coerced)."""
    buckets: OrderedDict[str, list[dict]] = OrderedDict()
    passthrough: list[tuple[int, object]] = []

    for index, item in enumerate(cc_list):
        if not isinstance(item, dict):
            passthrough.append((index, item))
            continue
        # Already grouped entries are left alone for grouping, then number-normalized.
        if "group" in item:
            key = normalize_cc_value(item.get("value"))
            if key is None:
                passthrough.append((index, item))
            else:
                buckets.setdefault(key, []).append(item)
            continue

        key = normalize_cc_value(item.get("value"))
        if key is None:
            passthrough.append((index, item))
            continue
        buckets.setdefault(key, []).append(item)

    changes: list[dict] = []
    consolidated: OrderedDict[str, dict] = OrderedDict()

    for key, items in buckets.items():
        # Skip items that are already grouped parents (single entry with group).
        if len(items) == 1 and "group" in items[0]:
            consolidated[key] = items[0]
            continue

        if len(items) == 1:
            consolidated[key] = items[0]
            continue

        # Flatten any pre-existing groups mixed into duplicates (unlikely).
        flat_items: list[dict] = []
        for item in items:
            if "group" in item and isinstance(item["group"], list):
                for nested in item["group"]:
                    if isinstance(nested, dict):
                        flat_items.append(nested)
            else:
                flat_items.append(item)

        first = items[0]
        names = []
        descriptions = []
        for item in flat_items:
            names.append(item.get("name") or "")
            descriptions.append(item.get("description"))

        parent = {
            "name": join_names(names),
            "value": coerce_midi_number(first.get("value")),
            "description": join_descriptions(descriptions),
            "group": [build_group_item(item) for item in flat_items],
        }
        consolidated[key] = parent
        changes.append(
            {
                "value": key,
                "count": len(flat_items),
                "name": parent["name"],
            }
        )

    # Rebuild list: preserve original order of first occurrence of each CC value,
    # and keep non-dict / valueless items in their original relative positions.
    result: list = []
    emitted_keys: set[str] = set()
    passthrough_by_index = {index: item for index, item in passthrough}
    numbers_coerced = False

    for index, item in enumerate(cc_list):
        if index in passthrough_by_index:
            passthrough_item = passthrough_by_index[index]
            if isinstance(passthrough_item, dict):
                passthrough_item, coerced = normalize_cc_item_numbers(passthrough_item)
                numbers_coerced = numbers_coerced or coerced
            result.append(passthrough_item)
            continue
        if not isinstance(item, dict):
            continue
        key = normalize_cc_value(item.get("value"))
        if key is None or key in emitted_keys:
            continue
        emitted_keys.add(key)
        normalized, coerced = normalize_cc_item_numbers(consolidated[key])
        numbers_coerced = numbers_coerced or coerced
        result.append(normalized)

    return result, changes, numbers_coerced


def dump_cc_block(cc_key: str, cc_list: list) -> str:
    """Dump only the cc/data section so other YAML keys keep their original formatting."""
    return yaml.dump(
        {cc_key: cc_list},
        Dumper=IndentListDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=1000,
    )


def find_top_level_block(text: str, key: str) -> tuple[int, int] | None:
    """Return [start, end) character offsets for a top-level YAML key block."""
    lines = text.splitlines(keepends=True)
    start_line: int | None = None
    for index, line in enumerate(lines):
        if line == f"{key}:\n" or line == f"{key}:\r\n" or line == f"{key}:":
            start_line = index
            break
        if line.startswith(f"{key}:") and not line[len(key) + 1 :].strip():
            start_line = index
            break

    if start_line is None:
        return None

    end_line = len(lines)
    for index in range(start_line + 1, len(lines)):
        line = lines[index]
        # Next top-level key (non-empty, no leading whitespace).
        if line.strip() and not line[0].isspace() and not line.startswith("#"):
            end_line = index
            break

    start = sum(len(line) for line in lines[:start_line])
    end = sum(len(line) for line in lines[:end_line])
    return start, end


def replace_cc_block(text: str, cc_key: str, cc_list: list) -> str:
    span = find_top_level_block(text, cc_key)
    if span is None:
        raise ValueError(f"Could not find top-level '{cc_key}:' block to replace")

    start, end = span
    new_block = dump_cc_block(cc_key, cc_list)
    if not new_block.endswith("\n"):
        new_block += "\n"

    # Preserve a blank line that originally separated this block from the next key.
    suffix = text[end:]
    if suffix.startswith("\n") and not new_block.endswith("\n\n"):
        # Original had an extra blank line after the block; keep file structure tidy
        # by not inventing blanks—only preserve if the following content already has one.
        pass

    return text[:start] + new_block + text[end:]


def process_file(path: Path, write: bool) -> tuple[bool, list[dict], bool]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return False, [], False

    cc_key = "cc" if "cc" in data else ("data" if "data" in data else None)
    if cc_key is None:
        return False, [], False

    cc_list = data[cc_key]
    if not isinstance(cc_list, list) or not cc_list:
        return False, [], False

    new_cc, changes, numbers_coerced = consolidate_cc_list(cc_list)
    if not changes and not numbers_coerced:
        return False, [], False

    if write:
        path.write_text(replace_cc_block(text, cc_key, new_cc), encoding="utf-8")

    return True, changes, numbers_coerced


def discover_paths(explicit: str | None) -> list[Path]:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise SystemExit(f"Path not found: {path}")
        return [path]
    if not BRANDS_DIR.is_dir():
        raise SystemExit(f"Brands directory not found: {BRANDS_DIR}")
    return sorted(BRANDS_DIR.glob("*/*.yaml"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolidate duplicate MIDI CC values into grouped YAML entries."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite YAML files in place. Without this flag, only report changes.",
    )
    parser.add_argument(
        "--path",
        help="Optional single YAML file (or brand folder) to process.",
    )
    args = parser.parse_args()

    paths = discover_paths(args.path)
    if args.path:
        path = Path(args.path)
        if path.is_dir():
            paths = sorted(path.glob("*.yaml"))

    touched = 0
    total_groups = 0
    numeric_only = 0

    for path in paths:
        changed, changes, numbers_coerced = process_file(path, write=args.write)
        if not changed:
            continue
        touched += 1
        total_groups += len(changes)
        if numbers_coerced and not changes:
            numeric_only += 1
        action = "Updated" if args.write else "Would update"
        details = []
        if changes:
            details.append(f"{len(changes)} grouped CC value(s)")
        if numbers_coerced:
            details.append("coerced string value/min/max to int")
        print(f"{action} {path} ({', '.join(details)})")
        for change in changes:
            print(
                f"  CC {change['value']}: {change['count']} entries -> {change['name']!r}"
            )

    mode = "Wrote" if args.write else "Dry-run:"
    print(
        f"\n{mode} {touched} file(s), {total_groups} duplicate CC value(s) "
        f"{'consolidated' if args.write else 'to consolidate'}"
        f"{f', {numeric_only} file(s) numeric-only' if numeric_only else ''}."
    )
    if not args.write and touched:
        print("Re-run with --write to apply changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
