"""cohub start <cli> - build context and launch a CLI."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import click

from ..core import project as proj
from ..core.adapter import load_adapter
from ..core.skills import collect_skills, render_skills_block
from ..core.heartbeat import HeartbeatThread, register_session, unregister_session, new_session_id
from ..core.summarizer import summarize_or_prompt


def _build_system_prompt(project_dir: Path, meta: dict) -> str:
    tags = meta.get("tags", []) or []
    forced = ((meta.get("skills") or {}).get("force") or [])
    skills = collect_skills(tags, forced)
    parts: list[str] = []

    skills_block = render_skills_block(skills)
    if skills_block:
        parts.append(skills_block)

    handoff = proj.read_handoff(project_dir)
    if handoff.strip():
        parts.append("# Previous Session Handoff\n\n" + handoff)

    state = proj.read_state(project_dir)
    if state.strip():
        parts.append("# Project State\n\n" + state)

    parts.append(
        "# cohub Coordination Notes\n"
        "You are working inside a cohub-coordinated environment. "
        "When the session exits, cohub will generate a handoff summary. "
        "State important progress explicitly so it can be summarized."
    )
    return "\n\n---\n\n".join(parts)


@click.command()
@click.argument("cli_name", type=str)
def start(cli_name: str) -> None:
    """Launch a CLI with handoff, state, and skills injected."""
    project_dir = Path.cwd()
    cohub_dir = project_dir / ".cohub"
    if not cohub_dir.exists():
        click.echo("No .cohub/ directory found. Run: cohub init")
        sys.exit(1)

    meta = proj.read_meta(project_dir)

    actives = proj.read_active_entries(project_dir)
    if actives:
        click.echo("Other active sessions:")
        for entry in actives:
            click.echo("  " + entry.raw)
        click.echo()

    try:
        adapter = load_adapter(cli_name)
    except Exception as e:
        click.echo(f"Unable to load adapter '{cli_name}': {e}")
        sys.exit(1)

    system_prompt = _build_system_prompt(project_dir, meta)
    cmd = adapter.build_command(system_prompt, str(project_dir))

    session_id = new_session_id(cli_name)
    pid = os.getpid()
    register_session(project_dir, session_id, cli_name, pid, doing="(just started)")
    hb = HeartbeatThread(project_dir, session_id)
    hb.start()

    click.echo(f"Starting {cli_name}, session={session_id}")
    rc = 0
    try:
        # Inherit stdio so the user can interact with the CLI normally.
        completed = subprocess.run(cmd, cwd=str(project_dir))
        rc = completed.returncode
    except KeyboardInterrupt:
        rc = 130
    except FileNotFoundError:
        click.echo(f"Executable not found: {cmd[0]}. Confirm that {cli_name} is installed and available on PATH.")
        rc = 127
    finally:
        hb.stop()
        unregister_session(project_dir, session_id)

    click.echo(f"{cli_name} exited (rc={rc}); generating handoff summary...")
    try:
        summarize_or_prompt(project_dir, adapter)
    except Exception as e:
        click.echo(f"Summary failed: {e}")

    sys.exit(rc)
