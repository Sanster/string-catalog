from enum import Enum
from typing import Dict, Optional, Set
from pydantic import BaseModel, Field

from string_catalog.language import Language


class TranslationState(str, Enum):
    NEW = "new"
    NEEDS_REVIEW = "needs_review"
    STALE = "stale"
    TRANSLATED = "translated"


class DeviceCategory(str, Enum):
    IPAD = "ipad"
    IPHONE = "iphone"
    IPOD = "ipod"
    MAC = "mac"
    OTHER = "other"
    TV = "appletv"
    VISION = "applevision"
    WATCH = "applewatch"


class PluralQualifier(str, Enum):
    ZERO = "zero"
    ONE = "one"
    TWO = "two"
    FEW = "few"
    MANY = "many"
    OTHER = "other"


class ExtractionState(str, Enum):
    EXTRACTED_WITH_VALUE = "extracted_with_value"
    MANUAL = "manual"
    MIGRATED = "migrated"
    UNKNOWN = "unknown"
    STALE = "stale"


class BaseModelWithAlias(BaseModel):
    model_config = {"populate_by_name": True}


class StringUnit(BaseModelWithAlias):
    state: TranslationState
    value: str

    @property
    def is_translated(self) -> bool:
        return self.state == TranslationState.TRANSLATED


class Variation(BaseModelWithAlias):
    string_unit: StringUnit = Field(alias="stringUnit")


class Variations(BaseModelWithAlias):
    device: Optional[Dict[DeviceCategory, Variation]] = None
    plural: Optional[Dict[PluralQualifier, Variation]] = None


class Substitution(BaseModelWithAlias):
    arg_num: int = Field(alias="argNum")
    format_specifier: str = Field(alias="formatSpecifier")
    variations: Optional[Variations] = None


class Localization(BaseModelWithAlias):
    string_unit: Optional[StringUnit] = Field(alias="stringUnit", default=None)
    substitutions: Optional[Dict[str, Substitution]] = None
    variations: Optional[Variations] = None


class CatalogEntry(BaseModelWithAlias):
    comment: Optional[str] = None
    extraction_state: Optional[ExtractionState] = Field(
        alias="extractionState", default=None
    )
    localizations: Optional[Dict[str, Localization]] = None
    should_translate: Optional[bool] = Field(alias="shouldTranslate", default=None)


class StringCatalog(BaseModelWithAlias):
    source_language: Language = Field(alias="sourceLanguage")
    strings: Dict[str, CatalogEntry]
    version: str = "1.0"

    def get_languages(self) -> Set[Language]:
        """
        Returns a set of all languages included in this catalog.

        Returns:
            set[Language]: A set containing the source language and all languages used in localizations.
        """
        languages = {self.source_language}

        for entry in self.strings.values():
            if entry.localizations:
                for lang in entry.localizations.keys():
                    # Language codes in localizations are stored as strings
                    try:
                        languages.add(Language(lang))
                    except ValueError:
                        # Skip invalid language codes
                        pass

        return languages


if __name__ == "__main__":
    string_unit = StringUnit(
        state=TranslationState.TRANSLATED, value="I really like tests!"
    )
    print(string_unit)
    localization = Localization(string_unit=string_unit)
    print(localization)
