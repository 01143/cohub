"""测试 core.project 的读写与 active.md 解析。"""
from __future__ import annotations

from pathlib import Path

import pytest

from cohub.core import project as proj


def test_meta_round_trip(tmp_path: Path) -> None:
    proj.ensure_cohub_dir(tmp_path)
    meta = proj.default_meta(project_name="demo", goal="测试", tags=["stata"], language=["python"])
    proj.write_meta(tmp_path, meta)
    loaded = proj.read_meta(tmp_path)
    assert loaded["project_name"] == "demo"
    assert loaded["tags"] == ["stata"]
    assert loaded["skills"] == {"force": []}


def test_active_upsert_and_remove(tmp_path: Path) -> None:
    proj.ensure_cohub_dir(tmp_path)
    proj.upsert_active(
        tmp_path,
        session_id="claude-123456-001",
        cli="claude",
        pid=42,
        started="2026-05-13T10:00:00+08:00",
        doing="写测试",
        heartbeat="2026-05-13T10:01:00+08:00",
    )
    entries = proj.read_active_entries(tmp_path)
    assert len(entries) == 1
    e = entries[0]
    assert e.session_id == "claude-123456-001"
    assert e.cli == "claude"
    assert e.pid == 42
    assert e.doing == "写测试"

    # 再 upsert 同 session_id,更新 doing,不重复
    proj.upsert_active(
        tmp_path,
        session_id="claude-123456-001",
        cli="claude",
        pid=42,
        started="2026-05-13T10:00:00+08:00",
        doing="改测试",
        heartbeat="2026-05-13T10:02:00+08:00",
    )
    entries = proj.read_active_entries(tmp_path)
    assert len(entries) == 1
    assert entries[0].doing == "改测试"

    # 加第二个 session
    proj.upsert_active(
        tmp_path,
        session_id="codex-999999-002",
        cli="codex",
        pid=99,
        started="2026-05-13T10:05:00+08:00",
        doing="审查",
        heartbeat="2026-05-13T10:05:00+08:00",
    )
    entries = proj.read_active_entries(tmp_path)
    assert len(entries) == 2

    # 移除
    proj.remove_active(tmp_path, "claude-123456-001")
    entries = proj.read_active_entries(tmp_path)
    assert len(entries) == 1
    assert entries[0].session_id == "codex-999999-002"


def test_active_stale_detection(tmp_path: Path) -> None:
    proj.ensure_cohub_dir(tmp_path)
    # 心跳一年前
    proj.upsert_active(
        tmp_path,
        session_id="claude-aaa-001",
        cli="claude",
        pid=1,
        started="2025-01-01T00:00:00+08:00",
        doing="X",
        heartbeat="2025-01-01T00:00:00+08:00",
    )
    entries = proj.read_active_entries(tmp_path)
    assert entries[0].is_stale()


def test_snapshot_append_and_read(tmp_path: Path) -> None:
    proj.ensure_cohub_dir(tmp_path)
    proj.append_snapshot(tmp_path, "2026-05-13T10:00:00+08:00", "首次提交", "snap-001")
    proj.append_snapshot(tmp_path, "2026-05-13T11:00:00+08:00", "二次", "snap-002")
    snaps = proj.read_snapshots(tmp_path)
    assert len(snaps) == 2
    assert snaps[0].tag == "snap-001"
    assert snaps[1].message == "二次"
