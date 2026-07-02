# observer

![observer logo](https://raw.githubusercontent.com/stefano-bragaglia/observer/main/logo.png)

[![CI](https://github.com/stefano-bragaglia/observer/actions/workflows/ci.yml/badge.svg)](https://github.com/stefano-bragaglia/observer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/stefano-bragaglia/observer/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/stefano-bragaglia/observer/blob/main/pyproject.toml)
[![Typing: Typed](https://img.shields.io/badge/typing-py.typed-brightgreen.svg)](https://github.com/stefano-bragaglia/observer/blob/main/src/observer/py.typed)
[![GitHub tag](https://img.shields.io/github/v/tag/stefano-bragaglia/observer.svg)](https://github.com/stefano-bragaglia/observer/tags)
[![GitHub last commit](https://img.shields.io/github/last-commit/stefano-bragaglia/observer/main.svg)](https://github.com/stefano-bragaglia/observer/commits/main)

A folder-watching daemon that detects file creations, modifications, and deletions, and notifies a consumer via overridable hook methods. Pure polling — no `watchdog`, no OS-native filesystem-event API — so behavior is consistent across macOS, Linux, and Windows.

## CLI usage

```
observer <folder>
```

Watches only `<folder>`'s immediate contents by default, polling once per second, logging every event to `log.txt` inside `<folder>`.

Flags:

```
observer <folder> --recursive --interval 0.5 --include-hidden --report-existing
```

- `--recursive` / `-r` — watch the full subtree instead of just `<folder>`'s immediate contents.
- `--interval SECONDS` / `-i SECONDS` — poll interval in seconds (default `1.0`), may be a float (e.g. `0.25`).
- `--include-hidden` — include hidden files/directories (dotfiles) and symlinks in the walk (excluded by default).
- `--report-existing` — fire a `FOUND` event for every pre-existing file at startup, instead of silently indexing it.

If `<folder>` doesn't exist or isn't a directory, `observer` prints an error and exits with a non-zero status without starting.

## Library usage

Subclass `Observer` and override whichever hooks you care about, then reuse the same argument parsing via `.main()` — no separate CLI-loading mechanism needed:

```python
from observer import Observer, EventType

class MyObserver(Observer):
    def notify_created(self, path: str) -> None:
        print(f"new file: {path}")

    def notify(self, event: EventType, path: str) -> None:
        send_metric(event, path)

MyObserver.main()
```

`MyObserver.main()` parses `sys.argv` exactly like the plain `observer` CLI (`<folder> [--recursive] [--interval SECONDS] [--include-hidden] [--report-existing]`), constructs a `MyObserver`, and calls `.run(...)`. Both `notify` (unified) and the event-specific hook (`notify_created`, `notify_modified`, `notify_deleted`, `notify_found`, `notify_error`) fire for every event — override either, both, or neither.

To embed an `Observer` inside a larger application (e.g. running `.run()` on its own thread), call `.stop()` to shut it down programmatically instead of relying on SIGINT/SIGTERM:

```python
import threading

observer = MyObserver("/path/to/folder")
thread = threading.Thread(target=observer.run, kwargs={"recursive": True})
thread.start()
...
observer.stop()
thread.join()
```
