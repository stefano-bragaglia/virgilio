from pathlib import Path

from virgilio.events import EventType
from virgilio.scan import hash_file
from virgilio.virgilio import Virgilio


class ChangeDetector:
    def __init__(self, virgilio: Virgilio, folder: Path) -> None:
        self._virgilio = virgilio
        self._folder = Path(folder)
        self._known: dict[Path, tuple[str, int]] = {}
        self._pending: dict[Path, int] = {}

    def seed(self, paths: list[Path], *, report_existing: bool = False) -> None:
        for path in paths:
            try:
                digest, size = hash_file(self._folder / path)
            except OSError:
                self._virgilio._notify(EventType.ERROR, str(path))
                continue
            self._known[path] = (digest, size)
            if report_existing:
                self._virgilio._notify(EventType.FOUND, str(path))

    def poll(self, paths: list[Path]) -> None:
        current = set(paths)
        for path in paths:
            self._poll_path(path)
        self._handle_missing(current)

    def _poll_path(self, path: Path) -> None:
        abs_path = self._folder / path
        try:
            current_size = abs_path.stat().st_size
        except OSError:
            return

        if path in self._known:
            self._poll_known_path(path, abs_path, current_size)
        else:
            self._poll_new_path(path, abs_path, current_size)

    def _poll_new_path(self, path: Path, abs_path: Path, current_size: int) -> None:
        if self._pending.get(path) != current_size:
            self._pending[path] = current_size
            return

        try:
            digest, size = hash_file(abs_path)
        except FileNotFoundError:
            del self._pending[path]
            self._virgilio._notify(EventType.CREATED, str(path))
            self._virgilio._notify(EventType.DELETED, str(path))
            return
        except OSError:
            self._virgilio._notify(EventType.ERROR, str(path))
            return

        self._known[path] = (digest, size)
        del self._pending[path]
        self._virgilio._notify(EventType.CREATED, str(path))

    def _poll_known_path(self, path: Path, abs_path: Path, current_size: int) -> None:
        old_hash, old_size = self._known[path]

        if current_size == old_size:
            self._compare_hash_directly(path, abs_path, old_hash)
            return

        if self._pending.get(path) != current_size:
            self._pending[path] = current_size
            return

        try:
            digest, size = hash_file(abs_path)
        except FileNotFoundError:
            del self._pending[path]
            self._virgilio._notify(EventType.MODIFIED, str(path))
            del self._known[path]
            self._virgilio._notify(EventType.DELETED, str(path))
            return
        except OSError:
            self._virgilio._notify(EventType.ERROR, str(path))
            return

        del self._pending[path]
        self._known[path] = (digest, size)
        if digest != old_hash:
            self._virgilio._notify(EventType.MODIFIED, str(path))

    def _compare_hash_directly(self, path: Path, abs_path: Path, old_hash: str) -> None:
        try:
            digest, size = hash_file(abs_path)
        except FileNotFoundError:
            del self._known[path]
            self._virgilio._notify(EventType.DELETED, str(path))
            return
        except OSError:
            self._virgilio._notify(EventType.ERROR, str(path))
            return

        self._known[path] = (digest, size)
        self._pending.pop(path, None)
        if digest != old_hash:
            self._virgilio._notify(EventType.MODIFIED, str(path))

    def _handle_missing(self, current: set[Path]) -> None:
        for path in [p for p in self._known if p not in current]:
            del self._known[path]
            self._virgilio._notify(EventType.DELETED, str(path))
        for path in [p for p in self._pending if p not in current]:
            del self._pending[path]
