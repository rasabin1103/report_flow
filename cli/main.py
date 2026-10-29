import json
from pathlib import Path
from typing import Annotated

import typer

from app.core.settings import ReportError, Settings
from app.services.reports import presentation_config
from app.services.worker import run_job

app = typer.Typer(help="ASE ReportFlow: deterministic spreadsheet reports.")


def execute(
    action: str,
    source: Path,
    config: Path | None = None,
    options: dict | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    logo: Path | None = None,
    cover_style: str | None = None,
):
    settings = Settings()
    try:
        with source.open("rb") as stream:
            data = stream.read(settings.max_file_bytes + 1)
        if len(data) > settings.max_file_bytes:
            raise ReportError("File size limit exceeded", 413)
        raw = None
        if config:
            with config.open("r", encoding="utf-8") as stream:
                raw = stream.read(1000001)
        if raw is not None:
            logo_bytes = None
            if logo is not None:
                with logo.open("rb") as stream:
                    logo_bytes = stream.read(500001)
            raw = presentation_config(
                raw, title=title, subtitle=subtitle, logo=logo_bytes, cover_style=cover_style
            )
        return run_job(action, data, source.name, raw, options, settings)
    except (ReportError, OSError, UnicodeError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from None


@app.command()
def inspect(
    input: Annotated[Path, typer.Option("--input")],
    sheet_name: str | None = None,
    encoding: str = "utf-8-sig",
    delimiter: str | None = None,
):
    result = execute(
        "inspect", input, options={"sheet_name": sheet_name, "encoding": encoding, "delimiter": delimiter}
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command()
def validate(
    input: Annotated[Path, typer.Option("--input")],
    config: Annotated[Path, typer.Option("--config")],
    title: str | None = None,
    subtitle: str | None = None,
    logo: Path | None = None,
    cover_style: str | None = None,
):
    typer.echo(
        json.dumps(
            execute(
                "validate", input, config, title=title, subtitle=subtitle, logo=logo, cover_style=cover_style
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def generate(
    input: Annotated[Path, typer.Option("--input")],
    config: Annotated[Path, typer.Option("--config")],
    output: Annotated[Path, typer.Option("--output")],
    title: str | None = None,
    subtitle: str | None = None,
    logo: Path | None = None,
    cover_style: str | None = None,
):
    data = execute(
        "generate", input, config, title=title, subtitle=subtitle, logo=logo, cover_style=cover_style
    )
    try:
        output.write_bytes(data)
    except OSError:
        typer.echo("Error: cannot write output", err=True)
        raise typer.Exit(1) from None
    typer.echo(str(output))


if __name__ == "__main__":
    app()
