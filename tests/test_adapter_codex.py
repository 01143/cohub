"""Basic interface tests for the Codex adapter."""
from __future__ import annotations

import json
from pathlib import Path

from cohub.adapters import codex


def test_codex_module_constants():
    assert codex.NAME == "codex"
    assert codex.INJECTION_METHOD == "initial_prompt"


def test_build_command_empty_prompt():
    cmd = codex.build_command("", "/tmp/proj")
    assert cmd[0] == "codex"
    assert "--cd" in cmd and "/tmp/proj" in cmd
    assert len(cmd) == 3


def test_build_command_with_prompt():
    cmd = codex.build_command("hello world", "/tmp/proj")
    assert cmd[0] == "codex"
    assert "--cd" in cmd and "/tmp/proj" in cmd
    assert "hello world" in cmd[-1]
    assert "current project context" in cmd[-1]


def test_find_latest_transcript_no_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    result = codex.find_latest_transcript(str(tmp_path))
    assert result is None or isinstance(result, Path)


def test_parse_transcript_valid(tmp_path):
    p = tmp_path / "session.jsonl"
    lines = [
        json.dumps({"role": "user", "content": "hello"}),
        json.dumps({"role": "assistant", "content": [{"type": "text", "text": "here"}]}),
        json.dumps({"type": "tool_call", "name": "bash"}),
        "",
        "not json at all",
    ]
    p.write_text("\n".join(lines), encoding="utf-8")
    result = codex.parse_transcript(p)
    assert result is not None
    assert len(result) == 2
    assert result[0] == {"role": "user", "content": "hello"}
    assert result[1]["role"] == "assistant"
    assert "here" in result[1]["content"]


def test_parse_transcript_empty_returns_none(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    assert codex.parse_transcript(p) is None


def test_parse_transcript_nonexistent_returns_none(tmp_path):
    p = tmp_path / "missing.jsonl"
    assert codex.parse_transcript(p) is None
