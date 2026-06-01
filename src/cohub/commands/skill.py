"""cohub skill <subcommand> - skill library management."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import click

from ..core import paths
from ..core import skills as sk_mod
from ..core import project as proj


@click.group()
def skill() -> None:
    """Manage the personal skill library under ~/.cohub/skills/."""


@skill.command("list")
@click.option("--tag", "tag", default=None, help="Filter by tag.")
def skill_list(tag: str | None) -> None:
    skills = sk_mod.load_all_skills()
    if tag:
        skills = [s for s in skills if tag in s.tags]
    if not skills:
        click.echo("(no skills)")
        return
    for s in skills:
        click.echo(f"- {s.name}  tags={s.tags}  when={s.when}")


@skill.command("save")
@click.argument("name", type=str)
@click.option("--tags", "tags", default="", help="Comma-separated tags.")
@click.option("--when", "when", default="", help="When to use this skill.")
def skill_save(name: str, tags: str, when: str) -> None:
    """Read skill content from stdin and save it."""
    paths.skills_dir().mkdir(parents=True, exist_ok=True)
    path = paths.skills_dir() / f"{name}.md"
    if path.exists():
        if not click.confirm(f"{path} already exists. Overwrite?", default=False):
            return

    click.echo("Paste skill content. Finish with Ctrl+Z then Enter on Windows, or Ctrl+D on Unix:")
    body = sys.stdin.read().strip()
    tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    front = "---\n"
    front += f"name: {name}\n"
    front += f"tags: {tags_list}\n"
    if when:
        front += f"when: {when}\n"
    front += "---\n\n"
    path.write_text(front + body + "\n", encoding="utf-8")
    click.echo(f"Saved: {path}")


@skill.command("edit")
@click.argument("name", type=str)
def skill_edit(name: str) -> None:
    """Open a skill with $EDITOR, or notepad on Windows."""
    path = paths.skills_dir() / f"{name}.md"
    if not path.exists():
        click.echo(f"Skill not found: {name}")
        sys.exit(1)
    editor = os.environ.get("EDITOR") or ("notepad" if os.name == "nt" else "vi")
    subprocess.run([editor, str(path)])


@skill.command("use")
@click.argument("name", type=str)
def skill_use(name: str) -> None:
    """Force a skill to be injected the next time this project starts."""
    project_dir = Path.cwd()
    if not (project_dir / ".cohub").exists():
        click.echo("No .cohub/ directory found. Run cohub init first.")
        sys.exit(1)
    meta = proj.read_meta(project_dir)
    skills_section = meta.get("skills") or {}
    force = skills_section.get("force") or []
    if name not in force:
        force.append(name)
    skills_section["force"] = force
    meta["skills"] = skills_section
    proj.write_meta(project_dir, meta)
    click.echo(f"Marked for forced injection: {name}")
