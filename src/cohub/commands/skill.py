"""cohub skill <subcommand> —— 技能库管理。"""
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
    """管理 ~/.cohub/skills/ 下的个人技能库。"""


@skill.command("list")
@click.option("--tag", "tag", default=None, help="按 tag 过滤。")
def skill_list(tag: str | None) -> None:
    skills = sk_mod.load_all_skills()
    if tag:
        skills = [s for s in skills if tag in s.tags]
    if not skills:
        click.echo("(无 skill)")
        return
    for s in skills:
        click.echo(f"- {s.name}  tags={s.tags}  when={s.when}")


@skill.command("save")
@click.argument("name", type=str)
@click.option("--tags", "tags", default="", help="逗号分隔的 tags。")
@click.option("--when", "when", default="", help="什么时候用。")
def skill_save(name: str, tags: str, when: str) -> None:
    """从 stdin 读取技能内容并保存。"""
    paths.skills_dir().mkdir(parents=True, exist_ok=True)
    path = paths.skills_dir() / f"{name}.md"
    if path.exists():
        if not click.confirm(f"{path} 已存在,覆盖?", default=False):
            return

    click.echo("请粘贴技能内容,结束按 Ctrl+Z 然后回车 (Windows) 或 Ctrl+D (Unix):")
    body = sys.stdin.read().strip()
    tags_list = [t.strip() for t in tags.split(",") if t.strip()]

    front = "---\n"
    front += f"name: {name}\n"
    front += f"tags: {tags_list}\n"
    if when:
        front += f"when: {when}\n"
    front += "---\n\n"
    path.write_text(front + body + "\n", encoding="utf-8")
    click.echo(f"已保存: {path}")


@skill.command("edit")
@click.argument("name", type=str)
def skill_edit(name: str) -> None:
    """用 $EDITOR (或 notepad) 打开 skill。"""
    path = paths.skills_dir() / f"{name}.md"
    if not path.exists():
        click.echo(f"找不到 skill: {name}")
        sys.exit(1)
    editor = os.environ.get("EDITOR") or ("notepad" if os.name == "nt" else "vi")
    subprocess.run([editor, str(path)])


@skill.command("use")
@click.argument("name", type=str)
def skill_use(name: str) -> None:
    """标记某 skill 在本项目下一次启动时强制注入。"""
    project_dir = Path.cwd()
    if not (project_dir / ".cohub").exists():
        click.echo("当前目录没有 .cohub/,请先 cohub init。")
        sys.exit(1)
    meta = proj.read_meta(project_dir)
    skills_section = meta.get("skills") or {}
    force = skills_section.get("force") or []
    if name not in force:
        force.append(name)
    skills_section["force"] = force
    meta["skills"] = skills_section
    proj.write_meta(project_dir, meta)
    click.echo(f"已标记 force 注入: {name}")
