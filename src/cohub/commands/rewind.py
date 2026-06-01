"""cohub rewind —— 交互式从快照回放。"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from ..core import git_wrap as gw
from ..core import project as proj


@click.command()
def rewind() -> None:
    """交互式列出快照,默认 worktree 只读检出;可选硬重置。"""
    project_dir = Path.cwd()
    if not (project_dir / ".cohub").exists():
        click.echo("当前目录没有 .cohub/,请先 cohub init。")
        sys.exit(1)

    snaps = proj.read_snapshots(project_dir)
    if not snaps:
        click.echo("还没有任何快照,先 cohub snap 一个吧。")
        return

    click.echo("已有快照:")
    for i, s in enumerate(snaps, 1):
        click.echo(f"  [{i}] {s.tag}  {s.timestamp}  {s.message}")

    idx_raw = click.prompt("选择编号(回车取消)", default="", show_default=False)
    if not idx_raw.strip():
        return
    try:
        idx = int(idx_raw) - 1
        chosen = snaps[idx]
    except (ValueError, IndexError):
        click.echo("选择无效,取消。")
        return

    mode = click.prompt("模式: w=worktree(只读), r=硬重置(危险)", default="w")
    if mode == "w":
        target = project_dir / "_history" / chosen.tag
        target.parent.mkdir(exist_ok=True)
        try:
            gw.run_git(project_dir, ["worktree", "add", str(target), chosen.tag])
        except gw.GitError as e:
            click.echo(f"worktree 创建失败: {e}")
            sys.exit(1)
        click.echo(f"已检出 worktree: {target}")
    elif mode == "r":
        if not click.confirm(f"将硬重置当前分支到 {chosen.tag},工作区改动会丢失!继续?", default=False):
            click.echo("取消。")
            return
        try:
            gw.run_git(project_dir, ["reset", "--hard", chosen.tag])
        except gw.GitError as e:
            click.echo(f"reset 失败: {e}")
            sys.exit(1)
        click.echo(f"已硬重置到 {chosen.tag}")
    else:
        click.echo("未知模式,取消。")
