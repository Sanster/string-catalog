"""
Module for handling What's New content generation from xcstrings files.

This module provides functionality to extract specific keys from Apple String Catalogs
and generate JSON files suitable for App Store Connect What's New updates.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from .models import StringCatalog


def extract_string_value(localization, key: str) -> str:
    """Extract string value from localization, handling variations and substitutions.

    Args:
        localization: The localization object from a string catalog entry
        key: The string key (used as fallback for debugging)

    Returns:
        The extracted string value, or empty string if no value found
    """
    if not localization:
        return ""

    # Check for simple string unit first
    if localization.string_unit:
        return localization.string_unit.value

    # Handle variations (plural forms, device variations)
    if localization.variations:
        values = []

        # Handle plural variations
        if localization.variations.plural:
            for qualifier, variation in localization.variations.plural.items():
                if variation.string_unit:
                    values.append(variation.string_unit.value)

        # Handle device variations
        if localization.variations.device:
            for device, variation in localization.variations.device.items():
                if variation.string_unit:
                    values.append(variation.string_unit.value)

        return " / ".join(values) if values else ""

    return ""


def extract_keys_from_catalog(
    catalog: StringCatalog, keys: List[str]
) -> Dict[str, str]:
    """Extract specified keys from catalog for all languages.

    Args:
        catalog: The string catalog to extract from
        keys: List of string keys to extract

    Returns:
        Dictionary mapping language codes to extracted content
    """
    result = {}

    # Get all available languages from the catalog
    all_languages = catalog.get_languages()

    for lang in all_languages:
        lang_code = lang.value
        extracted_values = []

        for key in keys:
            if key in catalog.strings:
                entry = catalog.strings[key]

                # Skip if should not translate
                if entry.should_translate is False:
                    continue

                # Get localization for this language
                localization = None
                if entry.localizations and lang_code in entry.localizations:
                    localization = entry.localizations[lang_code]
                elif lang_code == catalog.source_language.value:
                    # For source language, use the key itself if no localization exists
                    if (
                        entry.localizations
                        and catalog.source_language.value in entry.localizations
                    ):
                        localization = entry.localizations[
                            catalog.source_language.value
                        ]
                    else:
                        # Use key as fallback for source language
                        extracted_values.append(key)
                        continue

                value = extract_string_value(localization, key)
                if value:
                    extracted_values.append(value)

        if extracted_values:
            result[lang_code] = "\n\n".join(extracted_values)

    return result


def generate_whats_new_json(
    xcstrings_file: Path, keys: List[str], output_file: Path
) -> Dict[str, str]:
    """Generate What's New JSON file from xcstrings keys.

    Args:
        xcstrings_file: Path to the xcstrings file
        keys: List of keys to extract from the xcstrings file
        output_file: Path where the JSON file should be saved

    Returns:
        Dictionary containing the extracted What's New data

    Raises:
        FileNotFoundError: If xcstrings file doesn't exist
        ValueError: If no keys provided or no data extracted
        Exception: For other processing errors
    """
    if not xcstrings_file.exists():
        raise FileNotFoundError(f"xcstrings file not found: {xcstrings_file}")

    if not keys:
        raise ValueError("At least one key must be specified")

    # Load and parse the xcstrings file
    with open(xcstrings_file, "r", encoding="utf-8") as f:
        catalog_dict = json.load(f)

    catalog = StringCatalog.model_validate(catalog_dict)

    # Extract keys for all languages
    whats_new_data = extract_keys_from_catalog(catalog, keys)

    if not whats_new_data:
        raise ValueError("No data extracted from the specified keys")

    # Save to output file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(whats_new_data, f, ensure_ascii=False, indent=2)

    return whats_new_data


def load_whats_new_json(json_file: Path) -> Dict[str, str]:
    """Load What's New data from a JSON file.

    Args:
        json_file: Path to the JSON file

    Returns:
        Dictionary mapping language codes to What's New content

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        ValueError: If JSON format is invalid
    """
    if not json_file.exists():
        raise FileNotFoundError(f"JSON file not found: {json_file}")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            "JSON file must contain an object mapping language codes to content"
        )

    # Ensure all values are strings
    return {str(k): str(v) if v is not None else "" for k, v in data.items()}


def find_best_matching_locale(
    target_locale: str, available_locales: Dict[str, any]
) -> Optional[str]:
    """
    Find the best matching locale from available locales.
    First tries exact match, then falls back to base language code match.

    Args:
        target_locale: The locale to find (e.g., "es")
        available_locales: Dictionary of available locales (can be complex dict or simple dict)

    Returns:
        The best matching locale key, or None if no match found
    """
    # First try exact match
    if target_locale in available_locales:
        return target_locale

    # If no exact match, try to find locales that start with the base language code
    base_lang = target_locale.split("-")[
        0
    ]  # Extract base language (e.g., "es" from "es-MX")

    matching_locales = [
        locale
        for locale in available_locales.keys()
        if locale.startswith(base_lang + "-") or locale == base_lang
    ]

    if matching_locales:
        # Prefer exact base language match over regional variants
        if base_lang in matching_locales:
            return base_lang
        # Otherwise return the first regional variant
        return matching_locales[0]

    return None
