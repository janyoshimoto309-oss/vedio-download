from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from config import DOWNLOADS_DIR, FILE_TTL_SECONDS, MAX_CONCURRENT_DOWNLOADS


@dataclass
class TaskRecord:
    task_id: str
    path: Path
    filename: str
    expires_at: float


_lock = threading.Lock()
_tasks: dict[str, TaskRecord] = {}
_active_downloads = 0


def acquire_slot() -> bool:
    global _active_downloads
    with _lock:
        if _active_downloads >= MAX_CONCURRENT_DOWNLOADS:
            return False
        _active_downloads += 1
        return True


def release_slot() -> None:
    global _active_downloads
    with _lock:
        _active_downloads = max(0, _active_downloads - 1)


def register_file(path: Path, filename: str, ttl: int = FILE_TTL_SECONDS) -> TaskRecord:
    cleanup_expired()
    task_id = uuid.uuid4().hex
    rec = TaskRecord(
        task_id=task_id,
        path=path,
        filename=filename,
        expires_at=time.time() + ttl,
    )
    with _lock:
        _tasks[task_id] = rec
    return rec


def get_task(task_id: str) -> TaskRecord | None:
    cleanup_expired()
    with _lock:
        rec = _tasks.get(task_id)
        if rec is None:
            return None
        if rec.expires_at < time.time():
            _tasks.pop(task_id, None)
            return None
        return rec


def cleanup_expired() -> None:
    now = time.time()
    with _lock:
        expired = [k for k, v in _tasks.items() if v.expires_at < now]
        for k in expired:
            rec = _tasks.pop(k)
            _remove_task_dir(rec.path)

    if DOWNLOADS_DIR.exists():
        for child in DOWNLOADS_DIR.iterdir():
            if not child.is_dir():
                continue
            try:
                mtime = child.stat().st_mtime
            except OSError:
                continue
            if now - mtime > FILE_TTL_SECONDS:
                _rm_tree(child)


def _remove_task_dir(file_path: Path) -> None:
    parent = file_path.parent
    if parent == DOWNLOADS_DIR:
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass
        return
    if DOWNLOADS_DIR in parent.parents or parent == DOWNLOADS_DIR:
        _rm_tree(parent)


def _rm_tree(path: Path) -> None:
    import shutil

    try:
        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass
