"""Console script for translatorutils."""

import typer
from rich.console import Console

from translatorutils import utils

app = typer.Typer()
console = Console()


@app.command()
def main():
    """Console script for translatorutils."""
    console.print("Replace this message by putting your code into "
               "translatorutils.cli.main")
    console.print("See Typer documentation at https://typer.tiangolo.com/")
    utils.do_something_useful()


if __name__ == "__main__":
    app()
