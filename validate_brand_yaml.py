#!/usr/bin/env python3
"""Structural validator for data/brands/**/*.yaml used in CI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

BRANDS_DIR = Path("data/brands")
MAPPING_PATH = Path("data/mapping.json")

REQUIRED_TOP_LEVEL = ("cc", "pc", "midi_channel")
ALLOWED_CC_TYPES = frozenset({"variable", "fixed", "group"})
ALLOWED_OPTIONAL_KEYS = {
    "brand",
    "device_name",
    "model",
    "url",
    "email",
    "midi_in",
    "midi_thru",
    "midi_clock",
    "phantom_power",
    "midi_mapping",
    "instructions",
    "device_type",
    "midi_inputs",
    "midi_outputs",
    "brandName",
    "modelName",
    "data",  # legacy alias for cc
}
KNOWN_TOP_LEVEL = set(REQUIRED_TOP_LEVEL) | ALLOWED_OPTIONAL_KEYS


class IssueCollector:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def warn(self, path: str, message: str) -> None:
        self.warnings.append(f"{path}: {message}")


def is_nullish(value: object) -> bool:
    return value is None


def is_string_or_null(value: object) -> bool:
    return value is None or isinstance(value, str)


def parse_midi_byte(value: object) -> int | None:
    """Return int 0-127 if value is a MIDI byte; None if not a number."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 127 else -1
    if isinstance(value, float) and value.is_integer():
        number = int(value)
        return number if 0 <= number <= 127 else -1
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            number = int(stripped, 10)
        except ValueError:
            return None
        return number if 0 <= number <= 127 else -1
    return None


def validate_midi_number_field(
    item_path: str, field: str, value: object, issues: IssueCollector
) -> None:
    """Accept 0-127 ints/numeric strings; non-numeric strings warn only."""
    if is_nullish(value):
        issues.error(item_path, f"'{field}' must not be null")
        return

    parsed = parse_midi_byte(value)
    if parsed is not None and parsed >= 0:
        return
    if parsed == -1:
        issues.error(
            item_path,
            f"'{field}' must be in 0-127 when numeric, got {value!r}",
        )
        return
    if isinstance(value, str) and value.strip():
        issues.warn(
            item_path,
            f"'{field}' is non-numeric ({value!r}); expected 0-127 for strict MIDI CC values",
        )
        return
    issues.error(
        item_path,
        f"'{field}' must be an integer or numeric string in 0-127, got {value!r}",
    )


def validate_cc_item(path: str, index: int, item: object, issues: IssueCollector) -> None:
    item_path = f"{path}:cc[{index}]"
    if not isinstance(item, dict):
        issues.error(item_path, "must be a mapping")
        return

    name = item.get("name")
    if "name" not in item:
        issues.error(item_path, "missing required field 'name'")
    elif not is_string_or_null(name):
        issues.error(item_path, "'name' must be a string")
    elif is_nullish(name) or (isinstance(name, str) and not name.strip()):
        issues.error(item_path, "'name' must be a non-empty string")

    for field in ("value", "min", "max"):
        if field not in item:
            issues.error(item_path, f"missing required field '{field}'")
        else:
            validate_midi_number_field(item_path, field, item[field], issues)

    if "description" in item and not is_string_or_null(item["description"]):
        issues.error(item_path, "'description' must be a string when present")

    if "type" not in item:
        issues.error(item_path, "missing required field 'type'")
    else:
        cc_type = item["type"]
        if not isinstance(cc_type, str):
            issues.error(item_path, "'type' must be a string")
        elif cc_type not in ALLOWED_CC_TYPES:
            allowed = " | ".join(sorted(ALLOWED_CC_TYPES))
            issues.error(
                item_path,
                f"'type' must be one of {allowed}, got {cc_type!r}",
            )


def validate_port_list(path: str, key: str, value: object, issues: IssueCollector) -> None:
    if not isinstance(value, list):
        issues.error(path, f"'{key}' must be a list when present")
        return

    for index, item in enumerate(value):
        item_path = f"{path}:{key}[{index}]"
        if not isinstance(item, dict):
            issues.error(item_path, "must be a mapping")
            continue
        if "name" not in item or not isinstance(item["name"], str):
            issues.error(item_path, "'name' must be a string")
        if "type" not in item or not isinstance(item["type"], str):
            issues.error(item_path, "'type' must be a string")


def validate_document(path: str, data: object, issues: IssueCollector) -> None:
    if not isinstance(data, dict):
        issues.error(path, "root must be a mapping")
        return

    for key in data:
        if key not in KNOWN_TOP_LEVEL:
            issues.warn(path, f"unknown top-level key '{key}'")

    cc_key = "cc"
    if "cc" not in data and "data" in data:
        issues.warn(path, "using legacy 'data' key as alias for 'cc'")
        cc_key = "data"
    elif "cc" not in data:
        issues.error(path, "missing required key 'cc'")
        cc_key = None

    if cc_key is not None:
        cc_list = data[cc_key]
        if not isinstance(cc_list, list):
            issues.error(path, f"'{cc_key}' must be a list")
        elif len(cc_list) == 0:
            issues.error(path, f"'{cc_key}' must be a non-empty list")
        else:
            for index, item in enumerate(cc_list):
                validate_cc_item(path, index, item, issues)

    if "pc" not in data:
        issues.error(path, "missing required key 'pc'")
    else:
        pc = data["pc"]
        if not isinstance(pc, dict):
            issues.error(path, "'pc' must be a mapping")
        elif "description" not in pc:
            issues.error(path, "'pc' must contain 'description'")
        elif not is_string_or_null(pc["description"]):
            issues.error(path, "'pc.description' must be a string")

    if "midi_channel" not in data:
        issues.error(path, "missing required key 'midi_channel'")
    else:
        midi_channel = data["midi_channel"]
        if not isinstance(midi_channel, dict):
            issues.error(path, "'midi_channel' must be a mapping")
        elif "instructions" not in midi_channel:
            issues.error(path, "'midi_channel' must contain 'instructions'")
        elif not is_string_or_null(midi_channel["instructions"]):
            issues.error(path, "'midi_channel.instructions' must be a string")

    if "midi_inputs" in data:
        validate_port_list(path, "midi_inputs", data["midi_inputs"], issues)
    if "midi_outputs" in data:
        validate_port_list(path, "midi_outputs", data["midi_outputs"], issues)


def load_yaml(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def mapped_yaml_paths(mapping: dict) -> set[str]:
    paths: set[str] = set()
    brands = mapping.get("brands")
    if not isinstance(brands, list):
        return paths

    for brand in brands:
        if not isinstance(brand, dict):
            continue
        brand_value = brand.get("value")
        models = brand.get("models")
        if not isinstance(brand_value, str) or not isinstance(models, list):
            continue
        for model in models:
            if not isinstance(model, dict):
                continue
            model_value = model.get("value")
            if isinstance(model_value, str):
                paths.add(f"data/brands/{brand_value}/{model_value}.yaml")
    return paths


def discover_yaml_files() -> list[Path]:
    if not BRANDS_DIR.is_dir():
        return []
    return sorted(BRANDS_DIR.glob("*/*.yaml"))


def is_brand_yaml_path(path: Path) -> bool:
    try:
        path.relative_to(BRANDS_DIR)
    except ValueError:
        return False
    return path.suffix == ".yaml" and len(path.parts) >= 4


def validate_yaml_file(
    path_str: str, mapped: set[str], issues: IssueCollector
) -> None:
    path = Path(path_str)

    if not path.is_file():
        issues.error(path_str, "file does not exist")
        return

    if path_str not in mapped:
        issues.error(path_str, "not listed in mapping.json")

    try:
        data = load_yaml(path)
    except yaml.YAMLError as exc:
        issues.error(path_str, f"invalid YAML: {exc}")
        return
    except OSError as exc:
        issues.error(path_str, f"could not read file: {exc}")
        return

    if data is None:
        issues.error(path_str, "file is empty")
        return

    validate_document(path_str, data, issues)


def load_mapping(issues: IssueCollector) -> dict | None:
    if not MAPPING_PATH.is_file():
        issues.error(str(MAPPING_PATH), "file not found")
        return None

    try:
        mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.error(str(MAPPING_PATH), f"invalid JSON: {exc}")
        return None

    if not isinstance(mapping, dict):
        issues.error(str(MAPPING_PATH), "root must be a mapping")
        return None

    return mapping


def validate_paths(paths: list[str], issues: IssueCollector) -> None:
    """Validate specific brand YAML paths (PR / selective mode)."""
    mapping = load_mapping(issues)
    if mapping is None:
        return

    mapped = mapped_yaml_paths(mapping)

    for raw in paths:
        path = Path(raw)
        path_str = str(path)
        if not is_brand_yaml_path(path):
            issues.error(path_str, "not a brand YAML under data/brands/")
            continue
        validate_yaml_file(path_str, mapped, issues)


def validate_all(issues: IssueCollector) -> None:
    """Validate every brand YAML and full mapping consistency."""
    mapping = load_mapping(issues)
    if mapping is None:
        return

    mapped = mapped_yaml_paths(mapping)
    on_disk = {str(path) for path in discover_yaml_files()}

    for path in sorted(mapped - on_disk):
        issues.error(path, "listed in mapping.json but file does not exist")

    for path in sorted(on_disk - mapped):
        issues.error(path, "YAML file exists but is not listed in mapping.json")

    for path_str in sorted(on_disk & mapped):
        validate_yaml_file(path_str, mapped, issues)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    issues = IssueCollector()

    if args:
        print(f"Validating {len(args)} file(s)...")
        validate_paths(args, issues)
    else:
        print("Validating all brand YAML files...")
        validate_all(issues)

    print_report(issues)
    return 1 if issues.errors else 0


def print_report(issues: IssueCollector) -> None:
    for warning in issues.warnings:
        print(f"WARNING: {warning}")
    for error in issues.errors:
        print(f"ERROR: {error}")

    print(
        f"\n{len(issues.errors)} error(s), {len(issues.warnings)} warning(s)"
    )


if __name__ == "__main__":
    sys.exit(main())
