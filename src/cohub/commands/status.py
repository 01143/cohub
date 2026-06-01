"""cohub status - display active.md."""
from __future__ import annotations

from pathlib import Path

import click

from ..core import project as proj


@click.command()
def status() -> None:
    """Show active sessions for the current project."""
    project_dir = Path.cwd()
    cohub_dir = project_dir / ".cohub"
    if not cohub_dir.exists():
        click.echo("No .cohub/ directory found. Run cohub init first.")
        return

    entries = proj.read_active_entries(project_dir)
    if not entries:
        click.echo("No active sessions.")
        return

    click.echo("Active sessions:")
    for e in entries:
        marker = " (stale)" if e.is_stale() else ""
        click.echo(f"  [{e.session_id}] {e.cli} PID={e.pid} started={e.started} doing={e.doing} heartbeat={e.heartbeat}{marker}")
