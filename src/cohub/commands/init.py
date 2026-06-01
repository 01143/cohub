"""cohub init —— 在当前目录建立 .cohub/ 项目状态目录。"""
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
    """在当前目录创建 .cohub/ 子目录,交互式生成 meta.yaml。"""
    project_dir = Path.cwd()
    cohub_dir = project_dir / ".cohub"

    if cohub_dir.exists():
        click.echo(f"已存在 {cohub_dir},取消。")
        sys.exit(1)

    # 交互式收集元数据
    project_name = click.prompt("项目名称", default=project_dir.name)
    goal = click.prompt("项目目标(一句话)", default="(待填)")
    tags_raw = click.prompt("tags(逗号分隔,决定注入哪些 skills)", default="")
    languages_raw = click.prompt("language(逗号分隔)", default="")

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    languages = [l.strip() for l in languages_raw.split(",") if l.strip()]

    ensure_cohub_dir(project_dir)
    meta = default_meta(project_name=project_name, goal=goal, tags=tags, language=languages)
    write_meta(project_dir, meta)

    # 初始化各 markdown
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    (cohub_dir / "handoff.md").write_text(
        f"# 上次会话摘要(无, {now})\n\n## 在做什么\n无\n\n## 已完成\n无\n\n## 卡在哪\n无\n\n## 决策记录\n无\n\n## 下一步建议\n无\n",
        encoding="utf-8",
    )
    (cohub_dir / "state.md").write_text(
        f"# 项目状态(更新于 {now})\n\n## 目标\n{goal}\n\n## 当前进度\n- (待填)\n\n## 关键约定\n- (待填)\n\n## 最近改动\n无\n",
        encoding="utf-8",
    )
    (cohub_dir / "active.md").write_text(f"# 活跃会话({now})\n\n", encoding="utf-8")
    (cohub_dir / "snapshots.md").write_text("", encoding="utf-8")
    (cohub_dir / "reviews").mkdir(exist_ok=True)

    click.echo(f"已创建 {cohub_dir}")

    # git 检测
    if not is_git_repo(project_dir):
        if click.confirm("当前不是 git 仓库,是否 git init?", default=True):
            git_init(project_dir)
            click.echo("git init 完成")

    click.echo("接下来:cohub start claude")
