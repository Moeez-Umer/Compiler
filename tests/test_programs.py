"""Run every program in tests/valid, tests/invalid and tests/golden through the full pipeline (SPEC section 13).

Headers are audited first: a file with a missing or malformed `// EXPECT:` header is listed by name
and the HEADER is fixed, never the compiler (D-044).
"""
from pathlib import Path

import pytest

from tests.pipeline_helper import (
    check_tac, compile_source, expectation_problems, header_problems)

TESTS = Path(__file__).parent
FOLDERS = ("valid", "invalid", "golden")


def program_files(folder: str) -> list[Path]:
    """Every .sl file of one test folder, sorted by name."""
    return sorted((TESTS / folder).glob("*.sl"))


def read(path: Path) -> str:
    """Read a test program as UTF-8, keeping line endings as they are."""
    return path.read_bytes().decode("utf-8")


def ids(paths: list[Path]) -> list[str]:
    """Readable pytest ids: the file names."""
    return [path.name for path in paths]


def test_every_program_has_a_correct_header():
    """Lists EVERY file whose header is missing or malformed, not just the first."""
    bad = []
    for folder in FOLDERS:
        for path in program_files(folder):
            bad += [f"{folder}/{path.name}: {p}" for p in header_problems(read(path), folder)]
    assert not bad, "files with a bad EXPECT header:\n" + "\n".join(bad)


def test_every_folder_has_programs():
    """A moved or emptied folder must not make the suite pass silently."""
    for folder in FOLDERS:
        assert program_files(folder), f"tests/{folder} has no .sl files"


@pytest.mark.parametrize("path", program_files("valid"), ids=ids(program_files("valid")))
def test_valid_program(path: Path):
    """Valid: zero errors, TAC produced and well-formed."""
    result = compile_source(read(path))
    assert [e.format() for e in result.errors] == []
    assert result.tac is not None
    assert check_tac(result.tac) == []


@pytest.mark.parametrize("path", program_files("invalid"), ids=ids(program_files("invalid")))
def test_invalid_program(path: Path):
    """Invalid: the reported errors match the EXPECT lines exactly; no TAC is produced."""
    source = read(path)
    result = compile_source(source)
    assert expectation_problems(source, result) == []
    assert result.errors, "an invalid program reported no error"
    assert result.tac is None


@pytest.mark.parametrize("path", program_files("golden"), ids=ids(program_files("golden")))
def test_golden_program(path: Path):
    """Golden: compiles without errors and the TAC equals the .tac file exactly."""
    result = compile_source(read(path))
    assert [e.format() for e in result.errors] == []
    expected = path.with_suffix(".tac").read_text(encoding="utf-8").splitlines()
    assert result.tac == expected
    assert check_tac(result.tac) == []
