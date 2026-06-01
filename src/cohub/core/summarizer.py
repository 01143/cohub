"""Handoff summary generator with Anthropic API and manual fallback."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from . import project as proj


_SUMMARY_PROMPT = """Read the following transcript and write a handoff summary.
The summary must include:
- Current task
- Completed work
- Blockers
- Decisions
- Suggested next steps

Use exactly this Markdown structure in English:

# Session Handoff Summary (<CLI>, <timestamp>)

## Current Task
...

## Completed
- ...

## Blockers
- ...

## Decisions
- ...

## Suggested Next Steps
- ...

Be concise and specific. If a section has no content, write "None".
"""


def _transcript_to_text(transcript: list[dict]) -> str:
    parts: list[str] = []
    for msg in transcript:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, list):
            # Join content blocks into a string.
            content = "\n".join(
                (c.get("text") if isinstance(c, dict) else str(c)) or "" for c in content
            )
        parts.append(f"### {role}\n{content}")
    return "\n\n".join(parts)


def call_anthropic_summarize(transcript_text: str) -> str | None:
    """Return Markdown on success, otherwise None."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic  # type: ignore
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        # Keep very long transcripts bounded.
        if len(transcript_text) > 80000:
            transcript_text = transcript_text[-80000:]
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": _SUMMARY_PROMPT + "\n\n--- Transcript ---\n\n" + transcript_text,
                }
            ],
        )
        # resp.content is a list of ContentBlock objects.
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
    """Ask the user to manually enter a summary."""
    click.echo("Automatic summary is unavailable. Briefly describe this session (optional; Ctrl+Z+Enter to finish on Windows):")
    try:
        body = sys.stdin.read().strip()
    except Exception:
        body = ""
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    body = body or "None"
    return (
        f"# Session Handoff Summary ({cli_name}, {ts})\n\n"
        f"## Current Task\n{body}\n\n"
        "## Completed\nNone\n\n"
        "## Blockers\nNone\n\n"
        "## Decisions\nNone\n\n"
        "## Suggested Next Steps\nNone\n"
    )


def summarize_or_prompt(project_dir: Path, adapter: Any) -> None:
    """Attempt automatic summary, then fall back to manual input."""
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
        click.echo("(automatic summary unavailable; falling back to manual input)")
        summary_md = _fallback_prompt_user(cli_name)

    proj.write_handoff(project_dir, summary_md)
    click.echo(f"handoff.md updated ({len(summary_md)} characters)")
