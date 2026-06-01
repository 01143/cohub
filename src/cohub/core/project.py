"""Read and write project state files under .cohub/."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

from . import paths


# -------- meta.yaml --------

def default_meta(*, project_name: str, goal: str, tags: list[str], language: list[str]) -> dict:
    return {
        "project_name": project_name,
        "tags": tags,
        "language": language,
        "goal": goal,
        "skills": {"force": []},
    }


def ensure_cohub_dir(project_dir: Path) -> Path:
    cohub = paths.project_cohub(project_dir)
    cohub.mkdir(parents=True, exist_ok=True)
    paths.reviews_dir(project_dir).mkdir(exist_ok=True)
    return cohub


def read_meta(project_dir: Path) -> dict:
    p = paths.meta_path(project_dir)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def write_meta(project_dir: Path, meta: dict) -> None:
    p = paths.meta_path(project_dir)
    p.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")


# -------- handoff / state --------

def read_handoff(project_dir: Path) -> str:
    p = paths.handoff_path(project_dir)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def write_handoff(project_dir: Path, content: str) -> None:
    paths.handoff_path(project_dir).write_text(content, encoding="utf-8")


def read_state(project_dir: Path) -> str:
    p = paths.state_path(project_dir)
    return p.read_text(encoding="utf-8") if p.exists() else ""


# -------- active.md (one session per line) --------

# Format: [<sid>] <cli> | PID <pid> | <started_at> | <current_work> | heartbeat <time>
_ENTRY_RE = re.compile(
    r"^\[(?P<sid>[^\]]+)\]\s*(?P<cli>\S+)\s*\|\s*PID\s*(?P<pid>\d+)\s*\|\s*(?P<started>[^|]+?)\s*\|\s*(?P<doing>.*?)\s*\|\s*heartbeat\s*(?P<hb>.+?)\s*$"
)

STALE_AFTER = timedelta(minutes=5)


@dataclass
class ActiveEntry:
    session_id: str
    cli: str
    pid: int
    started: str
    doing: str
    heartbeat: str
    raw: str

    def is_stale(self) -> bool:
        try:
            hb = datetime.fromisoformat(self.heartbeat)
            now = datetime.now(hb.tzinfo) if hb.tzinfo else datetime.now()
            return (now - hb) > STALE_AFTER
        except Exception:
            return False


def _format_entry(session_id: str, cli: str, pid: int, started: str, doing: str, heartbeat: str) -> str:
    return f"[{session_id}] {cli} | PID {pid} | {started} | {doing} | heartbeat {heartbeat}"


def _parse_active_lines(text: str) -> list[ActiveEntry]:
    entries: list[ActiveEntry] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _ENTRY_RE.match(line)
        if not m:
            continue
        entries.append(
            ActiveEntry(
                session_id=m.group("sid"),
                cli=m.group("cli"),
                pid=int(m.group("pid")),
                started=m.group("started").strip(),
                doing=m.group("doing").strip(),
                heartbeat=m.group("hb").strip(),
                raw=line,
            )
        )
    return entries


def read_active_entries(project_dir: Path) -> list[ActiveEntry]:
    p = paths.active_path(project_dir)
    if not p.exists():
        return []
    return _parse_active_lines(p.read_text(encoding="utf-8"))


def _write_active(project_dir: Path, entries: list[ActiveEntry]) -> None:
    p = paths.active_path(project_dir)
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    body = f"# Active Sessions ({now})\n\n"
    body += "\n".join(e.raw for e in entries)
    if entries:
        body += "\n"
    p.write_text(body, encoding="utf-8")


def upsert_active(project_dir: Path, session_id: str, cli: str, pid: int,
                  started: str, doing: str, heartbeat: str) -> None:
    entries = read_active_entries(project_dir)
    raw = _format_entry(session_id, cli, pid, started, doing, heartbeat)
    new_entry = ActiveEntry(session_id, cli, pid, started, doing, heartbeat, raw)
    entries = [e for e in entries if e.session_id != session_id]
    entries.append(new_entry)
    _write_active(project_dir, entries)


def remove_active(project_dir: Path, session_id: str) -> None:
    entries = read_active_entries(project_dir)
    entries = [e for e in entries if e.session_id != session_id]
    _write_active(project_dir, entries)


# -------- snapshots.md --------

@dataclass
class Snapshot:
    timestamp: str
    message: str
    tag: str


_SNAP_RE = re.compile(r"^-\s*\[(?P<ts>[^\]]+)\]\s*(?P<msg>.*?)\s*\(tag:\s*(?P<tag>[^)]+)\)\s*$")


def read_snapshots(project_dir: Path) -> list[Snapshot]:
    p = paths.snapshots_path(project_dir)
    if not p.exists():
        return []
    out: list[Snapshot] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = _SNAP_RE.match(line.strip())
        if m:
            out.append(Snapshot(m.group("ts"), m.group("msg").strip(), m.group("tag").strip()))
    return out


def append_snapshot(project_dir: Path, timestamp: str, message: str, tag: str) -> None:
    p = paths.snapshots_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = f"- [{timestamp}] {message} (tag: {tag})\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)
