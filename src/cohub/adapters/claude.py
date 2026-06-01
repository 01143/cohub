"""Claude Code adapter.

接入方式: `claude --append-system-prompt "<text>"` (官方 flag,已通过 `claude --help` 验证)
Transcript 位置: ~/.claude/projects/<encoded-cwd>/*.jsonl,JSONL 每行一条事件
每条 user/assistant 事件里 message.content 可能是 str 或 list[{type:"text", text:...}]
"""
from __future__ import annotations

import json
import os
from pathlib import Path

NAME = "claude"
INJECTION_METHOD = "system_prompt_flag"


def _claude_executable() -> str:
    """返回 claude CLI 可执行名。Windows 下 PATH 中通常是 claude.cmd,直接用 'claude' 即可。"""
    return os.environ.get("COHUB_CLAUDE_BIN", "claude")


def build_command(system_prompt: str, project_dir: str) -> list[str]:
    """构造 `claude --append-system-prompt <prompt>` 启动命令。

    --append-system-prompt 把内容附加到默认 system prompt 之后,适合注入接力简报。
    若 prompt 为空,仍然启动 claude(不附加)。
    """
    cmd: list[str] = [_claude_executable()]
    if system_prompt.strip():
        cmd += ["--append-system-prompt", system_prompt]
    return cmd


def _projects_root() -> Path:
    return Path.home() / ".claude" / "projects"


def _encode_cwd(project_dir: str) -> str:
    """Claude Code 用 cwd 路径派生目录名(把分隔符替换为 '-')。

    例如 C:\\Users\\xxy 在磁盘上是 C--Users-xxy。
    我们不假设算法稳定,因此 find_latest_transcript 会同时 fallback 到全局扫描 + cwd 字段匹配。
    """
    p = str(Path(project_dir))
    # 粗略归一化: 替换 ":" "\\" "/" 为 "-"
    out = p.replace(":", "").replace("\\", "-").replace("/", "-")
    # 多 - 合并
    while "--" in out and out.count("--") and not out.startswith("--"):
        # 仅在非开头处不连续替换;实际 Claude Code 似乎保留 "--",所以这里其实不做合并
        break
    return out


def _read_cwd_from_jsonl(p: Path) -> str | None:
    """读 jsonl 中任一条带 cwd 字段的事件,返回该 cwd。"""
    try:
        with p.open("r", encoding="utf-8") as f:
            for _ in range(50):  # 只看前 50 行
                line = f.readline()
                if not line:
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cwd = obj.get("cwd")
                if cwd:
                    return str(cwd)
    except Exception:
        return None
    return None


def find_latest_transcript(project_dir: str) -> Path | None:
    """在 ~/.claude/projects/ 下找最新一条 jsonl,要求其 cwd 字段 == project_dir。

    策略:
      1) 优先扫匹配编码目录名的子目录(常见)。
      2) 兜底全局扫所有 jsonl,读 cwd 字段过滤。
    取 mtime 最大者。
    """
    root = _projects_root()
    if not root.exists():
        return None

    target = str(Path(project_dir)).rstrip("\\/")

    candidates: list[Path] = []
    encoded = _encode_cwd(project_dir)
    direct_dir = root / encoded
    if direct_dir.exists():
        candidates.extend(direct_dir.glob("*.jsonl"))

    if not candidates:
        # 全局扫
        for sub in root.iterdir():
            if not sub.is_dir():
                continue
            candidates.extend(sub.glob("*.jsonl"))

    # 按 cwd 字段过滤
    matching: list[Path] = []
    for p in candidates:
        cwd = _read_cwd_from_jsonl(p)
        if cwd and Path(cwd).resolve() == Path(target).resolve():
            matching.append(p)

    if not matching and candidates and direct_dir.exists():
        # cwd 读不到,但目录名命中,姑且全收
        matching = candidates

    if not matching:
        return None
    matching.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matching[0]


def parse_transcript(path: Path) -> list[dict] | None:
    """逐行 JSONL,提取 user / assistant 消息为 [{role, content}, ...]。

    message.content 兼容 str 和 list[{type:"text", text}]。
    无法解析返回 None。
    """
    try:
        out: list[dict] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = obj.get("type")
                if t not in ("user", "assistant"):
                    continue
                msg = obj.get("message") or {}
                role = msg.get("role") or t
                content = msg.get("content")
                if content is None:
                    # user 事件里 message 有时直接是 {role, content:str}
                    content = obj.get("content", "")
                # 统一成 list[{type:text, text:...}] 或 str → str
                if isinstance(content, list):
                    pieces: list[str] = []
                    for c in content:
                        if isinstance(c, dict):
                            if c.get("type") == "text" and c.get("text"):
                                pieces.append(str(c["text"]))
                            elif c.get("type") == "tool_use":
                                name = c.get("name", "tool")
                                pieces.append(f"[tool_use: {name}]")
                            elif c.get("type") == "tool_result":
                                # tool_result.content 可能再嵌套
                                inner = c.get("content")
                                if isinstance(inner, list):
                                    for ic in inner:
                                        if isinstance(ic, dict) and ic.get("type") == "text":
                                            pieces.append(f"[tool_result] {ic.get('text','')}")
                                elif isinstance(inner, str):
                                    pieces.append(f"[tool_result] {inner}")
                        else:
                            pieces.append(str(c))
                    text = "\n".join(p for p in pieces if p)
                elif isinstance(content, str):
                    text = content
                else:
                    text = str(content) if content else ""
                if text:
                    out.append({"role": role, "content": text})
        return out or None
    except Exception:
        return None
