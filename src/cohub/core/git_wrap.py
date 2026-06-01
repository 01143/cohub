"""Small Git subprocess wrapper without GitPython."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def run_git(project_dir: Path, args: list[str], check: bool = True) -> tuple[int, str]:
    """Run Git and return (returncode, combined_output)."""
    cmd = ["git"] + args
    proc = subprocess.run(
        cmd,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        shell=False,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if check and proc.returncode != 0:
        raise GitError(f"{' '.join(cmd)} failed: {out.strip()}")
    return proc.returncode, out


def is_git_repo(project_dir: Path) -> bool:
    rc, _ = run_git(project_dir, ["rev-parse", "--is-inside-work-tree"], check=False)
    return rc == 0


def git_init(project_dir: Path) -> None:
    run_git(project_dir, ["init"])


def list_tags(project_dir: Path) -> list[str]:
    rc, out = run_git(project_dir, ["tag", "--list", "snap-*"], check=False)
    if rc != 0:
        return []
    return [t.strip() for t in out.splitlines() if t.strip()]


_SNAP_TAG_RE = re.compile(r"^snap-(\d+)$")


def next_snap_tag(project_dir: Path) -> str:
    tags = list_tags(project_dir)
    nums = []
    for t in tags:
        m = _SNAP_TAG_RE.match(t)
        if m:
            nums.append(int(m.group(1)))
    n = (max(nums) + 1) if nums else 1
    return f"snap-{n:03d}"


def diff_head(project_dir: Path) -> str:
    rc, out = run_git(project_dir, ["diff", "HEAD"], check=False)
    return out if rc == 0 else ""
