"""Codex CLI adapter(OpenAI codex-cli)。

实施说明:
- codex 没有 `--append-system-prompt` 类的 flag。我们把项目上下文
  (handoff + state + skills 拼成的 system_prompt)作为**初始 user prompt**
  传入,效果上接近 system prompt。
- transcript 位置常见为 ~/.codex/sessions/YYYY-MM-DD/<uuid>.jsonl;
  字段未公开稳定,parse_transcript 做容错解析,失败返回 None 触发 fallback。
- 项目目录精准匹配(按 cwd 过滤)留作 P1.5,当前返回全局最新 jsonl。
"""
from __future__ import annotations

import json
from pathlib import Path

NAME = "codex"
INJECTION_METHOD = "initial_prompt"


def build_command(system_prompt: str, project_dir: str) -> list[str]:
    """启动 codex,把 system_prompt 作为初始 prompt 注入。"""
    if not system_prompt.strip():
        return ["codex", "--cd", project_dir]
    prefix = (
        "以下是当前项目的上下文(由 cohub 注入,含 handoff + state + skills),"
        "请在本次会话中遵循:\n\n---\n\n"
    )
    return ["codex", "--cd", project_dir, prefix + system_prompt]


_SESSIONS_DIRS = [
    Path.home() / ".codex" / "sessions",
    Path.home() / ".codex" / "history",
]


def find_latest_transcript(project_dir: str) -> Path | None:
    """在 codex sessions 目录里找最新的 jsonl。

    返回全局最新一个(按 mtime)。按 cwd 精准过滤留作 P1.5。
    找不到返回 None。
    """
    candidates: list[Path] = []
    for d in _SESSIONS_DIRS:
        if d.exists():
            candidates.extend(d.rglob("*.jsonl"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_transcript(path: Path) -> list[dict] | None:
    """解析 codex jsonl 为 [{role, content}, ...]。

    codex 的 jsonl 字段未公开稳定,尝试常见键。解析失败返回 None
    (touch fallback,让 summarizer 走手动输入路径)。
    """
    try:
        events: list[dict] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = evt.get("role") or evt.get("type") or evt.get("kind")
            content = evt.get("content") or evt.get("text") or evt.get("message") or ""
            if isinstance(content, list):
                parts = []
                for c in content:
                    if isinstance(c, dict):
                        parts.append(c.get("text", "") or c.get("content", ""))
                    else:
                        parts.append(str(c))
                content = "\n".join(p for p in parts if p)
            if role and content:
                events.append({"role": str(role), "content": str(content)})
        return events if events else None
    except Exception:
        return None
