import copy
import json
from pathlib import Path
from typing import Dict, Optional, Set, Union

from loguru import logger
from rich.progress import Progress, MofNCompleteColumn

from .models import (
    DeviceCategory,
    PluralQualifier,
    StringCatalog,
    Localization,
    StringUnit,
    Substitution,
    TranslationState,
    Variation,
    Variations,
)
from .translator import OpenAITranslator
from .language import Language


class TranslationCoordinator:
    def __init__(
        self,
        translator: OpenAITranslator,
        target_languages: Optional[Set[Language]] = None,
        overwrite: bool = False,
    ):
        self.translator = translator
        self.target_languages = target_languages
        self.overwrite = overwrite

    def translate_files(self, path: Path):
        """Translate all string catalog files in the given path"""
        files = self._find_catalog_files(path)

        if not files:
            logger.error(f"No .xcstrings files found in {path}")
            return

        for file_path in files:
            logger.info(f"Processing {file_path}")

            try:
                catalog = self._load_catalog(file_path)
                target_languages = (
                    self.target_languages or self._get_existing_languages(catalog)
                )
                logger.info(
                    f"Target languages: {[lang.value for lang in target_languages]}"
                )

                with Progress(
                    *Progress.get_default_columns(), MofNCompleteColumn()
                ) as progress:
                    task = progress.add_task(
                        f"Translating {file_path}", total=len(target_languages)
                    )
                    self._translate_catalog_entries(
                        catalog, target_languages, task, progress
                    )

                self._save_catalog(catalog, file_path)
            except Exception as e:
                logger.exception(e)

    def _find_catalog_files(self, path: Path) -> list[Path]:
        """Find all .xcstrings files in the given path"""
        if path.is_file() and path.suffix == ".xcstrings":
            return [path]

        return list(path.rglob("*.xcstrings"))

    def _load_catalog(self, path: Path) -> StringCatalog:
        """Load string catalog from file"""
        with open(path) as f:
            data = json.load(f)

        return StringCatalog.model_validate(data)

    def _save_catalog(self, catalog: StringCatalog, path: Path):
        """Save string catalog to file"""
        output_path = (
            path if self.overwrite else path.with_suffix(".translated.xcstrings")
        )

        logger.info(f"Saving to {output_path}")

        with open(output_path, "w") as f:
            json.dump(
                catalog.model_dump(by_alias=True, exclude_none=True),
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _translate_catalog_entries(
        self,
        catalog: StringCatalog,
        target_languages: Set[Language],
        task: int,
        progress: Progress,
    ):
        # Move target languages loop to outermost level
        for target_lang in target_languages:
            if target_lang == Language(catalog.source_language):
                continue

            progress.update(task, description=f"Translating to {target_lang}")

            # Process all entries for current target language
            for key, entry in catalog.strings.items():
                if (
                    not entry.localizations
                    or catalog.source_language not in entry.localizations
                ):
                    continue

                source_localization = entry.localizations[catalog.source_language]
                source_string_unit = source_localization.string_unit
                source_variations = source_localization.variations
                source_substitutions = source_localization.substitutions

                # Initialize target localization if needed
                if str(target_lang) not in entry.localizations:
                    entry.localizations[target_lang.value] = Localization()

                target_localization = entry.localizations[target_lang.value]

                # Translate main string unit if needed
                if source_string_unit:
                    if (
                        target_localization.string_unit
                        and not target_localization.string_unit.is_translated
                    ) or target_localization.string_unit is None:
                        translated_text = self.translator.translate(
                            source_string_unit.value, target_lang.value, entry.comment
                        )
                        target_localization.string_unit = StringUnit(
                            state=TranslationState.TRANSLATED, value=translated_text
                        )

                # Translate variations if they exist
                if source_variations:
                    self._translate_variations(
                        target_localization,
                        source_variations,
                        target_lang,
                        entry.comment,
                    )

                if source_substitutions:
                    if not target_localization.substitutions:
                        target_localization.substitutions = {}
                    for k, source_substitution in source_substitutions.items():
                        if k not in target_localization.substitutions:
                            target_localization.substitutions[k] = Substitution(
                                arg_num=source_substitution.arg_num,
                                format_specifier=source_substitution.format_specifier,
                            )

                        self._translate_variations(
                            target_localization.substitutions[k],
                            source_substitution.variations,
                            target_lang,
                            entry.comment,
                        )

            progress.update(task, advance=1)

    def _translate_variations(
        self,
        variations_parent: Union[Localization, Substitution],
        source_variations: Variations,
        lang: Language,
        comment: Optional[str] = None,
    ):
        if not variations_parent.variations:
            variations_parent.variations = Variations()

        if source_variations.plural:
            variations_parent.variations.plural = (
                self._translate_variations_plural_device(
                    variations_parent.variations.plural,
                    source_variations.plural,
                    lang,
                    comment,
                )
            )

        if source_variations.device:
            variations_parent.variations.device = (
                self._translate_variations_plural_device(
                    variations_parent.variations.device,
                    source_variations.device,
                    lang,
                    comment,
                )
            )

    def _translate_variations_plural_device(
        self,
        variations_dict: Optional[
            Dict[Union[PluralQualifier, DeviceCategory], Variation]
        ],
        source_variations_dict: Dict[Union[PluralQualifier, DeviceCategory], Variation],
        lang: Language,
        comment: Optional[str] = None,
    ):
        if variations_dict is None:
            variations_dict = copy.deepcopy(source_variations_dict)
            for key, variation in variations_dict.items():
                variation.string_unit.state = TranslationState.NEW

        for key, variation in variations_dict.items():
            if variation.string_unit.is_translated:
                continue
            if key not in source_variations_dict:
                continue

            variation.string_unit.value = self.translator.translate(
                source_variations_dict[key].string_unit.value, lang.value, comment
            )
            variations_dict[key] = variation
        return variations_dict

    def _get_existing_languages(self, catalog: StringCatalog) -> Set[Language]:
        """Get set of languages already present in catalog"""
        languages = {Language(catalog.source_language)}
        for entry in catalog.strings.values():
            if entry.localizations:
                languages.update(Language(lang) for lang in entry.localizations.keys())
        return languages
