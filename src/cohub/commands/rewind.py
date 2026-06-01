"""cohub rewind - interactively inspect or restore snapshots."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from ..core import git_wrap as gw
from ..core import project as proj


@click.command()
def rewind() -> None:
    """List snapshots interactively; use read-only worktree by default."""
    project_dir = Path.cwd()
    if not (project_dir / ".cohub").exists():
        click.echo("No .cohub/ directory found. Run cohub init first.")
        sys.exit(1)

    snaps = proj.read_snapshots(project_dir)
    if not snaps:
        click.echo("No snapshots yet. Create one with cohub snap first.")
        return

    click.echo("Available snapshots:")
    for i, s in enumerate(snaps, 1):
        click.echo(f"  [{i}] {s.tag}  {s.timestamp}  {s.message}")

    idx_raw = click.prompt("Select a number (press Enter to cancel)", default="", show_default=False)
    if not idx_raw.strip():
        return
    try:
        idx = int(idx_raw) - 1
        chosen = snaps[idx]
    except (ValueError, IndexError):
        click.echo("Invalid selection; cancelled.")
        return

    mode = click.prompt("Mode: w=worktree (read-only), r=hard reset (dangerous)", default="w")
    if mode == "w":
        target = project_dir / "_history" / chosen.tag
        target.parent.mkdir(exist_ok=True)
        try:
            gw.run_git(project_dir, ["worktree", "add", str(target), chosen.tag])
        except gw.GitError as e:
            click.echo(f"Failed to create worktree: {e}")
            sys.exit(1)
        click.echo(f"Checked out worktree: {target}")
    elif mode == "r":
        if not click.confirm(f"Hard reset the current branch to {chosen.tag}? Working tree changes will be lost. Continue?", default=False):
            click.echo("Cancelled.")
            return
        try:
            gw.run_git(project_dir, ["reset", "--hard", chosen.tag])
        except gw.GitError as e:
            click.echo(f"Reset failed: {e}")
            sys.exit(1)
        click.echo(f"Hard reset to {chosen.tag}")
    else:
        click.echo("Unknown mode; cancelled.")
