"""cohub review - MVP placeholder for a future review workflow."""
from __future__ import annotations

import click


@click.command()
@click.option("--with", "cli_name", default="codex", help="CLI used for review.")
def review(cli_name: str) -> None:
    """[P1] Start a selected CLI for read-only review. Not implemented in MVP."""
    click.echo("The review command is not implemented in the MVP and is reserved for P1.")
    click.echo("Recommended workflow: run cohub snap, then manually start Codex and paste git diff.")
