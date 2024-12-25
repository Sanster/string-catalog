import json
from typing import List
from pathlib import Path

from .models import StringCatalog, TranslationState


def find_catalog_files(path: Path) -> List[Path]:
    """Find all .xcstrings files in the given path"""
    if path.is_file() and path.suffix == ".xcstrings":
        return [path]

    return [p for p in path.rglob("*.xcstrings") if "translated" not in p.name]


def save_catalog(catalog: StringCatalog, save_path: Path):
    with open(save_path, "w") as f:
        json.dump(
            catalog.model_dump(by_alias=True, exclude_none=True),
            f,
            ensure_ascii=False,
            separators=(",", " : "),
            indent=2,
        )


def update_string_unit_state(data, old: TranslationState, new: TranslationState):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "stringUnit" and "state" in value:
                if value["state"] == old.value:
                    value["state"] = new.value
            else:
                update_string_unit_state(value, old, new)
    elif isinstance(data, list):
        for item in data:
            update_string_unit_state(item, old, new)
