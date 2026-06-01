"""测试 git_wrap 的快照编号递增。"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from cohub.core import git_wrap as gw


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _git_available(), reason="git not in PATH")


def _init_repo(p: Path) -> None:
    gw.run_git(p, ["init", "-q"])
    # 必备:本地 user.email/name
    gw.run_git(p, ["config", "user.email", "test@example.com"])
    gw.run_git(p, ["config", "user.name", "test"])
    (p / "a.txt").write_text("hi", encoding="utf-8")
    gw.run_git(p, ["add", "-A"])
    gw.run_git(p, ["commit", "-q", "-m", "init"])


def test_is_git_repo_false(tmp_path: Path) -> None:
    assert gw.is_git_repo(tmp_path) is False


def test_next_snap_tag_starts_at_001(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    assert gw.next_snap_tag(tmp_path) == "snap-001"
    gw.run_git(tmp_path, ["tag", "snap-001"])
    assert gw.next_snap_tag(tmp_path) == "snap-002"
    gw.run_git(tmp_path, ["tag", "snap-005"])
    assert gw.next_snap_tag(tmp_path) == "snap-006"
