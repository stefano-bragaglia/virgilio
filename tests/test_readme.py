import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"

HOOK_NAMES = (
    "notify_created",
    "notify_modified",
    "notify_deleted",
    "notify_found",
    "notify_error",
    "notify",
)


def _readme_text() -> str:
    return README_PATH.read_text()


def _python_code_blocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, re.DOTALL)


def test_readme_exists() -> None:
    assert README_PATH.is_file()


def test_readme_shows_plain_cli_usage() -> None:
    text = _readme_text()
    assert "virgilio <folder>" in text or re.search(r"virgilio\s+\S+", text)


def test_readme_mentions_all_four_flags() -> None:
    text = _readme_text()
    for flag in ("--recursive", "--interval", "--include-hidden", "--report-existing"):
        assert flag in text, f"README.md does not mention {flag}"


def test_readme_has_python_code_block_with_subclass_and_main_call() -> None:
    blocks = _python_code_blocks(_readme_text())
    assert blocks, "README.md has no fenced python code block"

    matching = [
        block
        for block in blocks
        if re.search(r"class\s+\w+\s*\(\s*Virgilio\s*\)", block) and ".main(" in block
    ]
    assert matching, "no python code block defines a subclass of Virgilio and calls .main()"


def test_readme_subclass_example_overrides_a_hook() -> None:
    blocks = _python_code_blocks(_readme_text())
    matching = [
        block
        for block in blocks
        if re.search(r"class\s+\w+\s*\(\s*Virgilio\s*\)", block) and ".main(" in block
    ]
    assert matching, "no python code block defines a subclass of Virgilio and calls .main()"

    assert any(
        any(f"def {hook}" in block for hook in HOOK_NAMES) for block in matching
    ), "subclass example does not override any notify hook"
