"""active.md 心跳线程。"""
from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import project as proj


_HB_INTERVAL = 60  # 秒


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_session_id(cli: str) -> str:
    ts = datetime.now().strftime("%H%M%S")[-6:]
    rnd = f"{random.randint(0, 999):03d}"
    return f"{cli}-{ts}-{rnd}"


def register_session(project_dir: Path, session_id: str, cli: str, pid: int, doing: str = "(刚启动)") -> None:
    now = _now()
    proj.upsert_active(project_dir, session_id, cli, pid, started=now, doing=doing, heartbeat=now)


def unregister_session(project_dir: Path, session_id: str) -> None:
    try:
        proj.remove_active(project_dir, session_id)
    except Exception:
        pass


def heartbeat(project_dir: Path, session_id: str, doing: str | None = None) -> None:
    entries = proj.read_active_entries(project_dir)
    me = next((e for e in entries if e.session_id == session_id), None)
    if me is None:
        return
    proj.upsert_active(
        project_dir,
        session_id=me.session_id,
        cli=me.cli,
        pid=me.pid,
        started=me.started,
        doing=doing if doing is not None else me.doing,
        heartbeat=_now(),
    )


class HeartbeatThread(threading.Thread):
    def __init__(self, project_dir: Path, session_id: str, interval: int = _HB_INTERVAL):
        super().__init__(daemon=True, name=f"cohub-hb-{session_id}")
        self.project_dir = project_dir
        self.session_id = session_id
        self.interval = interval
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                heartbeat(self.project_dir, self.session_id)
            except Exception:
                # 心跳失败不影响主流程
                pass
