"""Phase 7 tests: the command line (SPEC sections 9 and 12, D-041 to D-043).

Every CLI test of the project lives here. In-process tests call `run` / `main`;
subprocess tests start `python src/main.py` with cwd set to the repo root, and all
paths are built from this file's location, so the tests pass from any directory.
"""
import itertools
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.main import main as cli_main
from src.main import run

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src" / "main.py"
SAMPLES = ROOT / "samples"

HEADERS = ["== TOKENS ==", "== PARSE TREE ==", "== SYMBOL TABLES ==", "== ERRORS ==",
           "== THREE-ADDRESS CODE =="]
SECTION_FLAGS = {"--tokens": HEADERS[0], "--tree": HEADERS[1], "--symbols": HEADERS[2],
                 "--tac": HEADERS[4]}
ALL_FOUR = ["--tokens", "--tree", "--symbols", "--tac"]

VALID_PROGRAMS = [SAMPLES / "valid_program.sl", ROOT / "tests" / "valid" / "semantic_scopes.sl",
                  ROOT / "tests" / "valid" / "parser_precedence.sl"]
SYNTAX_DEMO = SAMPLES / "errors_lexical_syntax.sl"
SEMANTIC_DEMO = SAMPLES / "errors_semantic.sl"
SYNTAX_FILE = ROOT / "tests" / "invalid" / "syntax_multiple_errors.sl"
THREE_FILES = [VALID_PROGRAMS[0], SYNTAX_DEMO, SEMANTIC_DEMO]

needs_dot = pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz `dot` not installed")


def cli(*args):
    """Run `python src/main.py ARGS` from the repo root; return the CompletedProcess (text mode)."""
    command = [sys.executable, str(MAIN)] + [str(a) for a in args]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)


def headers_in(out):
    """The section header lines found in `out`, in print order."""
    return [line for line in out.splitlines() if line in HEADERS]


def run_cli(tmp_path, capsys, source, flags, png=None):
    """Write `source` to a temp file, call `run`, return (exit code, stdout, stderr)."""
    path = tmp_path / "prog.sl"
    path.write_text(source, encoding="utf-8")
    code = run(str(path), set(flags), png)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ------------------------------------------------ usage and file errors (exit code 2)

def assert_cli_exit_2(argv, capsys, stderr_part):
    """Run cli_main(argv); assert exit code 2, empty stdout, and a one-line message on stderr."""
    code = cli_main(argv)
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    err_lines = captured.err.splitlines()
    assert len(err_lines) == 1
    assert stderr_part in err_lines[0]


def test_cli_no_arguments_exits_2(capsys):
    assert_cli_exit_2([], capsys, "usage:")


def test_cli_missing_file_exits_2(capsys):
    assert_cli_exit_2(["does_not_exist.sl", "--tokens"], capsys, "cannot read 'does_not_exist.sl'")


def test_cli_unknown_flag_exits_2(capsys):
    assert_cli_exit_2([str(SAMPLES / "valid_all_tokens.sl"), "--unknown"], capsys, "usage:")


def test_cli_short_unknown_flag_exits_2(capsys):
    assert_cli_exit_2(["-x"], capsys, "usage:")


def test_cli_directory_path_exits_2(capsys):
    assert_cli_exit_2([str(SAMPLES), "--tokens"], capsys, f"cannot read '{SAMPLES}'")


def test_cli_invalid_utf8_file_exits_2(tmp_path, capsys):
    bad_file = tmp_path / "bad_utf8.sl"
    bad_file.write_bytes(b"int x = \xff\xfe;\n")
    assert_cli_exit_2([str(bad_file), "--tokens"], capsys, f"cannot read '{bad_file}'")


def test_cli_missing_file_is_still_exit_2(tmp_path):
    """Exit 2 stays reserved for usage and file errors."""
    assert run(str(tmp_path / "nope.sl"), {"--tree"}) == 2


def test_cli_tree_png_without_path_exits_2(capsys):
    assert_cli_exit_2([str(VALID_PROGRAMS[0]), "--tree-png"], capsys, "usage:")


def test_cli_tree_png_followed_by_a_flag_exits_2(capsys):
    """`--tree-png --tokens`: the next argument is a flag, so the PATH is missing."""
    assert_cli_exit_2([str(VALID_PROGRAMS[0]), "--tree-png", "--tokens"], capsys, "usage:")


def test_cli_two_source_files_exit_2(capsys):
    assert_cli_exit_2([str(VALID_PROGRAMS[0]), str(VALID_PROGRAMS[1])], capsys, "usage:")


# ------------------------------------------- subprocess tests: 3 valid, 3 invalid programs

@pytest.mark.parametrize("path", VALID_PROGRAMS, ids=lambda p: p.name)
def test_valid_program_exits_0_with_every_section(path):
    result = cli(path)
    assert result.returncode == 0 and result.stderr == ""
    assert headers_in(result.stdout) == HEADERS
    assert "== ERRORS ==\n(none)\n" in result.stdout
    assert "(skipped" not in result.stdout
    tac = result.stdout.split("== THREE-ADDRESS CODE ==\n")[1]
    assert "func " in tac and tac.rstrip().endswith("endfunc")


def test_valid_program_sample_key_lines():
    out = cli(VALID_PROGRAMS[0]).stdout
    assert "Scope 1 (function square)" in out and "Scope 0 (global)" in out
    assert "globals:" in out and "func main:" in out


def test_lexical_syntax_demo_exits_1_and_skips_later_stages():
    result = cli(SYNTAX_DEMO)
    out = result.stdout
    assert result.returncode == 1 and result.stderr == ""
    assert headers_in(out) == HEADERS
    assert "[Lexical Error] Line 3," in out and "[Syntax Error] Line 4," in out
    assert "[Syntax Error] Line 6, Col 5: Expected ';' but found 'if'" in out
    assert "[Syntax Error] Line 6, Col 15: Expected ')' but found '{'" in out
    assert "[Semantic Error]" not in out
    assert "== SYMBOL TABLES ==\n(skipped: lexical or syntax errors)\n" in out
    assert "== THREE-ADDRESS CODE ==\n(skipped: compilation errors)" in out
    assert "Program\n  FunctionDecl int main" in out     # the partial tree is still printed


def test_semantic_demo_exits_1_prints_tables_and_skips_tac():
    result = cli(SEMANTIC_DEMO)
    out = result.stdout
    assert result.returncode == 1 and result.stderr == ""
    assert headers_in(out) == HEADERS
    assert "[Semantic Error] Line 9, Col 5: Cannot assign float to int variable 'a'" in out
    assert "Undeclared identifier 'ghost'" in out and "Cannot assign to constant 'LIMIT'" in out
    assert "Function 'square' expects 1 argument, found 2" in out
    assert "Scope 1 (function square)" in out
    assert "== THREE-ADDRESS CODE ==\n(skipped: compilation errors)" in out


def test_invalid_corpus_file_syntax_errors():
    result = cli(SYNTAX_FILE)
    assert result.returncode == 1 and result.stderr == ""
    assert "[Syntax Error] Line 6, Col 9: Expected expression but found ';'" in result.stdout
    assert "(skipped: lexical or syntax errors)" in result.stdout


def test_sections_are_separated_by_exactly_one_blank_line():
    lines = cli(VALID_PROGRAMS[0]).stdout.split("\n")
    for index, line in enumerate(lines):
        if line in HEADERS and index > 0:
            assert lines[index - 1] == "" and lines[index - 2] != ""


# --------------------------------------------------------------- flag semantics

@pytest.mark.parametrize("path", THREE_FILES, ids=lambda p: p.name)
def test_flag_order_does_not_matter(path):
    first = cli(path, "--tokens", "--tree", "--symbols")
    second = cli("--symbols", path, "--tree", "--tokens")
    third = cli("--tree", "--symbols", "--tokens", path)
    assert first.stdout == second.stdout == third.stdout
    assert first.returncode == second.returncode == third.returncode


@pytest.mark.parametrize("path", THREE_FILES, ids=lambda p: p.name)
def test_no_flag_equals_all_equals_the_four_flags(path):
    bare = cli(path)
    all_flag = cli(path, "--all")
    four = cli(path, *ALL_FOUR)
    reversed_four = cli(*reversed(ALL_FOUR), path)
    assert bare.stdout == all_flag.stdout == four.stdout == reversed_four.stdout
    assert bare.returncode == all_flag.returncode == four.returncode


SUBSETS = [c for n in range(1, 5) for c in itertools.combinations(ALL_FOUR, n)]


@pytest.mark.parametrize("path", THREE_FILES, ids=lambda p: p.name)
@pytest.mark.parametrize("flags", SUBSETS, ids=lambda c: "+".join(f[2:] for f in c))
def test_flag_combination_prints_exactly_those_sections(path, flags, capsys):
    """Requested sections plus ERRORS, in the fixed order; the exit code ignores the flags."""
    code = run(str(path), set(flags))
    out = capsys.readouterr().out
    wanted = {SECTION_FLAGS[f] for f in flags} | {"== ERRORS =="}
    assert headers_in(out) == [h for h in HEADERS if h in wanted]
    assert code == (0 if path == VALID_PROGRAMS[0] else 1)


def test_tokens_alone_still_runs_semantic_stage(tmp_path, capsys):
    """Updated pin (was: --tokens alone does not run the semantic stage; SPEC section 9 now applies)."""
    code, out, _ = run_cli(tmp_path, capsys, TYPE_ERROR, ["--tokens"])
    assert code == 1 and SPEC_ERROR_LINE in out
    assert "== SYMBOL TABLES ==" not in out and "== PARSE TREE ==" not in out


def test_tac_alone_prints_errors_and_tac_only(tmp_path, capsys):
    code, out, _ = run_cli(tmp_path, capsys, GOOD, ["--tac"])
    assert code == 0
    assert headers_in(out) == ["== ERRORS ==", "== THREE-ADDRESS CODE =="]


def test_errors_section_is_always_printed_even_when_empty(tmp_path, capsys):
    code, out, _ = run_cli(tmp_path, capsys, GOOD, ["--tokens"])
    assert code == 0 and out.rstrip().endswith("== ERRORS ==\n(none)")


# ----------------------------------------------------------------- --tree-png

@needs_dot
@pytest.mark.parametrize("flags", [[], ["--tokens"], ["--tree", "--tac"]])
@pytest.mark.parametrize("path", THREE_FILES, ids=lambda p: p.name)
def test_tree_png_writes_file_and_keeps_stdout_identical(tmp_path, path, flags):
    png = tmp_path / "tree.png"
    plain = cli(path, *flags)
    with_png = cli(path, *flags, "--tree-png", png)
    assert with_png.stdout == plain.stdout
    assert with_png.returncode == plain.returncode
    assert with_png.stderr == f"wrote {png}\n"
    assert png.read_bytes()[:4] == b"\x89PNG"


def test_tree_png_failure_still_prints_all_sections(tmp_path):
    """A bad PATH (or a missing dot) is a graphviz problem: sections print, one stderr line, exit 2."""
    result = cli(VALID_PROGRAMS[0], "--tree-png", tmp_path / "no_such_dir" / "t.png")
    assert result.returncode == 2
    assert headers_in(result.stdout) == HEADERS
    assert result.stderr.count("\n") == 1 and result.stderr.startswith("error: ")


# ------------------------------------------------ in-process: --tree, --tree-png, --symbols

def test_cli_tree_prints_section(tmp_path, capsys):
    code, out, _ = run_cli(tmp_path, capsys, "int main() { return 1 + 2 * 3; }\n", ["--tokens", "--tree"])
    assert code == 0
    assert "== PARSE TREE ==" in out
    assert "BinaryOp +" in out and "BinaryOp *" in out
    assert out.index("== TOKENS ==") < out.index("== PARSE TREE ==") < out.index("== ERRORS ==")


def test_cli_tree_with_syntax_error_exit_code(tmp_path, capsys):
    code, out, _ = run_cli(tmp_path, capsys, "int main() { int x = 1 }\n", ["--tree"])
    assert code == 1
    assert "[Syntax Error] Line 1" in out


@needs_dot
def test_cli_tree_png_writes_file(tmp_path, capsys):
    png = tmp_path / "out.png"
    code, out, err = run_cli(tmp_path, capsys, "int main() { return 1; }\n", ["--tree-png"], str(png))
    assert code == 0 and png.exists() and png.stat().st_size > 0
    assert err == f"wrote {png}\n" and str(png) not in out


def test_cli_tree_png_missing_dot_gives_clear_message(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("src.tree_export.shutil.which", lambda name: None)
    code, out, err = run_cli(tmp_path, capsys, "int main() { return 1; }\n", ["--tree-png"],
                             str(tmp_path / "o.png"))
    assert code == 2
    assert "dot" in err and "graphviz" in err.lower() and err.count("\n") == 1
    assert headers_in(out) == HEADERS


def test_cli_invalid_lexical_sample_has_no_follow_on_syntax_error(capsys):
    code = run(str(SAMPLES / "invalid_lexical.sl"), {"--tree"})
    out = capsys.readouterr().out
    assert code == 1
    assert "[Syntax Error]" not in out


TYPE_ERROR = "int main() {\n    int x = 2.5;\n    return x;\n}\n"
SYNTAX_PLUS_TYPE = "int main() {\n    int x = 2.5;\n    int y = 1\n    return x;\n}\n"
GOOD = "int main() {\n    int x = 2;\n    return x;\n}\n"
SPEC_ERROR_LINE = "[Semantic Error] Line 2, Col 5: Cannot assign float to int variable 'x'"


@pytest.mark.parametrize("flags", [["--tree"], ["--symbols"], ["--tree", "--symbols"]])
def test_cli_semantic_error_only(tmp_path, capsys, flags):
    """A type error shows under == ERRORS == and gives exit 1; --symbols still prints the tables."""
    code, out, _ = run_cli(tmp_path, capsys, TYPE_ERROR, flags)
    assert code == 1
    assert SPEC_ERROR_LINE in out.split("== ERRORS ==")[1]
    if "--symbols" in flags:
        assert "== SYMBOL TABLES ==" in out and "Scope 1 (function main)" in out
        assert out.index("== SYMBOL TABLES ==") < out.index("== ERRORS ==")


@needs_dot
def test_cli_semantic_error_with_tree_png(tmp_path, capsys):
    """--tree-png does not change the pipeline: the semantic error is still reported."""
    code, out, _ = run_cli(tmp_path, capsys, TYPE_ERROR, ["--tree-png"], str(tmp_path / "t.png"))
    assert code == 1 and SPEC_ERROR_LINE in out


@pytest.mark.parametrize("flags", [["--tree"], ["--symbols"]])
def test_cli_syntax_error_hides_type_error(tmp_path, capsys, flags):
    """Syntax error plus type error: only the syntax error is reported; --symbols says skipped."""
    code, out, _ = run_cli(tmp_path, capsys, SYNTAX_PLUS_TYPE, flags)
    assert code == 1
    errors_section = out.split("== ERRORS ==")[1]
    assert "[Syntax Error]" in errors_section and "[Semantic Error]" not in errors_section
    if "--symbols" in flags:
        symbols = out.split("== SYMBOL TABLES ==")[1].split("== ERRORS ==")[0]
        assert symbols.strip() == "(skipped: lexical or syntax errors)"


def test_cli_valid_file(tmp_path, capsys):
    """A valid file exits 0, prints the tables and `(none)` under errors."""
    code, out, _ = run_cli(tmp_path, capsys, GOOD, ["--symbols"])
    assert code == 0 and "Scope 0 (global)" in out and out.rstrip().endswith("(none)")


def test_cli_lexical_errors_only_skip_semantic_stage(tmp_path, capsys):
    """A file with ONLY a lexical error: the undeclared `ghost` is not reported, --symbols says skipped."""
    source = "int main() {\n    int y = ghost;\n    int x = 1 @;\n    return 0;\n}\n"
    code, out, _ = run_cli(tmp_path, capsys, source, ["--tree", "--symbols"])
    errors_part = out.split("== ERRORS ==")[1]
    assert "[Lexical Error]" in errors_part and "[Syntax Error]" not in errors_part
    assert "Semantic" not in out and "ghost" not in errors_part
    assert "(skipped: lexical or syntax errors)" in out and code == 1


def test_cli_symbols_after_nested_too_deeply(tmp_path, capsys):
    """900 unary minus signs: one `nested too deeply` error, and --symbols still prints without a crash."""
    source = "int main() {\n    return " + "-" * 900 + "1;\n}\n"
    code, out, err = run_cli(tmp_path, capsys, source, ["--symbols"])
    assert code == 1 and err == ""
    assert "== SYMBOL TABLES ==" in out and "Scope 0 (global)" in out
    assert out.count("Program is nested too deeply to analyze") == 1


# ------------------------------------------------ deep nesting (D-037, D-043)

DEEP_CHAIN = "int main() {\n    return " + "1 + " * 3000 + "1;\n}\n"
TREE_SKIPPED = "== PARSE TREE ==\n(skipped: nested too deeply to print)"


def test_cli_deep_chain_tree_is_skipped_but_other_sections_print(tmp_path, capsys):
    """3000-term chain: only the tree section is skipped; nothing on stderr; exit 1 (D-043)."""
    code, out, err = run_cli(tmp_path, capsys, DEEP_CHAIN, ["--tree"])
    assert code == 1 and err == ""
    assert TREE_SKIPPED in out
    assert headers_in(out) == ["== PARSE TREE ==", "== ERRORS =="]
    assert "== ERRORS ==\n(none)" in out


@needs_dot
def test_cli_deep_chain_tree_png_gives_one_line_error(tmp_path, capsys):
    """Same chain with --tree-png: sections print, one stderr line about the PNG, exit 1 (not 2)."""
    code, out, err = run_cli(tmp_path, capsys, DEEP_CHAIN, ["--tree-png"], str(tmp_path / "t.png"))
    assert code == 1
    assert err.count("\n") == 1 and err.startswith("error: ") and "too deeply" in err
    assert headers_in(out) == HEADERS and TREE_SKIPPED in out


def test_cli_3000_term_chain_with_tac_alone_succeeds(tmp_path, capsys):
    """3000-term chain with `--tac` alone succeeds (all stages loop down the left spine)."""
    code, out, err = run_cli(tmp_path, capsys, DEEP_CHAIN, ["--tac"])
    assert code == 0 and err == ""
    assert "== THREE-ADDRESS CODE ==" in out
    assert "  t1 = 1 + 1" in out
    assert "  t3000 = t2999 + 1" in out
    assert "  return t3000" in out


def test_cli_3000_term_chain_with_tree_and_tac(tmp_path, capsys):
    """`--tree --tac` on the chain: tree skipped, TAC still printed, exit 1, stderr empty."""
    code, out, err = run_cli(tmp_path, capsys, DEEP_CHAIN, ["--tree", "--tac"])
    assert code == 1 and err == ""
    assert TREE_SKIPPED in out
    assert "  t3000 = t2999 + 1" in out and "Traceback" not in out + err


def test_cli_900_unary_chain_with_tac_skips_tac_and_exits_1(tmp_path, capsys):
    """Right-nested 900 unary minus chain reports a Semantic error and skips TAC cleanly."""
    source = "int main() {\n    return " + "-" * 900 + "1;\n}\n"
    code, out, err = run_cli(tmp_path, capsys, source, ["--tac"])
    assert code == 1 and err == ""
    assert "Program is nested too deeply to analyze" in out
    tac_section = out.split("== THREE-ADDRESS CODE ==")[1]
    assert tac_section.strip() == "(skipped: compilation errors)"


# ------------------------------------------------------------ --tac integration

def test_cli_tac_prints_section_after_errors(tmp_path, capsys):
    """`--tac` prints `== THREE-ADDRESS CODE ==` after `== ERRORS ==` and exits 0 on valid input."""
    source = "int main() {\n    int x = 2 + 3;\n    return x;\n}\n"
    code, out, err = run_cli(tmp_path, capsys, source, ["--tokens", "--symbols", "--tac"])
    assert code == 0 and err == ""
    assert out.index("== TOKENS ==") < out.index("== SYMBOL TABLES ==")
    assert out.index("== SYMBOL TABLES ==") < out.index("== ERRORS ==")
    assert out.index("== ERRORS ==") < out.index("== THREE-ADDRESS CODE ==")
    tac_section = out.split("== THREE-ADDRESS CODE ==")[1].strip().splitlines()
    assert tac_section == [
        "func main:",
        "  t1 = 2 + 3",
        "  x = t1",
        "  return x",
        "endfunc",
    ]


@pytest.mark.parametrize(
    "bad_source,expected_error",
    [
        ("int main() {\n    int x = 1 @;\n    return x;\n}\n", "[Lexical Error]"),
        ("int main() {\n    int x = ;\n    return 0;\n}\n", "[Syntax Error]"),
        ("int main() {\n    int x = 2.5;\n    return x;\n}\n", "[Semantic Error]"),
    ],
)
def test_cli_tac_skipped_on_any_error(tmp_path, capsys, bad_source, expected_error):
    """Lexical, syntax, or semantic errors skip TAC and print one skip line."""
    code, out, err = run_cli(tmp_path, capsys, bad_source, ["--tac"])
    assert code == 1 and err == ""
    assert expected_error in out
    assert "== THREE-ADDRESS CODE ==" in out
    tac_section = out.split("== THREE-ADDRESS CODE ==")[1]
    assert tac_section.strip() == "(skipped: compilation errors)"
    assert "func main:" not in tac_section


def test_cli_tac_prints_none_when_no_instructions_emitted(tmp_path, capsys):
    """A valid file with only an uninitialized global emits zero TAC lines and prints `(none)`."""
    code, out, err = run_cli(tmp_path, capsys, "int g;\n", ["--tac"])
    assert code == 0 and err == ""
    tac_section = out.split("== THREE-ADDRESS CODE ==")[1]
    assert tac_section.strip() == "(none)"
