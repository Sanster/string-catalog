import json
from pathlib import Path

import pytest

from string_catalog.models import TranslationState
from string_catalog.utils import update_string_unit_state


@pytest.fixture
def update_state_catalog():
    catalog_path = Path(__file__).parent / "example" / "UpdateStateCatalog.xcstrings"
    with open(catalog_path) as f:
        return json.load(f)


def test_update_string_unit_state(update_state_catalog):
    # Update states from needs_review to translated
    update_string_unit_state(
        update_state_catalog,
        old=TranslationState.NEEDS_REVIEW,
        new=TranslationState.TRANSLATED,
    )

    # Test basic string unit
    assert (
        update_state_catalog["strings"]["basicKey"]["localizations"]["en"][
            "stringUnit"
        ]["state"]
        == "translated"
    )

    # Test plural variation
    assert (
        update_state_catalog["strings"]["pluralKey"]["localizations"]["en"][
            "variations"
        ]["plural"]["one"]["stringUnit"]["state"]
        == "translated"
    )

    # Test substitutions
    substitutions = update_state_catalog["strings"]["substitutionKey"]["localizations"][
        "en"
    ]["substitutions"]

    # Check arg1 substitution
    assert (
        substitutions["arg1"]["variations"]["plural"]["one"]["stringUnit"]["state"]
        == "translated"
    )
    # This one was already translated, should remain translated
    assert (
        substitutions["arg1"]["variations"]["plural"]["other"]["stringUnit"]["state"]
        == "translated"
    )

    # Check arg2 substitution
    assert (
        substitutions["arg2"]["variations"]["plural"]["one"]["stringUnit"]["state"]
        == "translated"
    )
    # This one was already translated, should remain translated
    assert (
        substitutions["arg2"]["variations"]["plural"]["other"]["stringUnit"]["state"]
        == "translated"
    )

    # Test that strings in other languages are also updated
    assert (
        update_state_catalog["strings"][
            "Key is source language content and contain other language"
        ]["localizations"]["it"]["stringUnit"]["state"]
        == "translated"
    )
