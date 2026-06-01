"""cohub CLI 主入口 (click)。"""
from __future__ import annotations

import io
import sys

# Windows 上默认 stdio codec 是 GBK / cp936,会污染中文输入。强制 UTF-8。
def _force_utf8_stdio() -> None:
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # py3.7+
        except Exception:
            # Fallback: 包一层 TextIOWrapper
            try:
                buffer = getattr(stream, "buffer", None)
                if buffer is not None:
                    setattr(sys, stream_name, io.TextIOWrapper(buffer, encoding="utf-8", errors="replace"))
            except Exception:
                pass


_force_utf8_stdio()

import click  # noqa: E402

from .commands import (
    init as cmd_init,
    start as cmd_start,
    status as cmd_status,
    handoff as cmd_handoff,
    review as cmd_review,
    snap as cmd_snap,
    rewind as cmd_rewind,
    skill as cmd_skill,
)


@click.group(help="cohub —— 本地多 CLI Agent 工作流协调工具。")
@click.version_option(package_name="cohub")
def cli() -> None:
    """根命令组,具体功能见各子命令。"""


cli.add_command(cmd_init.init)
cli.add_command(cmd_start.start)
cli.add_command(cmd_status.status)
cli.add_command(cmd_handoff.handoff)
cli.add_command(cmd_review.review)
cli.add_command(cmd_snap.snap)
cli.add_command(cmd_rewind.rewind)
cli.add_command(cmd_skill.skill)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
