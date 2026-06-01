"""测试 claude adapter 的 build_command + transcript 解析。"""
from __future__ import annotations

import json
from pathlib import Path

from cohub.adapters import claude as claude_adapter


def test_build_command_with_prompt() -> None:
    cmd = claude_adapter.build_command("hello world", "C:/proj")
    assert cmd[0] == "claude"
    assert "--append-system-prompt" in cmd
    idx = cmd.index("--append-system-prompt")
    assert cmd[idx + 1] == "hello world"


def test_build_command_empty_prompt_skips_flag() -> None:
    cmd = claude_adapter.build_command("   ", "C:/proj")
    assert cmd == ["claude"]


def test_parse_transcript_extracts_user_and_assistant(tmp_path: Path) -> None:
    p = tmp_path / "fake.jsonl"
    lines = [
        # 非对话事件应被忽略
        {"type": "permission-mode"},
        # user 消息(content 是 str)
        {
            "type": "user",
            "message": {"role": "user", "content": "你好"},
            "cwd": str(tmp_path),
        },
        # assistant 消息(content 是 list)
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "你好,我是 Claude"},
                    {"type": "tool_use", "name": "Read"},
                ],
            },
        },
        # 另一条 user
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "content": "ok"}],
            },
        },
    ]
    p.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")

    parsed = claude_adapter.parse_transcript(p)
    assert parsed is not None
    assert len(parsed) >= 2  # 至少两条对话内容
    roles = [m["role"] for m in parsed]
    assert "user" in roles
    assert "assistant" in roles
    # 检查文本提取
    blob = "\n".join(m["content"] for m in parsed)
    assert "你好" in blob
    assert "Claude" in blob


def test_parse_transcript_broken_file_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "broken.jsonl"
    p.write_text("not json\nalso not json\n", encoding="utf-8")
    # 全部非 JSON,parsed 为空 list → 函数返回 None
    parsed = claude_adapter.parse_transcript(p)
    assert parsed is None


def test_find_latest_transcript_matches_cwd(tmp_path: Path, monkeypatch) -> None:
    # 准备假 ~/.claude/projects 目录
    fake_home = tmp_path / "home"
    fake_projects = fake_home / ".claude" / "projects" / "X--proj"
    fake_projects.mkdir(parents=True)

    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    # 一个匹配 cwd 的 jsonl
    jl = fake_projects / "abc.jsonl"
    jl.write_text(
        json.dumps({"type": "user", "cwd": str(project_dir), "message": {"role": "user", "content": "hi"}}) + "\n",
        encoding="utf-8",
    )

    # 一个不匹配 cwd 的
    jl2 = fake_projects / "def.jsonl"
    jl2.write_text(
        json.dumps({"type": "user", "cwd": "C:/other", "message": {"role": "user", "content": "x"}}) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(Path, "home", lambda: fake_home)

    found = claude_adapter.find_latest_transcript(str(project_dir))
    assert found is not None
    assert found.name == "abc.jsonl"
