"""测试 summarizer 的 transcript 文本化和 fallback 路径。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cohub.core import summarizer as sm


def test_transcript_to_text_handles_str_and_list() -> None:
    transcript = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": [{"type": "text", "text": "回答"}, {"type": "text", "text": "第二段"}]},
    ]
    text = sm._transcript_to_text(transcript)
    assert "你好" in text
    assert "回答" in text
    assert "第二段" in text
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
    # 准备 .cohub 目录
    (tmp_path / ".cohub").mkdir()

    # 没有 transcript → 直接走 fallback → stdin 输入摘要
    monkeypatch.setattr("sys.stdin", FakeStdin("正在测试 cohub"))
    sm.summarize_or_prompt(tmp_path, _FakeAdapter())

    handoff = (tmp_path / ".cohub" / "handoff.md").read_text(encoding="utf-8")
    assert "正在测试 cohub" in handoff
    assert "# 上次会话摘要" in handoff


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
        return [{"role": "user", "content": "改 bug"}, {"role": "assistant", "content": "已改"}]


def test_summarize_uses_anthropic_when_available(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".cohub").mkdir()

    # mock 掉 Anthropic 调用
    with patch.object(sm, "call_anthropic_summarize", return_value="# 上次会话摘要(claude, X)\n\n## 在做什么\n改 bug\n"):
        sm.summarize_or_prompt(tmp_path, _FakeAdapterWithTranscript())

    handoff = (tmp_path / ".cohub" / "handoff.md").read_text(encoding="utf-8")
    assert "改 bug" in handoff
