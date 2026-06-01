"""cohub snap "<message>" - git add, commit, tag, and update snapshots.md."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from ..core import git_wrap as gw
from ..core import project as proj


@click.command()
@click.argument("message", type=str)
def snap(message: str) -> None:
    """Create a snapshot with git add, commit, and snap-NNN tag."""
    project_dir = Path.cwd()
    if not (project_dir / ".cohub").exists():
        click.echo("No .cohub/ directory found. Run cohub init first.")
        sys.exit(1)
    if not gw.is_git_repo(project_dir):
        click.echo("Current directory is not a Git repository; cannot create snapshot.")
        sys.exit(1)

    try:
        gw.run_git(project_dir, ["add", "-A"])
        # Attempt commit even when there may be no changes.
        commit_rc, commit_out = gw.run_git(project_dir, ["commit", "-m", message], check=False)
        if commit_rc != 0 and "nothing to commit" not in commit_out and "no changes" not in commit_out:
            click.echo(f"git commit failed: {commit_out}")
            sys.exit(1)

        tag = gw.next_snap_tag(project_dir)
        gw.run_git(project_dir, ["tag", tag])
    except gw.GitError as e:
        click.echo(f"Git operation failed: {e}")
        sys.exit(1)

    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    proj.append_snapshot(project_dir, ts, message, tag)
    click.echo(f"Snapshot saved: {tag}  {message}")
