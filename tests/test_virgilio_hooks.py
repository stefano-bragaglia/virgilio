from virgilio.events import EventType
from virgilio.virgilio import Virgilio


def _log_bytes(folder):
    log_path = folder / "log.txt"
    return log_path.read_bytes() if log_path.exists() else None


def test_virgilio_constructs_without_error(tmp_path):
    Virgilio(tmp_path)


def test_notify_returns_none_and_does_not_raise(tmp_path):
    virgilio = Virgilio(tmp_path)
    assert virgilio.notify(EventType.CREATED, "a.txt") is None


def test_notify_created_returns_none_and_does_not_raise(tmp_path):
    virgilio = Virgilio(tmp_path)
    assert virgilio.notify_created("a.txt") is None


def test_notify_modified_returns_none_and_does_not_raise(tmp_path):
    virgilio = Virgilio(tmp_path)
    assert virgilio.notify_modified("a.txt") is None


def test_notify_deleted_returns_none_and_does_not_raise(tmp_path):
    virgilio = Virgilio(tmp_path)
    assert virgilio.notify_deleted("a.txt") is None


def test_notify_found_returns_none_and_does_not_raise(tmp_path):
    virgilio = Virgilio(tmp_path)
    assert virgilio.notify_found("a.txt") is None


def test_notify_error_returns_none_and_does_not_raise(tmp_path):
    virgilio = Virgilio(tmp_path)
    assert virgilio.notify_error("a.txt") is None


def test_calling_hooks_directly_does_not_touch_log(tmp_path):
    virgilio = Virgilio(tmp_path)
    before = _log_bytes(tmp_path)

    virgilio.notify(EventType.CREATED, "a.txt")
    virgilio.notify_created("a.txt")
    virgilio.notify_modified("a.txt")
    virgilio.notify_deleted("a.txt")
    virgilio.notify_found("a.txt")
    virgilio.notify_error("a.txt")

    assert _log_bytes(tmp_path) == before


def test_subclass_overriding_one_hook_still_instantiates_and_others_stay_noop(tmp_path):
    class OnlyCreated(Virgilio):
        def notify_created(self, path: str) -> None:
            self.seen = path

    instance = OnlyCreated(tmp_path)
    assert instance.notify_modified("b.txt") is None
