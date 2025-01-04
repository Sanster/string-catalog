import json
from pathlib import Path
from typing import List
from rich import print

import typer

from .translator import OpenAITranslator
from .coordinator import TranslationCoordinator
from .language import Language
from .models import StringCatalog, TranslationState
from .utils import find_catalog_files, save_catalog, update_string_unit_state


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
        help="Target language(s) or 'all' for all common languages",
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
                print(f"[red]Error: Invalid language code. {str(e)}[/red]")
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

        update_string_unit_state(catalog_dict, old, new)

        catalog = StringCatalog.model_validate(catalog_dict)
        print(f"Save {file}")
        save_catalog(catalog, file)
