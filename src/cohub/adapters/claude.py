"""Claude Code adapter.

Integration method: `claude --append-system-prompt "<text>"`.
Transcript location: ~/.claude/projects/<encoded-cwd>/*.jsonl.
Each user/assistant event may contain message.content as str or list[{type:"text", text:...}].
"""
from __future__ import annotations

import json
import os
from pathlib import Path

NAME = "claude"
INJECTION_METHOD = "system_prompt_flag"


def _claude_executable() -> str:
    """Return the Claude CLI executable name."""
    return os.environ.get("COHUB_CLAUDE_BIN", "claude")


def build_command(system_prompt: str, project_dir: str) -> list[str]:
    """Build `claude --append-system-prompt <prompt>` launch command.

    When the prompt is empty, launch Claude without an appended prompt.
    """
    cmd: list[str] = [_claude_executable()]
    if system_prompt.strip():
        cmd += ["--append-system-prompt", system_prompt]
    return cmd


def _projects_root() -> Path:
    return Path.home() / ".claude" / "projects"


def _encode_cwd(project_dir: str) -> str:
    """Derive a likely Claude Code project directory name from cwd.

    The exact algorithm is not assumed stable, so find_latest_transcript also
    falls back to a global scan and cwd-field matching.
    """
    p = str(Path(project_dir))
    # Rough normalization: replace path separators with hyphens.
    out = p.replace(":", "").replace("\\", "-").replace("/", "-")
    while "--" in out and out.count("--") and not out.startswith("--"):
        # Claude Code may preserve "--"; keep this conservative.
        break
    return out


def _read_cwd_from_jsonl(p: Path) -> str | None:
    """Read the first cwd field found in a JSONL transcript."""
    try:
        with p.open("r", encoding="utf-8") as f:
            for _ in range(50):
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
    """Find the newest Claude JSONL transcript for the given project.

    Strategy:
      1) scan the likely encoded directory first;
      2) fall back to scanning all JSONL files and filtering by cwd.
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
        # Global scan.
        for sub in root.iterdir():
            if not sub.is_dir():
                continue
            candidates.extend(sub.glob("*.jsonl"))

    # Filter by cwd field.
    matching: list[Path] = []
    for p in candidates:
        cwd = _read_cwd_from_jsonl(p)
        if cwd and Path(cwd).resolve() == Path(target).resolve():
            matching.append(p)

    if not matching and candidates and direct_dir.exists():
        # If cwd cannot be read but the directory matched, keep candidates.
        matching = candidates

    if not matching:
        return None
    matching.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matching[0]


def parse_transcript(path: Path) -> list[dict] | None:
    """Extract user/assistant messages from a JSONL transcript.

    message.content may be str or list[{type:"text", text}].
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
                    # Some user events store content directly on the event.
                    content = obj.get("content", "")
                # Normalize list or string content to a string.
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
                                # tool_result.content may be nested.
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
