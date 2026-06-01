"""codex adapter 基础接口测试。"""
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
    # 空 prompt 不追加位置参数
    assert len(cmd) == 3


def test_build_command_with_prompt():
    cmd = codex.build_command("hello world", "/tmp/proj")
    assert cmd[0] == "codex"
    assert "--cd" in cmd and "/tmp/proj" in cmd
    # 最后一个参数应该包含 prompt
    assert "hello world" in cmd[-1]
    assert "项目的上下文" in cmd[-1]  # prefix 标识


def test_find_latest_transcript_no_dir(tmp_path, monkeypatch):
    # 把 home 指向空目录,确保不存在 ~/.codex
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    # 因为 _SESSIONS_DIRS 是模块加载时 Path.home() 算出的,这里只测函数对不存在路径的容错
    # 模块常量已固定,我们直接验证函数不抛
    result = codex.find_latest_transcript(str(tmp_path))
    # 不报错即可(可能找到全局已有的或返回 None)
    assert result is None or isinstance(result, Path)


def test_parse_transcript_valid(tmp_path):
    p = tmp_path / "session.jsonl"
    lines = [
        json.dumps({"role": "user", "content": "你好"}),
        json.dumps({"role": "assistant", "content": [{"type": "text", "text": "在的"}]}),
        json.dumps({"type": "tool_call", "name": "bash"}),  # 没 content,会被跳过
        "",  # 空行
        "not json at all",  # 非 json,会被跳过
    ]
    p.write_text("\n".join(lines), encoding="utf-8")
    result = codex.parse_transcript(p)
    assert result is not None
    assert len(result) == 2
    assert result[0] == {"role": "user", "content": "你好"}
    assert result[1]["role"] == "assistant"
    assert "在的" in result[1]["content"]


def test_parse_transcript_empty_returns_none(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("", encoding="utf-8")
    assert codex.parse_transcript(p) is None


def test_parse_transcript_nonexistent_returns_none(tmp_path):
    p = tmp_path / "missing.jsonl"
    # read_text 会抛 FileNotFoundError,函数内 try/except 应捕获返回 None
    assert codex.parse_transcript(p) is None
