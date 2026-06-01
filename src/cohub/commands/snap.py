"""cohub snap "<说明>" —— git add + commit + tag + snapshots.md。"""
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
    """提交快照: git add -A && git commit && git tag snap-NNN。"""
    project_dir = Path.cwd()
    if not (project_dir / ".cohub").exists():
        click.echo("当前目录没有 .cohub/,请先 cohub init。")
        sys.exit(1)
    if not gw.is_git_repo(project_dir):
        click.echo("当前目录不是 git 仓库,无法快照。")
        sys.exit(1)

    try:
        gw.run_git(project_dir, ["add", "-A"])
        # 即使没有改动也尝试 commit,有改动 → 成功;无改动 → 跳过
        commit_rc, commit_out = gw.run_git(project_dir, ["commit", "-m", message], check=False)
        if commit_rc != 0 and "nothing to commit" not in commit_out and "no changes" not in commit_out:
            click.echo(f"git commit 失败: {commit_out}")
            sys.exit(1)

        tag = gw.next_snap_tag(project_dir)
        gw.run_git(project_dir, ["tag", tag])
    except gw.GitError as e:
        click.echo(f"git 操作失败: {e}")
        sys.exit(1)

    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    proj.append_snapshot(project_dir, ts, message, tag)
    click.echo(f"快照已保存: {tag}  {message}")
