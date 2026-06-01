"""cohub review —— MVP 占位,P1 实现。"""
from __future__ import annotations

import click


@click.command()
@click.option("--with", "cli_name", default="codex", help="审查所用 CLI。")
def review(cli_name: str) -> None:
    """[P1] 启动指定 CLI 做只读审查。当前 MVP 未实现。"""
    click.echo("review 命令在 MVP 阶段未实现,留作 P1。")
    click.echo("当前推荐:cohub snap 保存进度后,手动启动 codex 并粘贴 git diff。")
