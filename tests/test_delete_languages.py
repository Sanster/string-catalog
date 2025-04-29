import json
from pathlib import Path

import pytest

from string_catalog.models import StringCatalog
from string_catalog.language import Language
from string_catalog.utils import delete_languages_from_catalog


@pytest.fixture
def test_catalog():
    """Create a test catalog with multiple languages"""
    catalog_path = Path(__file__).parent / "example" / "BasicCatalog.xcstrings"
    with open(catalog_path) as f:
        catalog_data = json.load(f)

    # Ensure we have multiple languages for testing
    catalog_data["strings"]["basicKey"]["localizations"]["zh-Hans"] = {
        "stringUnit": {"state": "translated", "value": "我真的很喜欢测试！"}
    }
    catalog_data["strings"]["basicKey"]["localizations"]["es"] = {
        "stringUnit": {
            "state": "translated",
            "value": "¡Realmente me gustan las pruebas!",
        }
    }
    catalog_data["strings"]["basicKey"]["localizations"]["fr"] = {
        "stringUnit": {"state": "translated", "value": "J'aime vraiment les tests!"}
    }

    return StringCatalog.model_validate(catalog_data)


def test_keep_languages(test_catalog):
    """Test keeping only specific languages"""
    # Keep only English (source) and Chinese
    keep_languages = {Language.CHINESE_SIMPLIFIED}
    modified = delete_languages_from_catalog(
        test_catalog, keep_languages=keep_languages
    )

    # Check if it was modified
    assert modified is True

    # Check source language is still there
    assert "en" in test_catalog.strings["basicKey"].localizations

    # Check kept language is still there
    assert "zh-Hans" in test_catalog.strings["basicKey"].localizations

    # Check deleted languages
    assert "es" not in test_catalog.strings["basicKey"].localizations
    assert "fr" not in test_catalog.strings["basicKey"].localizations


def test_exclude_languages(test_catalog):
    """Test excluding specific languages"""
    # Exclude Spanish and French
    exclude_languages = {Language.SPANISH, Language.FRENCH}
    modified = delete_languages_from_catalog(
        test_catalog, exclude_languages=exclude_languages
    )

    # Check if it was modified
    assert modified is True

    # Check source language is still there
    assert "en" in test_catalog.strings["basicKey"].localizations

    # Check kept language is still there
    assert "zh-Hans" in test_catalog.strings["basicKey"].localizations

    # Check deleted languages
    assert "es" not in test_catalog.strings["basicKey"].localizations
    assert "fr" not in test_catalog.strings["basicKey"].localizations


def test_keep_source_language(test_catalog):
    """Test that source language is always preserved"""
    # Try to exclude all languages including source
    exclude_languages = {
        Language.ENGLISH,
        Language.CHINESE_SIMPLIFIED,
        Language.SPANISH,
        Language.FRENCH,
    }
    modified = delete_languages_from_catalog(
        test_catalog, exclude_languages=exclude_languages
    )

    # Check if it was modified
    assert modified is True

    # Check source language is still there (should not be deleted)
    assert "en" in test_catalog.strings["basicKey"].localizations

    # Check other languages are deleted
    assert "zh-Hans" not in test_catalog.strings["basicKey"].localizations
    assert "es" not in test_catalog.strings["basicKey"].localizations
    assert "fr" not in test_catalog.strings["basicKey"].localizations


def test_no_changes(test_catalog):
    """Test when no languages are deleted"""
    # Keep all existing languages
    keep_languages = set()

    # 将测试目录中的所有语言添加到 keep_languages 集合中
    for key, entry in test_catalog.strings.items():
        if entry.localizations:
            for lang in entry.localizations:
                # 将字符串语言代码转换为 Language 枚举
                keep_languages.add(Language(lang))

    print(f"Total languages before deletion: {test_catalog.get_languages()}")
    modified = delete_languages_from_catalog(
        test_catalog, keep_languages=keep_languages
    )
    print(f"Total languages after deletion: {test_catalog.get_languages()}")

    # Check that no modifications were made
    assert modified is False

    # Check all languages are still there
    assert "en" in test_catalog.strings["basicKey"].localizations
    assert "zh-Hans" in test_catalog.strings["basicKey"].localizations
    assert "es" in test_catalog.strings["basicKey"].localizations
    assert "fr" in test_catalog.strings["basicKey"].localizations


def test_mixed_entries(test_catalog):
    """Test catalog with entries having different language sets"""
    # Add a new entry with different language set
    test_catalog.strings["newKey"] = test_catalog.strings["basicKey"].model_copy(
        deep=True
    )
    # Remove Spanish from the new entry
    del test_catalog.strings["newKey"].localizations["es"]

    # Keep only Chinese
    keep_languages = {Language.CHINESE_SIMPLIFIED}
    modified = delete_languages_from_catalog(
        test_catalog, keep_languages=keep_languages
    )

    # Check if it was modified
    assert modified is True

    # Check results for first entry
    assert "en" in test_catalog.strings["basicKey"].localizations
    assert "zh-Hans" in test_catalog.strings["basicKey"].localizations
    assert "es" not in test_catalog.strings["basicKey"].localizations
    assert "fr" not in test_catalog.strings["basicKey"].localizations

    # Check results for second entry
    assert "en" in test_catalog.strings["newKey"].localizations
    assert "zh-Hans" in test_catalog.strings["newKey"].localizations
    assert "fr" not in test_catalog.strings["newKey"].localizations
