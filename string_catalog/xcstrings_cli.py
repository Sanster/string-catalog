import json
from pathlib import Path
from typing import List
from rich import print

import typer

from .translator import OpenAITranslator
from .coordinator import TranslationCoordinator
from .language import Language
from .models import StringCatalog, TranslationState
from .utils import (
    find_catalog_files,
    save_catalog,
    update_string_unit_state,
    delete_languages_from_catalog,
)

AVAILABLE_LANGUAGES = "".join(
    f"| {lang.value}: {lang.name.replace('_', ' ').title()}" for lang in Language
)

app = typer.Typer(
    add_completion=False,
    help="A CLI tool for translating Apple String Catalogs",
)


@app.command()
def translate(
    file_or_directory: Path = typer.Argument(
        ..., help="File or directory containing string catalogs to translate"
    ),
    base_url: str = typer.Option(
        "https://openrouter.ai/api/v1",
        "--base-url",
        "-b",
        envvar=["BASE_URL"],
    ),
    api_key: str = typer.Option(..., "--api-key", "-k", envvar=["OPENROUTER_API_KEY"]),
    model: str = typer.Option(
        "anthropic/claude-3.5-haiku-20241022",
        "--model",
        "-m",
    ),
    languages: List[str] = typer.Option(
        ...,
        "--lang",
        "-l",
        help=f"Target language(s) or 'all' for all common languages. Available languages: {AVAILABLE_LANGUAGES}",
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing translations"
    ),
):
    translator = OpenAITranslator(base_url, api_key, model)

    # Convert string languages to Language enum
    if languages:
        if len(languages) == 1 and languages[0].lower() == "all":
            target_langs = set(Language.all_common())
        else:
            try:
                target_langs = {Language(lang) for lang in languages}
            except ValueError as e:
                print(f"Error: Invalid language code. {str(e)}")
                raise typer.Exit(1)
    else:
        target_langs = None

    coordinator = TranslationCoordinator(
        translator=translator,
        target_languages=target_langs,
        overwrite=overwrite,
    )

    coordinator.translate_files(file_or_directory)


@app.command(help="Update the state of stringUnit in xcstrings file")
def update_state(
    file_or_directory: Path = typer.Argument(
        ..., help="File or directory containing string catalogs to update state"
    ),
    old: TranslationState = typer.Option(
        TranslationState.NEEDS_REVIEW, help="Old state to update"
    ),
    new: TranslationState = typer.Option(TranslationState.TRANSLATED, help="New state"),
):
    files = find_catalog_files(file_or_directory)

    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            catalog_dict = json.load(f)

        # Track if any changes were made
        modified = update_string_unit_state(catalog_dict, old, new)

        if modified:
            catalog = StringCatalog.model_validate(catalog_dict)
            print(f"✅ Successfully updated state in {file}")
            save_catalog(catalog, file)


@app.command(
    help=f"Delete language from xcstrings file. Available languages: {AVAILABLE_LANGUAGES}"
)
def delete(
    file_or_directory: Path = typer.Argument(
        ..., help="File or directory containing string catalogs to delete language"
    ),
    keep_languages: List[str] = typer.Option(
        None,
        "--keep",
        "-k",
        help="Only keep these languages",
    ),
    exclude_languages: List[str] = typer.Option(
        None,
        "--exclude",
        "-e",
        help="Delete these languages",
    ),
):
    if keep_languages and exclude_languages:
        print("Error: Cannot specify both --keep and --exclude options together")
        raise typer.Exit(1)

    if not keep_languages and not exclude_languages:
        print("Error: Must specify either --keep or --exclude option")
        raise typer.Exit(1)

    # Convert string languages to Language enum
    target_langs = None
    if keep_languages:
        try:
            target_langs = {Language(lang) for lang in keep_languages}
            print(
                f"ℹ️ Keeping only these languages: {[lang.value for lang in target_langs]}"
            )
        except ValueError as e:
            print(f"Error: Invalid language code. {str(e)}")
            raise typer.Exit(1)

    exclude_langs = None
    if exclude_languages:
        try:
            exclude_langs = {Language(lang) for lang in exclude_languages}
            print(
                f"ℹ️ Excluding these languages: {[lang.value for lang in exclude_langs]}"
            )
        except ValueError as e:
            print(f"Error: Invalid language code. {str(e)}")
            raise typer.Exit(1)

    files = find_catalog_files(file_or_directory)
    if not files:
        print(f"⚠️ No .xcstrings files found in {file_or_directory}")
        return

    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            catalog_dict = json.load(f)

        catalog = StringCatalog.model_validate(catalog_dict)
        modified = delete_languages_from_catalog(catalog, target_langs, exclude_langs)

        if modified:
            print(f"✅ Successfully saved modified catalog to {file}")
            save_catalog(catalog, file)
