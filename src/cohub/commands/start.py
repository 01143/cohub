"""cohub start <cli> —— 拼接 system prompt 并启动 CLI。"""
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
        parts.append("# 上次会话接力\n\n" + handoff)

    state = proj.read_state(project_dir)
    if state.strip():
        parts.append("# 项目状态\n\n" + state)

    parts.append(
        "# cohub 协调说明\n你正在 cohub 协调环境中工作。"
        "退出会话时,cohub 会自动生成接力简报。"
        "重要进展请在对话中明确表达,便于摘要。"
    )
    return "\n\n---\n\n".join(parts)


@click.command()
@click.argument("cli_name", type=str)
def start(cli_name: str) -> None:
    """启动指定 CLI,自动注入 handoff + state + skills 作为 system prompt。"""
    project_dir = Path.cwd()
    cohub_dir = project_dir / ".cohub"
    if not cohub_dir.exists():
        click.echo("当前目录没有 .cohub/,请先运行: cohub init")
        sys.exit(1)

    meta = proj.read_meta(project_dir)

    # 显示已活跃会话
    actives = proj.read_active_entries(project_dir)
    if actives:
        click.echo("提示:当前已有活跃会话:")
        for entry in actives:
            click.echo("  " + entry.raw)
        click.echo()

    try:
        adapter = load_adapter(cli_name)
    except Exception as e:
        click.echo(f"无法加载 adapter '{cli_name}': {e}")
        sys.exit(1)

    system_prompt = _build_system_prompt(project_dir, meta)
    cmd = adapter.build_command(system_prompt, str(project_dir))

    session_id = new_session_id(cli_name)
    pid = os.getpid()
    register_session(project_dir, session_id, cli_name, pid, doing="(刚启动)")
    hb = HeartbeatThread(project_dir, session_id)
    hb.start()

    click.echo(f"启动 {cli_name},session={session_id}")
    rc = 0
    try:
        # 直接 inherit stdio,让用户和 CLI 正常交互
        completed = subprocess.run(cmd, cwd=str(project_dir))
        rc = completed.returncode
    except KeyboardInterrupt:
        rc = 130
    except FileNotFoundError:
        click.echo(f"找不到可执行文件: {cmd[0]}。请确认 {cli_name} CLI 已安装并在 PATH 中。")
        rc = 127
    finally:
        hb.stop()
        unregister_session(project_dir, session_id)

    click.echo(f"{cli_name} 退出 (rc={rc}),开始生成接力简报...")
    try:
        summarize_or_prompt(project_dir, adapter)
    except Exception as e:
        click.echo(f"摘要失败: {e}")

    sys.exit(rc)
