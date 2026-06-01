"""Test transcript text conversion and fallback summary paths."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cohub.core import summarizer as sm


def test_transcript_to_text_handles_str_and_list() -> None:
    transcript = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "answer"}, {"type": "text", "text": "second paragraph"}]},
    ]
    text = sm._transcript_to_text(transcript)
    assert "hello" in text
    assert "answer" in text
    assert "second paragraph" in text
    assert "user" in text and "assistant" in text


def test_call_anthropic_returns_none_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert sm.call_anthropic_summarize("dummy") is None


class _FakeAdapter:
    NAME = "claude"

    def find_latest_transcript(self, project_dir: str):
        return None

    def parse_transcript(self, path: Path):
        return None


def test_summarize_falls_back_to_user_when_no_transcript(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".cohub").mkdir()

    monkeypatch.setattr("sys.stdin", FakeStdin("testing cohub"))
    sm.summarize_or_prompt(tmp_path, _FakeAdapter())

    handoff = (tmp_path / ".cohub" / "handoff.md").read_text(encoding="utf-8")
    assert "testing cohub" in handoff
    assert "# Session Handoff Summary" in handoff


class FakeStdin:
    def __init__(self, text: str):
        self.text = text

    def read(self) -> str:
        return self.text


class _FakeAdapterWithTranscript:
    NAME = "claude"

    def find_latest_transcript(self, project_dir: str):
        return Path("/tmp/fake.jsonl")

    def parse_transcript(self, path: Path):
        return [{"role": "user", "content": "fix bug"}, {"role": "assistant", "content": "fixed"}]


def test_summarize_uses_anthropic_when_available(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".cohub").mkdir()

    with patch.object(sm, "call_anthropic_summarize", return_value="# Session Handoff Summary (claude, X)\n\n## Current Task\nfix bug\n"):
        sm.summarize_or_prompt(tmp_path, _FakeAdapterWithTranscript())

    handoff = (tmp_path / ".cohub" / "handoff.md").read_text(encoding="utf-8")
    assert "fix bug" in handoff
