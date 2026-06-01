"""路径相关 helper —— ~/.cohub 全局,.cohub/ 项目内。"""
from __future__ import annotations

from pathlib import Path


def home_cohub() -> Path:
    """~/.cohub 全局目录。"""
    return Path.home() / ".cohub"


def skills_dir() -> Path:
    return home_cohub() / "skills"


def adapters_dir() -> Path:
    return home_cohub() / "adapters"


def global_config_path() -> Path:
    return home_cohub() / "config.yaml"


def project_cohub(project_dir: Path) -> Path:
    return project_dir / ".cohub"


def handoff_path(project_dir: Path) -> Path:
    return project_cohub(project_dir) / "handoff.md"


def state_path(project_dir: Path) -> Path:
    return project_cohub(project_dir) / "state.md"


def active_path(project_dir: Path) -> Path:
    return project_cohub(project_dir) / "active.md"


def snapshots_path(project_dir: Path) -> Path:
    return project_cohub(project_dir) / "snapshots.md"


def meta_path(project_dir: Path) -> Path:
    return project_cohub(project_dir) / "meta.yaml"


def reviews_dir(project_dir: Path) -> Path:
    return project_cohub(project_dir) / "reviews"
