from pathlib import Path

from virgilio.detector import ChangeDetector
from virgilio.events import EventType
from virgilio.scan import hash_file
from virgilio.virgilio import Virgilio


class RecordingVirgilio(Virgilio):
    def __init__(self, folder):
        super().__init__(folder)
        self.events = []

    def notify(self, event, path):
        self.events.append((event, path))


def make_detector(tmp_path: Path) -> tuple[ChangeDetector, RecordingVirgilio]:
    virgilio = RecordingVirgilio(tmp_path)
    detector = ChangeDetector(virgilio, tmp_path)
    return detector, virgilio


def write(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return Path(name)


# --- dict-state-and-classification ---


def test_first_poll_of_new_path_fires_no_event_and_not_yet_known(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    rel = write(tmp_path, "a.txt", b"hello")

    detector.poll([rel])

    assert virgilio.events == []
    assert rel not in detector._known


def test_second_poll_same_size_fires_created_and_records_known_entry(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    rel = write(tmp_path, "a.txt", b"hello")

    detector.poll([rel])
    detector.poll([rel])

    assert virgilio.events == [(EventType.CREATED, str(rel))]
    expected_hash, expected_size = hash_file(tmp_path / rel)
    assert detector._known[rel] == (expected_hash, expected_size)
    assert rel not in detector._pending


def test_size_differs_between_first_and_second_poll_restarts_stabilization(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    rel = tmp_path / "a.txt"
    rel.write_bytes(b"hello")
    relp = Path("a.txt")

    detector.poll([relp])
    rel.write_bytes(b"a much longer piece of content now")
    detector.poll([relp])

    assert virgilio.events == []
    assert relp not in detector._known

    detector.poll([relp])
    assert virgilio.events == [(EventType.CREATED, str(relp))]


def test_known_path_unchanged_fires_no_event(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    relp = write(tmp_path, "a.txt", b"hello")
    detector.poll([relp])
    detector.poll([relp])
    virgilio.events.clear()

    detector.poll([relp])

    assert virgilio.events == []


def test_modify_content_same_size_fires_modified_without_stability_wait(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    relp = Path("a.txt")
    path.write_bytes(b"aaaaa")
    detector.poll([relp])
    detector.poll([relp])
    virgilio.events.clear()

    path.write_bytes(b"bbbbb")
    detector.poll([relp])

    assert virgilio.events == [(EventType.MODIFIED, str(relp))]
    expected_hash, expected_size = hash_file(path)
    assert detector._known[relp] == (expected_hash, expected_size)


def test_grow_size_then_stabilize_fires_modified_only_if_content_changed(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    relp = Path("a.txt")
    path.write_bytes(b"short")
    detector.poll([relp])
    detector.poll([relp])
    virgilio.events.clear()

    path.write_bytes(b"a much longer value")
    detector.poll([relp])
    assert virgilio.events == []
    assert relp in detector._pending

    detector.poll([relp])
    assert virgilio.events == [(EventType.MODIFIED, str(relp))]
    expected_hash, expected_size = hash_file(path)
    assert detector._known[relp] == (expected_hash, expected_size)
    assert relp not in detector._pending


def test_size_round_trip_same_content_updates_known_size_without_event(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    relp = Path("a.txt")
    original = b"same-content"
    path.write_bytes(original)
    detector.poll([relp])
    detector.poll([relp])
    virgilio.events.clear()

    path.write_bytes(original + b"-temp-suffix")
    detector.poll([relp])
    path.write_bytes(original)
    detector.poll([relp])

    assert virgilio.events == []
    expected_hash, expected_size = hash_file(path)
    assert detector._known[relp] == (expected_hash, expected_size)


def test_removing_known_file_fires_deleted_and_removes_entry(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    relp = Path("a.txt")
    path.write_bytes(b"hello")
    detector.poll([relp])
    detector.poll([relp])
    virgilio.events.clear()

    path.unlink()
    detector.poll([])

    assert virgilio.events == [(EventType.DELETED, str(relp))]
    assert relp not in detector._known


def test_pending_only_file_removed_before_stabilizing_fires_no_event(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    relp = Path("a.txt")
    path.write_bytes(b"hello")

    detector.poll([relp])
    assert relp in detector._pending

    path.unlink()
    detector.poll([])

    assert virgilio.events == []
    assert relp not in detector._pending
    assert relp not in detector._known


def test_repeated_identical_polls_after_stabilization_fire_no_further_events(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    relp = write(tmp_path, "a.txt", b"hello")
    detector.poll([relp])
    detector.poll([relp])
    virgilio.events.clear()

    for _ in range(5):
        detector.poll([relp])

    assert virgilio.events == []


def test_two_independent_paths_stabilize_and_change_independently(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    slow_path = tmp_path / "slow.txt"
    slow_rel = Path("slow.txt")
    slow_path.write_bytes(b"one")
    fast_rel = write(tmp_path, "fast.txt", b"two")

    # slow.txt: first poll, not yet stable
    detector.poll([slow_rel, fast_rel])
    assert virgilio.events == []

    # slow.txt changes size again (still not stable); fast.txt now stable -> CREATED
    slow_path.write_bytes(b"one-changed")
    detector.poll([slow_rel, fast_rel])
    assert virgilio.events == [(EventType.CREATED, str(fast_rel))]
    assert fast_rel in detector._known
    assert slow_rel not in detector._known

    virgilio.events.clear()
    # slow.txt now stable at its new size -> CREATED; fast.txt unchanged -> no event
    detector.poll([slow_rel, fast_rel])
    assert virgilio.events == [(EventType.CREATED, str(slow_rel))]
    assert slow_rel in detector._known


# --- startup-baseline ---


def test_seed_without_report_existing_populates_known_silently(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    a = write(tmp_path, "a.txt", b"aaa")
    b = write(tmp_path, "b.txt", b"bbbbb")

    detector.seed([a, b])

    assert virgilio.events == []
    assert detector._known[a] == hash_file(tmp_path / a)
    assert detector._known[b] == hash_file(tmp_path / b)


def test_seed_with_report_existing_fires_found_per_path(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    a = write(tmp_path, "a.txt", b"aaa")
    b = write(tmp_path, "b.txt", b"bbbbb")

    detector.seed([a, b], report_existing=True)

    assert virgilio.events == [(EventType.FOUND, str(a)), (EventType.FOUND, str(b))]
    assert detector._known[a] == hash_file(tmp_path / a)
    assert detector._known[b] == hash_file(tmp_path / b)


def test_poll_after_seed_unchanged_file_fires_no_event(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    a = write(tmp_path, "a.txt", b"aaa")
    detector.seed([a])
    virgilio.events.clear()

    detector.poll([a])

    assert virgilio.events == []


def test_poll_after_seed_same_size_modification_fires_modified_immediately(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    a = write(tmp_path, "a.txt", b"aaaaa")
    detector.seed([a])
    virgilio.events.clear()

    path.write_bytes(b"bbbbb")
    detector.poll([a])

    assert virgilio.events == [(EventType.MODIFIED, str(a))]
    assert detector._known[a] == hash_file(path)


def test_poll_after_seed_different_size_modification_stabilizes_then_fires_modified(tmp_path):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    a = write(tmp_path, "a.txt", b"short")
    detector.seed([a])
    virgilio.events.clear()

    path.write_bytes(b"a much longer value now")
    detector.poll([a])
    assert virgilio.events == []

    detector.poll([a])
    assert virgilio.events == [(EventType.MODIFIED, str(a))]
    assert detector._known[a] == hash_file(path)


def test_seed_empty_list_is_a_no_op(tmp_path):
    detector, virgilio = make_detector(tmp_path)

    detector.seed([])

    assert virgilio.events == []
    assert detector._known == {}


# --- hash-error-handling ---
# Assumes detector.py imports hash_file via `from virgilio.scan import hash_file`,
# so it can be monkeypatched at "virgilio.detector.hash_file".


def _raise_permission_error(path):
    raise PermissionError(f"no access: {path}")


def test_new_path_permission_error_fires_error_and_leaves_pending(tmp_path, monkeypatch):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    a = write(tmp_path, "a.txt", b"hello")
    detector.poll([a])

    monkeypatch.setattr("virgilio.detector.hash_file", _raise_permission_error)
    detector.poll([a])

    assert virgilio.events == [(EventType.ERROR, str(a))]
    assert a not in detector._known
    assert detector._pending[a] == path.stat().st_size


def test_new_path_permission_error_then_success_fires_created(tmp_path, monkeypatch):
    detector, virgilio = make_detector(tmp_path)
    a = write(tmp_path, "a.txt", b"hello")
    detector.poll([a])
    monkeypatch.setattr("virgilio.detector.hash_file", _raise_permission_error)
    detector.poll([a])
    virgilio.events.clear()

    monkeypatch.setattr("virgilio.detector.hash_file", hash_file)
    detector.poll([a])

    assert virgilio.events == [(EventType.CREATED, str(a))]
    assert a in detector._known
    assert a not in detector._pending


def test_known_path_same_size_permission_error_leaves_known_unchanged(tmp_path, monkeypatch):
    detector, virgilio = make_detector(tmp_path)
    a = write(tmp_path, "a.txt", b"hello")
    detector.poll([a])
    detector.poll([a])
    original_entry = detector._known[a]
    virgilio.events.clear()

    monkeypatch.setattr("virgilio.detector.hash_file", _raise_permission_error)
    detector.poll([a])

    assert virgilio.events == [(EventType.ERROR, str(a))]
    assert detector._known[a] == original_entry


def test_known_path_changed_size_stabilized_permission_error_leaves_pending(tmp_path, monkeypatch):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    a = write(tmp_path, "a.txt", b"hello")
    detector.poll([a])
    detector.poll([a])
    original_entry = detector._known[a]
    virgilio.events.clear()

    path.write_bytes(b"a much longer value")
    detector.poll([a])
    monkeypatch.setattr("virgilio.detector.hash_file", _raise_permission_error)
    detector.poll([a])

    assert virgilio.events == [(EventType.ERROR, str(a))]
    assert detector._known[a] == original_entry
    assert detector._pending[a] == path.stat().st_size


def test_seed_permission_error_on_one_path_still_seeds_others(tmp_path, monkeypatch):
    detector, virgilio = make_detector(tmp_path)
    a = write(tmp_path, "a.txt", b"aaa")
    b = write(tmp_path, "b.txt", b"bbbbb")

    def selective_raise(path):
        if path.name == "a.txt":
            raise PermissionError("no access")
        return hash_file(path)

    monkeypatch.setattr("virgilio.detector.hash_file", selective_raise)
    detector.seed([a, b])

    assert virgilio.events == [(EventType.ERROR, str(a))]
    assert a not in detector._known
    assert detector._known[b] == hash_file(tmp_path / b)


# --- delete-mid-hash-race ---


def _raise_file_not_found(path):
    raise FileNotFoundError(f"gone: {path}")


def test_new_path_deleted_mid_hash_fires_created_then_deleted(tmp_path, monkeypatch):
    detector, virgilio = make_detector(tmp_path)
    a = write(tmp_path, "a.txt", b"hello")
    detector.poll([a])

    monkeypatch.setattr("virgilio.detector.hash_file", _raise_file_not_found)
    detector.poll([a])

    assert virgilio.events == [(EventType.CREATED, str(a)), (EventType.DELETED, str(a))]
    assert a not in detector._known
    assert a not in detector._pending

    virgilio.events.clear()
    detector.poll([])
    assert virgilio.events == []


def test_known_path_changed_size_deleted_mid_hash_fires_modified_then_deleted(
    tmp_path, monkeypatch
):
    detector, virgilio = make_detector(tmp_path)
    path = tmp_path / "a.txt"
    a = write(tmp_path, "a.txt", b"hello")
    detector.poll([a])
    detector.poll([a])
    virgilio.events.clear()

    path.write_bytes(b"a much longer value")
    detector.poll([a])
    monkeypatch.setattr("virgilio.detector.hash_file", _raise_file_not_found)
    detector.poll([a])

    assert virgilio.events == [(EventType.MODIFIED, str(a)), (EventType.DELETED, str(a))]
    assert a not in detector._known
    assert a not in detector._pending

    virgilio.events.clear()
    detector.poll([])
    assert virgilio.events == []


def test_stat_race_on_new_path_skips_this_cycle_without_error(tmp_path, monkeypatch):
    detector, virgilio = make_detector(tmp_path)
    a = write(tmp_path, "a.txt", b"hello")

    import pathlib

    real_stat = pathlib.Path.stat

    def flaky_stat(self, *args, **kwargs):
        if self.name == "a.txt":
            raise OSError("vanished between walk() and stat()")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "stat", flaky_stat)
    detector.poll([a])

    assert virgilio.events == []
    assert a not in detector._known
    assert a not in detector._pending

    monkeypatch.undo()
    detector.poll([a])
    detector.poll([a])
    assert virgilio.events == [(EventType.CREATED, str(a))]


def test_known_path_unchanged_size_deleted_mid_hash_fires_deleted_only(tmp_path, monkeypatch):
    detector, virgilio = make_detector(tmp_path)
    a = write(tmp_path, "a.txt", b"hello")
    detector.poll([a])
    detector.poll([a])
    virgilio.events.clear()

    monkeypatch.setattr("virgilio.detector.hash_file", _raise_file_not_found)
    detector.poll([a])

    assert virgilio.events == [(EventType.DELETED, str(a))]
    assert a not in detector._known
    assert a not in detector._pending

    virgilio.events.clear()
    detector.poll([])
    assert virgilio.events == []
