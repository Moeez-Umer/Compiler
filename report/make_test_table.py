"""Generate `report/assets/test_table.md` by running every `.sl` file in `tests/` (Phase 8).

Runs each program in `tests/valid`, `tests/invalid`, and `tests/golden` through the compiler
pipeline and writes a Markdown table with columns:
ID, Description, Input file, Expected, Actual, Pass/Fail.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.pipeline_helper import (  # noqa: E402
    check_tac, compile_source, expectation_problems, header_problems, parse_expects)

TESTS_DIR = ROOT / "tests"
OUT_PATH = ROOT / "report" / "assets" / "test_table.md"
FOLDERS = ("valid", "invalid", "golden")


def escape_cell(text: str) -> str:
    """Escape Markdown table pipes and newlines so every row stays on one line."""
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def humanize_stem(stem: str) -> str:
    """Turn a file stem like `semantic_float_to_int` into `semantic float to int`."""
    return stem.replace("_", " ")


def describe_file(path: Path, folder: str, source: str) -> str:
    """Build the Description column; for invalid files, include the first EXPECT message."""
    base = humanize_stem(path.stem)
    if folder == "invalid":
        expects = parse_expects(source)
        if expects:
            first = expects[0]
            extra = f" (+{len(expects) - 1} more)" if len(expects) > 1 else ""
            return f"{base}: {first.kind} L{first.line} — {first.text}{extra}"
    for line in source.splitlines()[1:4]:
        stripped = line.strip()
        if stripped.startswith("//") and not stripped.startswith("// EXPECT:"):
            comment = stripped.lstrip("/").strip().rstrip(".")
            if comment:
                return f"{base}: {comment}"
    if folder == "golden":
        return f"Golden TAC test ({base})"
    return f"Valid program ({base})"


def evaluate_program(path: Path, folder: str) -> tuple[str, str, str, bool]:
    """Run one `.sl` file and return (description, expected_str, actual_str, passed)."""
    source = path.read_bytes().decode("utf-8")
    desc = describe_file(path, folder, source)
    hdr_errs = header_problems(source, folder)
    result = compile_source(source)

    if folder == "valid":
        expected = "0 errors; well-formed TAC"
        tac_errs = check_tac(result.tac) if result.tac is not None else ["no TAC"]
        passed = not hdr_errs and not result.errors and result.tac is not None and not tac_errs
        if passed:
            actual = f"0 errors; TAC ({len(result.tac)} lines)"
        else:
            errs = [e.format() for e in result.errors] + hdr_errs + tac_errs
            actual = "; ".join(errs)
        return desc, expected, actual, passed

    if folder == "golden":
        tac_path = path.with_suffix(".tac")
        expected_tac = tac_path.read_text(encoding="utf-8").splitlines()
        expected = f"0 errors; matches {tac_path.name} ({len(expected_tac)} lines)"
        tac_errs = check_tac(result.tac) if result.tac is not None else ["no TAC"]
        passed = (
            not hdr_errs
            and not result.errors
            and result.tac == expected_tac
            and not tac_errs
        )
        if passed:
            actual = f"0 errors; exact match ({len(result.tac)} lines)"
        else:
            actual = "TAC mismatch or compile error"
        return desc, expected, actual, passed

    expects = parse_expects(source)
    expected = "; ".join(f"{e.kind} L{e.line}: {e.text}" for e in expects)
    problems = hdr_errs + expectation_problems(source, result)
    passed = not problems and bool(result.errors) and result.tac is None
    actual = "; ".join(f"{e.kind} L{e.line}: {e.message}" for e in result.errors) or "(no errors)"
    return desc, expected, actual, passed


def build_table() -> tuple[str, int, int]:
    """Run all test programs and return (markdown_text, total_count, passed_count)."""
    rows: list[str] = []
    total = 0
    passed_count = 0
    counts: dict[str, int] = {}

    for folder in FOLDERS:
        files = sorted((TESTS_DIR / folder).glob("*.sl"))
        counts[folder] = len(files)
        for path in files:
            total += 1
            test_id = f"T-{total:03d}"
            rel_path = f"tests/{folder}/{path.name}"
            desc, expected, actual, passed = evaluate_program(path, folder)
            if passed:
                passed_count += 1
            status = "PASS" if passed else "FAIL"
            rows.append(
                f"| {test_id} | {escape_cell(desc)} | `{rel_path}` | "
                f"{escape_cell(expected)} | {escape_cell(actual)} | {status} |"
            )

    header = [
        "# SmartLang Test Suite Execution Table",
        "",
        f"Total programs: **{total}** "
        f"(`tests/valid`: {counts['valid']}, `tests/invalid`: {counts['invalid']}, "
        f"`tests/golden`: {counts['golden']}). "
        f"Passed: **{passed_count}/{total}**.",
        "",
        "| ID | Description | Input file | Expected | Actual | Pass/Fail |",
        "|---|---|---|---|---|---|",
    ]
    return "\n".join(header + rows) + "\n", total, passed_count


def main() -> int:
    """Write `report/assets/test_table.md` and exit 0 if all test programs passed."""
    os.makedirs(OUT_PATH.parent, exist_ok=True)
    text, total, passed_count = build_table()
    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(ROOT)} ({total} programs, {passed_count} passed)")
    return 0 if total == passed_count else 1


if __name__ == "__main__":
    sys.exit(main())
