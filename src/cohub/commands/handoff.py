"""cohub handoff - manually trigger handoff summary generation."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from ..core.adapter import load_adapter
from ..core.summarizer import summarize_or_prompt


@click.command()
@click.option("--cli", "cli_name", default="claude", show_default=True, help="Adapter used to find the transcript.")
def handoff(cli_name: str) -> None:
    """Generate handoff.md from the latest transcript, with manual fallback."""
    project_dir = Path.cwd()
    if not (project_dir / ".cohub").exists():
        click.echo("No .cohub/ directory found. Run cohub init first.")
        sys.exit(1)
    try:
        adapter = load_adapter(cli_name)
    except Exception as e:
        click.echo(f"Adapter load failed: {e}")
        sys.exit(1)
    summarize_or_prompt(project_dir, adapter)
