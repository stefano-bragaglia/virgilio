import hashlib
import os
from pathlib import Path

_CHUNK_SIZE = 65536


def walk(folder: Path, *, recursive: bool = False, include_hidden: bool = False) -> list[Path]:
    folder = Path(folder)
    results: list[Path] = []
    ancestors = {folder.resolve()}
    _scan(folder, folder, recursive, include_hidden, results, ancestors)
    results.sort()
    return results


def _scan(
    root: Path,
    current: Path,
    recursive: bool,
    include_hidden: bool,
    results: list[Path],
    ancestors: set[Path],
) -> None:
    try:
        entries = list(os.scandir(current))
    except OSError:
        return

    for entry in entries:
        if not include_hidden and entry.name.startswith("."):
            continue
        _visit_entry(entry, root, current, recursive, include_hidden, results, ancestors)


def _visit_entry(
    entry: os.DirEntry,
    root: Path,
    current: Path,
    recursive: bool,
    include_hidden: bool,
    results: list[Path],
    ancestors: set[Path],
) -> None:
    kind = _entry_kind(entry)
    if kind is None:
        return
    is_symlink, is_dir = kind
    if is_symlink and not include_hidden:
        return

    path = current / entry.name
    if not is_dir:
        results.append(path.relative_to(root))
        return

    if not recursive:
        return
    real = path.resolve()
    if real in ancestors:
        return
    _scan(root, path, recursive, include_hidden, results, ancestors | {real})


def _entry_kind(entry: os.DirEntry) -> tuple[bool, bool] | None:
    try:
        return entry.is_symlink(), entry.is_dir(follow_symlinks=True)
    except OSError:
        return None


def hash_file(path: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK_SIZE):
            hasher.update(chunk)
            size += len(chunk)
    return hasher.hexdigest(), size
