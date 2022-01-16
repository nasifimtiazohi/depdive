#!/usr/bin/env python
"""Command-line interface."""
import click
from rich import traceback


@click.command()
@click.version_option(version="0.0.15", message=click.style("depdive Version: 0.0.15"))
def main() -> None:
    """depdive."""


if __name__ == "__main__":
    traceback.install()
    main(prog_name="depdive")  # pragma: no cover
