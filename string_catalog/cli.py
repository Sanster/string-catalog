import typer

from .appstoreconnect_cli import app as appstore_app
from .xcstrings_cli import app as xcstrings_app

app = typer.Typer(
    add_completion=False,
    help="A CLI tool for translating Apple String Catalogs",
)

# Add subcommand groups
app.add_typer(
    xcstrings_app,
    name="xcstrings",
    help="Commands for working with Apple String Catalogs (.xcstrings files)",
)

app.add_typer(
    appstore_app, name="appstore", help="Commands for App Store Connect automation"
)
