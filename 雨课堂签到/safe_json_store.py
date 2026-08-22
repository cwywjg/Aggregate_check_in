"""Cross-process safe JSON persistence used by every server-side component.

The project only stores a few hundred records, so keeping the existing JSON
format is useful for compatibility.  This module supplies the properties that
plain ``open(..., "w")`` was missing:

* one lock shared by threads and processes;
* read/modify/write under the same lock;
* same-directory temporary files and atomic ``os.replace``;
* a backup of the last valid file;
* corruption is raised instead of silently being treated as an empty database.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar


T = TypeVar("T")


class JsonStoreError(RuntimeError):
    pass


class JsonStoreCorruptionError(JsonStoreError):
    pass


_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


class InterProcessFileLock:
    """Small dependency-free exclusive file lock for Windows and POSIX."""

    def __init__(self, path: Path, timeout: float = 15.0):
        self.path = path
        self.timeout = timeout
        self._handle = None
        self._thread_lock = _thread_lock(path)

    def __enter__(self):
        self._thread_lock.acquire()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = open(self.path, "a+b")
            self._handle.seek(0, os.SEEK_END)
            if self._handle.tell() == 0:
                self._handle.write(b"\0")
                self._handle.flush()
            deadline = time.monotonic() + self.timeout
            while True:
                try:
                    self._lock_once()
                    return self
                except (BlockingIOError, OSError):
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"timed out acquiring JSON lock: {self.path}")
                    time.sleep(0.05)
        except Exception:
            if self._handle:
                self._handle.close()
                self._handle = None
            self._thread_lock.release()
            raise

    def _lock_once(self):
        self._handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._handle:
                self._handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            if self._handle:
                self._handle.close()
                self._handle = None
            self._thread_lock.release()


class JsonStore(Generic[T]):
    def __init__(self, path: str | Path, default_factory: Callable[[], T]):
        self.path = Path(path).resolve()
        self.default_factory = default_factory
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.backup_path = self.path.with_suffix(self.path.suffix + ".bak")

    @contextmanager
    def locked(self):
        with InterProcessFileLock(self.lock_path):
            yield

    def _read_unlocked(self) -> T:
        if not self.path.exists():
            return self.default_factory()
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            corrupt_copy = self.path.with_suffix(self.path.suffix + f".corrupt-{stamp}")
            try:
                shutil.copy2(self.path, corrupt_copy)
            except OSError:
                pass
            raise JsonStoreCorruptionError(
                f"invalid JSON in {self.path}; preserved as {corrupt_copy.name}"
            ) from exc

    def read(self) -> T:
        with self.locked():
            return copy.deepcopy(self._read_unlocked())

    def _write_unlocked(self, data: T) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            if self.path.exists():
                try:
                    shutil.copy2(self.path, self.backup_path)
                except OSError:
                    pass
            # Windows may briefly deny replacement while Defender/indexers or
            # another process closes a handle.  The inter-process lock still
            # serializes writers; this retry only bridges that short OS window.
            replace_deadline = time.monotonic() + 3.0
            while True:
                try:
                    os.replace(temp_name, self.path)
                    break
                except PermissionError:
                    if time.monotonic() >= replace_deadline:
                        raise
                    time.sleep(0.05)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def write(self, data: T) -> None:
        with self.locked():
            self._write_unlocked(data)

    def update(self, mutator: Callable[[T], Any]) -> Any:
        """Run ``mutator`` and persist its in-place changes atomically.

        The callback may return any result.  The data is only written after the
        callback finishes successfully.
        """

        with self.locked():
            data = self._read_unlocked()
            result = mutator(data)
            self._write_unlocked(data)
            return result


def data_path(filename: str) -> Path:
    root = Path(os.environ.get("YKT_DATA_DIR") or Path(__file__).resolve().parent)
    return root.resolve() / filename


ACCOUNTS_STORE: JsonStore[list[dict[str, Any]]] = JsonStore(data_path("accounts.json"), list)
KEYS_STORE: JsonStore[dict[str, dict[str, Any]]] = JsonStore(data_path("keys.json"), dict)
HISTORY_STORE: JsonStore[list[dict[str, Any]]] = JsonStore(data_path("ai_history.json"), list)
PROBLEM_STATE_STORE: JsonStore[dict[str, dict[str, Any]]] = JsonStore(
    data_path("problem_states.json"), dict
)
AI_HEALTH_STORE: JsonStore[dict[str, Any]] = JsonStore(
    data_path("ai_health.json"), dict
)
