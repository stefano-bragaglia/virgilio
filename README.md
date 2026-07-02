# virgilio

![virgilio logo](https://raw.githubusercontent.com/stefano-bragaglia/virgilio/main/logo.png)

[![CI](https://github.com/stefano-bragaglia/virgilio/actions/workflows/ci.yml/badge.svg)](https://github.com/stefano-bragaglia/virgilio/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/stefano-bragaglia/virgilio/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/stefano-bragaglia/virgilio/blob/main/pyproject.toml)
[![Typing: Typed](https://img.shields.io/badge/typing-py.typed-brightgreen.svg)](https://github.com/stefano-bragaglia/virgilio/blob/main/src/virgilio/py.typed)
[![GitHub tag](https://img.shields.io/github/v/tag/stefano-bragaglia/virgilio.svg)](https://github.com/stefano-bragaglia/virgilio/tags)
[![GitHub last commit](https://img.shields.io/github/last-commit/stefano-bragaglia/virgilio/main.svg)](https://github.com/stefano-bragaglia/virgilio/commits/main)

A folder-watching daemon that detects file creations, modifications, and deletions, and notifies a consumer via overridable hook methods. Pure polling — no `watchdog`, no OS-native filesystem-event API — so behavior is consistent across macOS, Linux, and Windows.

## CLI usage

```
virgilio <folder>
```

Watches only `<folder>`'s immediate contents by default, polling once per second, logging every event to `log.txt` inside `<folder>`.

Flags:

```
virgilio <folder> --recursive --interval 0.5 --include-hidden --report-existing
```

- `--recursive` / `-r` — watch the full subtree instead of just `<folder>`'s immediate contents.
- `--interval SECONDS` / `-i SECONDS` — poll interval in seconds (default `1.0`), may be a float (e.g. `0.25`).
- `--include-hidden` — include hidden files/directories (dotfiles) and symlinks in the walk (excluded by default).
- `--report-existing` — fire a `FOUND` event for every pre-existing file at startup, instead of silently indexing it.

If `<folder>` doesn't exist or isn't a directory, `virgilio` prints an error and exits with a non-zero status without starting.

## Library usage

Subclass `Virgilio` and override whichever hooks you care about, then reuse the same argument parsing via `.main()` — no separate CLI-loading mechanism needed:

```python
from virgilio import Virgilio, EventType

class MyVirgilio(Virgilio):
    def notify_created(self, path: str) -> None:
        print(f"new file: {path}")

    def notify(self, event: EventType, path: str) -> None:
        send_metric(event, path)

MyVirgilio.main()
```

`MyVirgilio.main()` parses `sys.argv` exactly like the plain `virgilio` CLI (`<folder> [--recursive] [--interval SECONDS] [--include-hidden] [--report-existing]`), constructs a `MyVirgilio`, and calls `.run(...)`. Both `notify` (unified) and the event-specific hook (`notify_created`, `notify_modified`, `notify_deleted`, `notify_found`, `notify_error`) fire for every event — override either, both, or neither.

To embed a `Virgilio` inside a larger application (e.g. running `.run()` on its own thread), call `.stop()` to shut it down programmatically instead of relying on SIGINT/SIGTERM:

```python
import threading

virgilio = MyVirgilio("/path/to/folder")
thread = threading.Thread(target=virgilio.run, kwargs={"recursive": True})
thread.start()
...
virgilio.stop()
thread.join()
```
