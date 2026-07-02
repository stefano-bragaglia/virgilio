import hashlib
import os
from pathlib import Path

import pytest

from virgilio.scan import hash_file, walk


def test_walk_empty_dir_returns_empty_list(tmp_path: Path) -> None:
    assert walk(tmp_path) == []


def test_walk_returns_only_direct_files_sorted(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "c.txt").write_text("c")

    assert walk(tmp_path) == [Path("a.txt"), Path("b.txt"), Path("c.txt")]


def test_walk_flat_ignores_subdirectory_contents_and_subdirectories_themselves(
    tmp_path: Path,
) -> None:
    (tmp_path / "top.txt").write_text("top")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested")

    result = walk(tmp_path)

    assert result == [Path("top.txt")]
    assert Path("sub") not in result
    assert Path("sub/nested.txt") not in result


def test_walk_dir_with_only_subdirectories_returns_empty_list(tmp_path: Path) -> None:
    (tmp_path / "sub1").mkdir()
    (tmp_path / "sub2").mkdir()

    assert walk(tmp_path) == []


def test_walk_reflects_new_file_added_between_calls(tmp_path: Path) -> None:
    (tmp_path / "existing.txt").write_text("existing")

    first = walk(tmp_path)
    (tmp_path / "new.txt").write_text("new")
    second = walk(tmp_path)

    assert first == [Path("existing.txt")]
    assert second == [Path("existing.txt"), Path("new.txt")]


def test_walk_recursive_empty_dir_returns_empty_list(tmp_path: Path) -> None:
    assert walk(tmp_path, recursive=True) == []


def test_walk_recursive_deeply_nested_empty_subdirectories_returns_empty_list(
    tmp_path: Path,
) -> None:
    (tmp_path / "sub" / "deeper").mkdir(parents=True)

    assert walk(tmp_path, recursive=True) == []


def test_walk_recursive_returns_files_at_every_depth_sorted_relative_to_folder(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_text("a")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("b")
    deeper = sub / "deeper"
    deeper.mkdir()
    (deeper / "c.txt").write_text("c")

    result = walk(tmp_path, recursive=True)

    assert result == [Path("a.txt"), Path("sub/b.txt"), Path("sub/deeper/c.txt")]


def test_walk_recursive_picks_up_subdirectory_created_after_initial_call(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_text("a")

    first = walk(tmp_path, recursive=True)
    newsub = tmp_path / "newsub"
    newsub.mkdir()
    (newsub / "newfile.txt").write_text("new")
    second = walk(tmp_path, recursive=True)

    assert first == [Path("a.txt")]
    assert Path("newsub/newfile.txt") in second


def test_walk_flat_and_recursive_differ_on_tree_with_nested_files(tmp_path: Path) -> None:
    (tmp_path / "top.txt").write_text("top")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested")

    flat = walk(tmp_path, recursive=False)
    recursive = walk(tmp_path, recursive=True)

    assert flat == [Path("top.txt")]
    assert recursive == [Path("sub/nested.txt"), Path("top.txt")]
    assert flat != recursive


@pytest.mark.parametrize("recursive", [False, True])
def test_walk_excludes_dotfile_by_default(tmp_path: Path, recursive: bool) -> None:
    (tmp_path / "visible.txt").write_text("v")
    (tmp_path / ".hidden").write_text("h")

    result = walk(tmp_path, recursive=recursive)

    assert Path(".hidden") not in result
    assert all(not any(part.startswith(".") for part in p.parts) for p in result)


def test_walk_include_hidden_returns_dotfile(tmp_path: Path) -> None:
    (tmp_path / ".hidden").write_text("h")

    assert Path(".hidden") in walk(tmp_path, include_hidden=True)


def test_walk_excludes_dot_directory_contents_by_default(tmp_path: Path) -> None:
    dot_dir = tmp_path / ".config"
    dot_dir.mkdir()
    (dot_dir / "settings.txt").write_text("s")

    result = walk(tmp_path, recursive=True)

    assert result == []


def test_walk_include_hidden_descends_into_dot_directory(tmp_path: Path) -> None:
    dot_dir = tmp_path / ".config"
    dot_dir.mkdir()
    (dot_dir / "settings.txt").write_text("s")

    result = walk(tmp_path, recursive=True, include_hidden=True)

    assert Path(".config/settings.txt") in result


def test_walk_excludes_symlinked_file_by_default(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("content")
    os.symlink(target, tmp_path / "link.txt")

    result = walk(tmp_path)

    assert Path("link.txt") not in result
    assert result == [Path("target.txt")]


def test_walk_excludes_symlinked_directory_by_default(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "inside.txt").write_text("inside")
    os.symlink(real_dir, tmp_path / "link_dir", target_is_directory=True)

    result = walk(tmp_path, recursive=True)

    assert Path("link_dir") not in result
    assert not any(p.parts[0] == "link_dir" for p in result)
    assert result == [Path("real/inside.txt")]


def test_walk_include_hidden_follows_symlinked_directory_recursive(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "inside.txt").write_text("inside")
    os.symlink(real_dir, tmp_path / "link_dir", target_is_directory=True)

    result = walk(tmp_path, recursive=True, include_hidden=True)

    assert Path("link_dir/inside.txt") in result


def test_walk_symlink_cycle_does_not_hang_or_duplicate(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a")
    os.symlink(tmp_path, tmp_path / "loop", target_is_directory=True)

    result = walk(tmp_path, recursive=True, include_hidden=True)

    assert result.count(Path("a.txt")) == 1


def test_walk_broken_symlink_does_not_raise(tmp_path: Path) -> None:
    os.symlink(tmp_path / "does_not_exist.txt", tmp_path / "broken_link")

    walk(tmp_path, include_hidden=True)


def test_hash_file_known_content_returns_expected_digest_and_size(tmp_path: Path) -> None:
    content = b"the quick brown fox jumps over the lazy dog"
    path = tmp_path / "known.txt"
    path.write_bytes(content)

    digest, size = hash_file(path)

    assert digest == hashlib.sha256(content).hexdigest()
    assert size == len(content)


def test_hash_file_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_bytes(b"")

    digest, size = hash_file(path)

    assert digest == hashlib.sha256(b"").hexdigest()
    assert size == 0


def test_hash_file_large_file_spanning_multiple_chunks(tmp_path: Path) -> None:
    content = (b"0123456789" * 1024) * 512  # ~5MB, spans many chunks regardless of chunk size
    path = tmp_path / "large.bin"
    path.write_bytes(content)

    digest, size = hash_file(path)

    assert digest == hashlib.sha256(content).hexdigest()
    assert size == len(content)


def test_hash_file_nonexistent_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        hash_file(tmp_path / "does_not_exist.txt")


def test_walk_skips_unreadable_directory_during_scan(tmp_path: Path) -> None:
    (tmp_path / "visible.txt").write_text("v")
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "secret.txt").write_text("s")
    locked.chmod(0o000)

    try:
        result = walk(tmp_path, recursive=True)
    finally:
        locked.chmod(0o755)

    assert result == [Path("visible.txt")]


def test_walk_skips_entry_when_stat_raises_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "visible.txt").write_text("v")

    class _BrokenEntry:
        name = "broken"

        def is_symlink(self) -> bool:
            raise OSError("stat failed")

        def is_dir(self, *, follow_symlinks: bool = True) -> bool:
            raise OSError("stat failed")

    real_scandir = os.scandir

    def fake_scandir(path):
        entries = list(real_scandir(path))
        if Path(path) == tmp_path:
            entries.append(_BrokenEntry())
        return entries

    monkeypatch.setattr(os, "scandir", fake_scandir)

    result = walk(tmp_path)

    assert result == [Path("visible.txt")]
