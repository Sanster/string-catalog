import copy
import json
from pathlib import Path
from typing import Dict, Optional, Set, Union

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
from .utils import find_catalog_files, save_catalog


class TranslationCoordinator:
    def __init__(
        self,
        translator: OpenAITranslator,
        target_languages: Set[Language],
        overwrite: bool = False,
        ref_language: Optional[Language] = None,
    ):
        self.translator = translator
        self.target_languages = target_languages
        self.overwrite = overwrite
        self.ref_language = ref_language
        self.console = Console()

    def translate_files(self, path: Path):
        """Translate all string catalog files in the given path"""
        files = find_catalog_files(path)

        if not files:
            print(f"No .xcstrings files found in {path}")
            return

        print(f"Target languages: {[lang.value for lang in self.target_languages]}")
        if self.ref_language:
            print(f"Reference language: {self.ref_language.value}")

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

    def _load_catalog(self, path: Path) -> StringCatalog:
        """Load string catalog from file"""
        return StringCatalog.model_validate_json(path.read_text())

    def _save_catalog(self, catalog: StringCatalog, path: Path):
        """Save string catalog to file"""
        output_path = (
            path if self.overwrite else path.with_suffix(".translated.xcstrings")
        )

        self.console.log(f"Saving to {output_path}")

        save_catalog(catalog, output_path)

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

                # Prepare optional reference language context
                ref_localization = None
                if self.ref_language:
                    ref_localization = entry.localizations.get(self.ref_language.value)

                base_comment = entry.comment
                if (
                    ref_localization
                    and ref_localization.string_unit
                    and ref_localization.string_unit.value
                ):
                    ref_text = ref_localization.string_unit.value
                    ref_line = (
                        f"Reference translation [{self.ref_language.value}]: {ref_text}"
                    )
                    guidance = (
                        "Use the reference translation line(s) below only to clarify meaning. "
                        "Do not copy it directly; if it conflicts with the source text, follow the source text."
                    )
                    base_comment = (
                        f"{base_comment}\n\n{guidance}\n{ref_line}"
                        if base_comment
                        else f"{guidance}\n{ref_line}"
                    )

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
                            source_string_unit.value,
                            target_lang.value,
                            base_comment,
                        )
                        target_localization.string_unit = StringUnit(
                            state=TranslationState.NEEDS_REVIEW, value=translated_text
                        )

                # Translate variations if they exist
                if source_variations:
                    self._translate_variations(
                        target_localization,
                        source_variations,
                        ref_localization.variations if ref_localization else None,
                        target_lang,
                        base_comment,
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
                            (
                                ref_localization.substitutions.get(k).variations
                                if (
                                    ref_localization
                                    and ref_localization.substitutions
                                    and k in ref_localization.substitutions
                                    and ref_localization.substitutions.get(k)
                                )
                                else None
                            ),
                            target_lang,
                            base_comment,
                        )

                progress.update(entry_task, advance=1)

                if should_delete_source_lang_localization:
                    del entry.localizations[catalog.source_language]

            progress.update(lang_task, advance=1)

    def _translate_variations(
        self,
        variations_parent: Union[Localization, Substitution],
        source_variations: Variations,
        ref_variations: Optional[Variations],
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
                    (ref_variations.plural if ref_variations else None),
                    lang,
                    comment,
                    variation_kind="plural",
                )
            )

        if source_variations.device:
            variations_parent.variations.device = (
                self._translate_variations_plural_device(
                    variations_parent.variations.device,
                    source_variations.device,
                    (ref_variations.device if ref_variations else None),
                    lang,
                    comment,
                    variation_kind="device",
                )
            )

    def _translate_variations_plural_device(
        self,
        variations_dict: Optional[
            Dict[Union[PluralQualifier, DeviceCategory], Variation]
        ],
        source_variations_dict: Dict[Union[PluralQualifier, DeviceCategory], Variation],
        ref_variations_dict: Optional[
            Dict[Union[PluralQualifier, DeviceCategory], Variation]
        ],
        lang: Language,
        comment: Optional[str] = None,
        variation_kind: str = "",
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

            # Prepare per-variation reference comment if available
            per_variation_comment = comment
            if ref_variations_dict and key in ref_variations_dict:
                ref_text = ref_variations_dict[key].string_unit.value
                ref_line = (
                    (
                        f"Reference translation [{self.ref_language.value}, {variation_kind}={key.value}]: {ref_text}"
                    )
                    if self.ref_language
                    else f"Reference translation [{variation_kind}={key.value}]: {ref_text}"
                )
                if comment:
                    per_variation_comment = f"{comment}\n{ref_line}"
                else:
                    guidance = (
                        "Use the reference translation line(s) below only to clarify meaning. "
                        "Do not copy it directly; if it conflicts with the source text, follow the source text."
                    )
                    per_variation_comment = f"{guidance}\n{ref_line}"

            variation.string_unit.value = self.translator.translate(
                source_variations_dict[key].string_unit.value,
                lang.value,
                per_variation_comment,
            )
            variations_dict[key] = variation
        return variations_dict
