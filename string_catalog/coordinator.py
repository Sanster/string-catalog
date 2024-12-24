import copy
import json
from pathlib import Path
from typing import Dict, Optional, Set, Union, List

from rich.progress import Progress, MofNCompleteColumn
from rich.console import Console
from rich import print

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
        target_languages: Set[Language],
        overwrite: bool = False,
    ):
        self.translator = translator
        self.target_languages = target_languages
        self.overwrite = overwrite
        self.console = Console()

    def translate_files(self, path: Path):
        """Translate all string catalog files in the given path"""
        files = self._find_catalog_files(path)

        if not files:
            print(f"No .xcstrings files found in {path}")
            return

        print(f"Target languages: {[lang.value for lang in self.target_languages]}")

        with Progress(
            *Progress.get_default_columns(), MofNCompleteColumn(), console=self.console
        ) as progress:
            file_task = progress.add_task(
                f"Translating {len(files)} files", total=len(files)
            )
            lang_task = progress.add_task(
                f"Translating {len(self.target_languages)} languages...",
                total=len(self.target_languages),
            )
            entry_task = progress.add_task("Processing entries")
            for file_path in files:
                try:
                    catalog = self._load_catalog(file_path)
                    progress.log(f"Processing {file_path}")

                    progress.update(lang_task, completed=0)

                    self._translate_catalog_entries(
                        catalog, self.target_languages, lang_task, entry_task, progress
                    )

                    self._save_catalog(catalog, file_path)
                    progress.update(file_task, advance=1)
                except Exception:
                    self.console.print_exception(show_locals=True)

    def _find_catalog_files(self, path: Path) -> List[Path]:
        """Find all .xcstrings files in the given path"""
        if path.is_file() and path.suffix == ".xcstrings":
            return [path]

        return [p for p in path.rglob("*.xcstrings") if "translated" not in p.name]

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

        self.console.log(f"Saving to {output_path}")

        with open(output_path, "w") as f:
            json.dump(
                catalog.model_dump(by_alias=True, exclude_none=True),
                f,
                ensure_ascii=False,
                separators=(",", " : "),
                indent=2,
            )

    def _translate_catalog_entries(
        self,
        catalog: StringCatalog,
        target_languages: Set[Language],
        lang_task: int,
        entry_task: int,
        progress: Progress,
    ):
        # Move target languages loop to outermost level
        for target_lang in target_languages:
            if target_lang == Language(catalog.source_language):
                continue

            progress.update(
                entry_task,
                completed=0,
                description=f"Processing {len(catalog.strings.items())} entries",
                total=len(catalog.strings),
            )

            # Process all entries for current target language
            for key, entry in catalog.strings.items():
                if entry.should_translate is False:
                    continue

                if not entry.localizations:
                    entry.localizations = {}

                should_delete_source_lang_localization = False
                if catalog.source_language not in entry.localizations:
                    should_delete_source_lang_localization = True
                    # create dummy localization for source language, will delete when finish
                    entry.localizations[catalog.source_language.value] = Localization(
                        string_unit=StringUnit(
                            state=TranslationState.TRANSLATED, value=key
                        )
                    )

                source_localization = entry.localizations[catalog.source_language]
                source_string_unit = source_localization.string_unit
                source_variations = source_localization.variations
                source_substitutions = source_localization.substitutions

                # Initialize target localization if needed
                if target_lang.value not in entry.localizations:
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
                            state=TranslationState.NEEDS_REVIEW, value=translated_text
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

                progress.update(entry_task, advance=1)

                if should_delete_source_lang_localization:
                    del entry.localizations[catalog.source_language]

            progress.update(lang_task, advance=1)

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
                variation.string_unit.state = TranslationState.NEEDS_REVIEW

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
