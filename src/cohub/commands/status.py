"""cohub status —— 美化打印 active.md。"""
from __future__ import annotations

from pathlib import Path

import click

from ..core import project as proj


@click.command()
def status() -> None:
    """显示当前项目的活跃会话。"""
    project_dir = Path.cwd()
    cohub_dir = project_dir / ".cohub"
    if not cohub_dir.exists():
        click.echo("当前目录没有 .cohub/,请先 cohub init。")
        return

    entries = proj.read_active_entries(project_dir)
    if not entries:
        click.echo("当前无活跃会话。")
        return

    click.echo("活跃会话:")
    for e in entries:
        marker = " (stale)" if e.is_stale() else ""
        click.echo(f"  [{e.session_id}] {e.cli} PID={e.pid} 启动={e.started} 在做={e.doing} 心跳={e.heartbeat}{marker}")
