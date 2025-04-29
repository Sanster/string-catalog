import json
from typing import List, Set, Optional
from pathlib import Path

from .models import StringCatalog, TranslationState
from .language import Language


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
    modified = False
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "stringUnit" and "state" in value:
                if value["state"] == old.value:
                    value["state"] = new.value
                    modified = True
            else:
                if update_string_unit_state(value, old, new):
                    modified = True
    elif isinstance(data, list):
        for item in data:
            if update_string_unit_state(item, old, new):
                modified = True
    return modified


def delete_languages_from_catalog(
    catalog: StringCatalog,
    keep_languages: Optional[Set[Language]] = None,
    exclude_languages: Optional[Set[Language]] = None,
) -> bool:
    """
    Delete languages from a string catalog based on keep or exclude lists.

    Args:
        catalog: The StringCatalog to modify
        keep_languages: Only keep these languages (and source language)
        exclude_languages: Delete these languages (preserves source language)

    Returns:
        bool: True if catalog was modified, False otherwise
    """
    source_lang = catalog.source_language.value
    modified = False

    for key, entry in catalog.strings.items():
        if not entry.localizations:
            continue

        languages_to_delete = set()

        # Determine which languages to delete
        for lang in entry.localizations:
            # Never delete source language
            if lang == source_lang:
                continue

            if keep_languages and Language(lang) not in keep_languages:
                languages_to_delete.add(lang)
            elif exclude_languages and Language(lang) in exclude_languages:
                languages_to_delete.add(lang)

        # Delete the languages
        for lang in languages_to_delete:
            if lang in entry.localizations:
                del entry.localizations[lang]
                modified = True

    return modified
