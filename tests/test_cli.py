import sys
from pathlib import Path

import pytest

from virgilio.virgilio import Virgilio


@pytest.fixture
def run_calls(monkeypatch):
    calls: list[tuple[Virgilio, dict]] = []

    def fake_run(self, **kwargs):
        calls.append((self, kwargs))

    monkeypatch.setattr(Virgilio, "run", fake_run)
    return calls


def test_nonexistent_folder_exits_nonzero_and_does_not_call_run(
    tmp_path: Path, capsys, run_calls
) -> None:
    missing = tmp_path / "does_not_exist"

    with pytest.raises(SystemExit) as exc_info:
        Virgilio.main([str(missing)])

    assert exc_info.value.code != 0
    assert capsys.readouterr().err.strip() != ""
    assert run_calls == []


def test_folder_is_a_file_exits_nonzero_and_does_not_call_run(
    tmp_path: Path, capsys, run_calls
) -> None:
    a_file = tmp_path / "file.txt"
    a_file.write_text("content")

    with pytest.raises(SystemExit) as exc_info:
        Virgilio.main([str(a_file)])

    assert exc_info.value.code != 0
    assert capsys.readouterr().err.strip() != ""
    assert run_calls == []


def test_valid_folder_no_flags_calls_run_with_defaults(tmp_path: Path, run_calls) -> None:
    Virgilio.main([str(tmp_path)])

    assert len(run_calls) == 1
    instance, kwargs = run_calls[0]
    assert isinstance(instance, Virgilio)
    assert kwargs == {
        "recursive": False,
        "interval": 1.0,
        "include_hidden": False,
        "report_existing": False,
    }


def test_all_flags_given_calls_run_with_those_values(tmp_path: Path, run_calls) -> None:
    Virgilio.main(
        [
            str(tmp_path),
            "--recursive",
            "--interval",
            "0.5",
            "--include-hidden",
            "--report-existing",
        ]
    )

    assert len(run_calls) == 1
    _instance, kwargs = run_calls[0]
    assert kwargs == {
        "recursive": True,
        "interval": 0.5,
        "include_hidden": True,
        "report_existing": True,
    }


def test_short_forms_match_long_forms(tmp_path: Path, run_calls) -> None:
    Virgilio.main([str(tmp_path), "-r", "-i", "0.5"])

    assert len(run_calls) == 1
    _instance, kwargs = run_calls[0]
    assert kwargs["recursive"] is True
    assert kwargs["interval"] == 0.5


def test_non_numeric_interval_exits_nonzero_via_argparse(tmp_path: Path, run_calls) -> None:
    with pytest.raises(SystemExit) as exc_info:
        Virgilio.main([str(tmp_path), "--interval", "not-a-number"])

    assert exc_info.value.code != 0
    assert run_calls == []


def test_subclass_main_constructs_subclass_instance(tmp_path: Path, run_calls) -> None:
    class MySubclass(Virgilio):
        pass

    MySubclass.main([str(tmp_path)])

    assert len(run_calls) == 1
    instance, _kwargs = run_calls[0]
    assert type(instance) is MySubclass


def test_module_main_uses_real_sys_argv(tmp_path: Path, run_calls, monkeypatch) -> None:
    from virgilio.main import main

    monkeypatch.setattr(sys, "argv", ["virgilio", str(tmp_path)])

    main()

    assert len(run_calls) == 1
    instance, kwargs = run_calls[0]
    assert isinstance(instance, Virgilio)
    assert kwargs == {
        "recursive": False,
        "interval": 1.0,
        "include_hidden": False,
        "report_existing": False,
    }
