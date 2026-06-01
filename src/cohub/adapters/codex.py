"""Codex CLI adapter (OpenAI codex-cli).

Implementation notes:
- Codex does not expose an `--append-system-prompt` style flag. cohub passes
  the project context as the initial user prompt.
- Transcript fields are not assumed stable, so parse_transcript is defensive.
- Exact project-directory matching is deferred; the adapter currently returns
  the newest global JSONL transcript.
"""
from __future__ import annotations

import json
from pathlib import Path

NAME = "codex"
INJECTION_METHOD = "initial_prompt"


def build_command(system_prompt: str, project_dir: str) -> list[str]:
    """Launch Codex and inject the system_prompt as the initial prompt."""
    if not system_prompt.strip():
        return ["codex", "--cd", project_dir]
    prefix = (
        "The following is the current project context injected by cohub "
        "(handoff + state + skills). Follow it in this session:\n\n---\n\n"
    )
    return ["codex", "--cd", project_dir, prefix + system_prompt]


_SESSIONS_DIRS = [
    Path.home() / ".codex" / "sessions",
    Path.home() / ".codex" / "history",
]


def find_latest_transcript(project_dir: str) -> Path | None:
    """Find the newest JSONL file in Codex session directories.

    This currently returns the newest global transcript by mtime.
    """
    candidates: list[Path] = []
    for d in _SESSIONS_DIRS:
        if d.exists():
            candidates.extend(d.rglob("*.jsonl"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_transcript(path: Path) -> list[dict] | None:
    """Parse Codex JSONL into [{role, content}, ...].

    Codex JSONL fields are not assumed stable, so common keys are tried.
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
