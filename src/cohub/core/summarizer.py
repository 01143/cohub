"""接力简报生成器 —— Anthropic API,带 fallback。"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from . import project as proj


_SUMMARY_PROMPT = """请阅读以下对话记录,生成接力简报。简报需包含:
- 在做什么(当前任务)
- 已完成(具体动作和产出)
- 卡在哪(未解决的问题)
- 决策记录(选择了什么,弃了什么,为什么)
- 下一步建议

输出格式: 严格按以下 markdown 结构,中文:

# 上次会话摘要(<CLI>, <时间戳>)

## 在做什么
...

## 已完成
- ...

## 卡在哪
- ...

## 决策记录
- ...

## 下一步建议
- ...

要求: 简洁、具体、不要废话。如果某节没有内容,写"无"。
"""


def _transcript_to_text(transcript: list[dict]) -> str:
    parts: list[str] = []
    for msg in transcript:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, list):
            # 把 list 拼成字符串(content blocks)
            content = "\n".join(
                (c.get("text") if isinstance(c, dict) else str(c)) or "" for c in content
            )
        parts.append(f"### {role}\n{content}")
    return "\n\n".join(parts)


def call_anthropic_summarize(transcript_text: str) -> str | None:
    """成功返回 markdown,失败返回 None。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic  # type: ignore
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        # 截断超长 transcript,避免 token 爆炸
        if len(transcript_text) > 80000:
            transcript_text = transcript_text[-80000:]
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": _SUMMARY_PROMPT + "\n\n--- 对话记录 ---\n\n" + transcript_text,
                }
            ],
        )
        # resp.content 是 list[ContentBlock]
        chunks = []
        for block in resp.content:
            text = getattr(block, "text", None)
            if text:
                chunks.append(text)
        out = "\n".join(chunks).strip()
        return out or None
    except Exception:
        return None


def _fallback_prompt_user(cli_name: str) -> str:
    """让用户手动输入摘要(可留空)。"""
    click.echo("无法自动摘要,请简要描述本次会话(可留空,Ctrl+Z+Enter 结束):")
    try:
        body = sys.stdin.read().strip()
    except Exception:
        body = ""
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    body = body or "无"
    return (
        f"# 上次会话摘要({cli_name}, {ts})\n\n"
        f"## 在做什么\n{body}\n\n"
        "## 已完成\n无\n\n"
        "## 卡在哪\n无\n\n"
        "## 决策记录\n无\n\n"
        "## 下一步建议\n无\n"
    )


def summarize_or_prompt(project_dir: Path, adapter: Any) -> None:
    """尝试自动摘要,失败则提示用户手动输入。结果写入 handoff.md。"""
    cli_name = getattr(adapter, "NAME", "unknown")
    transcript_path = None
    transcript: list[dict] | None = None
    try:
        transcript_path = adapter.find_latest_transcript(str(project_dir))
    except Exception:
        transcript_path = None

    if transcript_path:
        try:
            transcript = adapter.parse_transcript(Path(transcript_path))
        except Exception:
            transcript = None

    summary_md: str | None = None
    if transcript:
        text = _transcript_to_text(transcript)
        summary_md = call_anthropic_summarize(text)

    if not summary_md:
        click.echo("(自动摘要不可用,降级为手动输入)")
        summary_md = _fallback_prompt_user(cli_name)

    proj.write_handoff(project_dir, summary_md)
    click.echo(f"handoff.md 已更新 ({len(summary_md)} 字符)")
