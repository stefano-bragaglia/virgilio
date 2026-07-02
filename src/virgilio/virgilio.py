import argparse
import os
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

from virgilio.events import EventType


class Virgilio:
    def __init__(self, folder: str | os.PathLike) -> None:
        self._folder = Path(folder)
        self._log_path = self._folder / "log.txt"
        self._log_path.write_text("")
        self._stop_event = threading.Event()

    def notify(self, event: EventType, path: str) -> None:
        pass

    def notify_created(self, path: str) -> None:
        pass

    def notify_modified(self, path: str) -> None:
        pass

    def notify_deleted(self, path: str) -> None:
        pass

    def notify_found(self, path: str) -> None:
        pass

    def notify_error(self, path: str) -> None:
        pass

    def _notify(self, event: EventType, path: str) -> None:
        self._log(event, path)
        self.notify(event, path)
        match event:
            case EventType.CREATED:
                self.notify_created(path)
            case EventType.MODIFIED:
                self.notify_modified(path)
            case EventType.DELETED:
                self.notify_deleted(path)
            case EventType.FOUND:
                self.notify_found(path)
            case EventType.ERROR:
                self.notify_error(path)
            case _:
                raise ValueError(f"Unexpected event type: {event!r} for {path!r}")

    def _log(self, event: EventType, path: str) -> None:
        timestamp = datetime.now().isoformat()
        with self._log_path.open("a") as f:
            f.write(f"{timestamp} {event.name} {path}\n")

    def run(
        self,
        *,
        recursive: bool = False,
        interval: float = 1.0,
        include_hidden: bool = False,
        report_existing: bool = False,
    ) -> None:
        from virgilio.detector import ChangeDetector

        self._stop_event.clear()
        self._install_signal_handlers()

        detector = ChangeDetector(self, self._folder)
        paths = self._watched_paths(recursive=recursive, include_hidden=include_hidden)
        detector.seed(paths, report_existing=report_existing)

        while not self._stop_event.wait(interval):
            paths = self._watched_paths(recursive=recursive, include_hidden=include_hidden)
            detector.poll(paths)

    def _watched_paths(self, *, recursive: bool, include_hidden: bool) -> list[Path]:
        from virgilio.scan import walk

        log_rel = self._log_path.relative_to(self._folder)
        return [
            path
            for path in walk(self._folder, recursive=recursive, include_hidden=include_hidden)
            if path != log_rel
        ]

    def stop(self) -> None:
        self._stop_event.set()

    def _install_signal_handlers(self) -> None:
        try:
            signal.signal(signal.SIGINT, self._handle_signal)
            signal.signal(signal.SIGTERM, self._handle_signal)
        except ValueError:
            pass

    def _handle_signal(self, signum: int, frame: object) -> None:
        self.stop()

    @classmethod
    def main(cls, argv: list[str] | None = None) -> None:
        parser = argparse.ArgumentParser(
            prog="virgilio",
            description=(
                "Watch a folder for file creations, modifications, and deletions. "
                "Polls the filesystem rather than relying on OS-native filesystem-event "
                "APIs, so behavior is consistent across macOS, Linux, and Windows. "
                "Every event is logged to log.txt inside the watched folder."
            ),
            epilog=(
                "Example: virgilio ./data --recursive --interval 0.5 "
                "--include-hidden --report-existing"
            ),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser.add_argument(
            "folder",
            help="path to the directory to watch; must already exist",
        )
        parser.add_argument(
            "--recursive",
            "-r",
            action="store_true",
            help="watch the full subtree instead of just the folder's immediate contents",
        )
        parser.add_argument(
            "--interval",
            "-i",
            type=float,
            default=1.0,
            metavar="SECONDS",
            help="poll interval in seconds; may be a float (e.g. 0.25)",
        )
        parser.add_argument(
            "--include-hidden",
            action="store_true",
            help=(
                "include hidden files/directories (dotfiles) and symlinks in the "
                "walk (excluded by default)"
            ),
        )
        parser.add_argument(
            "--report-existing",
            action="store_true",
            help=(
                "fire a FOUND event for every pre-existing file at startup, "
                "instead of silently indexing it"
            ),
        )
        args = parser.parse_args(argv)

        folder = Path(args.folder)
        if not folder.is_dir():
            print(f"error: {folder} is not a directory", file=sys.stderr)
            sys.exit(1)

        instance = cls(folder)
        instance.run(
            recursive=args.recursive,
            interval=args.interval,
            include_hidden=args.include_hidden,
            report_existing=args.report_existing,
        )
