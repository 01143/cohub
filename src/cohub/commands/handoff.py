"""cohub handoff —— 手动触发当前会话摘要。"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from ..core.adapter import load_adapter
from ..core.summarizer import summarize_or_prompt


@click.command()
@click.option("--cli", "cli_name", default="claude", show_default=True, help="使用哪个 adapter 找 transcript。")
def handoff(cli_name: str) -> None:
    """手动生成 handoff.md(从最新 transcript 摘要;失败则提示手动输入)。"""
    project_dir = Path.cwd()
    if not (project_dir / ".cohub").exists():
        click.echo("当前目录没有 .cohub/,请先 cohub init。")
        sys.exit(1)
    try:
        adapter = load_adapter(cli_name)
    except Exception as e:
        click.echo(f"adapter 加载失败: {e}")
        sys.exit(1)
    summarize_or_prompt(project_dir, adapter)
