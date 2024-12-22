from pathlib import Path
from typing import List, Optional

import typer

from .translator import OpenAITranslator
from .coordinator import TranslationCoordinator
from .language import Language

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
    languages: List[Language] = typer.Option(
        None,
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
            target_langs = {Language(lang) for lang in languages}
    else:
        target_langs = None

    coordinator = TranslationCoordinator(
        translator=translator,
        target_languages=target_langs,
        overwrite=overwrite,
    )

    coordinator.translate_files(file_or_directory)
