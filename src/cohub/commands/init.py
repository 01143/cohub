"""cohub init - create a .cohub project state directory."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import yaml

from ..core.project import default_meta, ensure_cohub_dir, write_meta
from ..core.git_wrap import is_git_repo, git_init


@click.command()
def init() -> None:
    """Create .cohub in the current directory and generate meta.yaml interactively."""
    project_dir = Path.cwd()
    cohub_dir = project_dir / ".cohub"

    if cohub_dir.exists():
        click.echo(f"{cohub_dir} already exists; cancelled.")
        sys.exit(1)

    project_name = click.prompt("Project name", default=project_dir.name)
    goal = click.prompt("Project goal (one sentence)", default="(to be filled)")
    tags_raw = click.prompt("Tags (comma-separated; used for skill matching)", default="")
    languages_raw = click.prompt("Languages (comma-separated)", default="")

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    languages = [l.strip() for l in languages_raw.split(",") if l.strip()]

    ensure_cohub_dir(project_dir)
    meta = default_meta(project_name=project_name, goal=goal, tags=tags, language=languages)
    write_meta(project_dir, meta)

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    (cohub_dir / "handoff.md").write_text(
        f"# Session Handoff Summary (none, {now})\n\n## Current Task\nNone\n\n## Completed\nNone\n\n## Blockers\nNone\n\n## Decisions\nNone\n\n## Suggested Next Steps\nNone\n",
        encoding="utf-8",
    )
    (cohub_dir / "state.md").write_text(
        f"# Project State (updated at {now})\n\n## Goal\n{goal}\n\n## Current Progress\n- (to be filled)\n\n## Key Conventions\n- (to be filled)\n\n## Recent Changes\nNone\n",
        encoding="utf-8",
    )
    (cohub_dir / "active.md").write_text(f"# Active Sessions ({now})\n\n", encoding="utf-8")
    (cohub_dir / "snapshots.md").write_text("", encoding="utf-8")
    (cohub_dir / "reviews").mkdir(exist_ok=True)

    click.echo(f"Created {cohub_dir}")

    if not is_git_repo(project_dir):
        if click.confirm("This directory is not a Git repository. Run git init?", default=True):
            git_init(project_dir)
            click.echo("git init complete")

    click.echo("Next: cohub start claude")
