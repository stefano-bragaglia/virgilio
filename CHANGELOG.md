# Changelog

All notable changes to VirgilIO are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-01

Initial stable release.

### Added

- `virgilio <folder>` CLI: watches a folder (immediate contents by default, `--recursive`
  for the full subtree), logging every event to `log.txt` inside the watched folder.
- `--interval SECONDS`/`-i` (default `1.0`), `--include-hidden` (dotfiles/symlinks,
  excluded by default), `--report-existing` (fire `FOUND` for the startup baseline
  instead of silent indexing).
- `Virgilio` base class with overridable hooks (`notify`, `notify_created`,
  `notify_modified`, `notify_deleted`, `notify_found`, `notify_error`) and an
  `EventType` enum (`CREATED`, `MODIFIED`, `DELETED`, `FOUND`, `ERROR`).
- `Virgilio.run()`/`Virgilio.stop()` for embedding the daemon in a larger
  application (e.g. on its own thread), independent of the CLI/signal-based
  lifecycle.
- `Virgilio.main(argv=None)` classmethod so a subclass can reuse the same CLI
  argument parsing with zero extra wiring (`MyVirgilio.main()`).
- Change detection: SHA-256 content hashing with a size-stability wait before
  hashing, so files are only inspected once they stop changing size between
  polls; independent per-file state so one large file never blocks detection
  of others in the same cycle.
- Hidden-file/symlink filtering, symlink-cycle protection, and resilience to
  permission errors during scanning and hashing (surfaced as `ERROR` events
  rather than crashing the daemon).
- `py.typed` marker (PEP 561) — the package ships inline type hints.

[1.0.0]: https://github.com/stefano-bragaglia/virgilio/releases/tag/v1.0.0
