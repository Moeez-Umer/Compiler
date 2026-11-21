"""Phase 6 tests: Three-address code generator (SPEC section 11, interfaces.md: tacgen.py)."""
from pathlib import Path

import pytest

from src.errors import ErrorCollector
from src.lexer import tokenize
from src.main import run
from src.parser import parse
from src.semantic import analyze
from src.tacgen import generate

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "tests" / "golden"
VALID_DIR = ROOT / "tests" / "valid"


def compile_to_tac(source: str) -> list[str]:
    """Lex, parse, analyze `source` (asserting zero errors), and return `generate(tree)`."""
    errors = ErrorCollector()
    tokens = tokenize(source, errors)
    tree = parse(tokens, errors)
    analyze(tree, errors)
    assert not errors.has_errors(), [e.format() for e in errors.all()]
    return generate(tree)


def main_tac(body: str, prelude: str = "") -> list[str]:
    """Compile `prelude` + `int main() { body }` and return the generated TAC lines."""
    return compile_to_tac(f"{prelude}int main() {{\n{body}}}\n")


# ------------------------------------------------------------------ plan examples (c)

def test_plan_example_precedence_assignment():
    """Plan (c.1): `x = a + b * c;` -> t1 = b * c; t2 = a + t1; x = t2."""
    tac = main_tac(
        "    int a = 1;\n"
        "    int b = 2;\n"
        "    int c = 3;\n"
        "    int x = 0;\n"
        "    x = a + b * c;\n"
        "    return x;\n"
    )
    assert tac == [
        "func main:",
        "  a = 1",
        "  b = 2",
        "  c = 3",
        "  x = 0",
        "  t1 = b * c",
        "  t2 = a + t1",
        "  x = t2",
        "  return x",
        "endfunc",
    ]


def test_plan_example_if_else():
    """Plan (c.2): `if (a < b) { x = 1; } else { x = 2; }`."""
    tac = main_tac(
        "    int a = 1;\n"
        "    int b = 2;\n"
        "    int x = 0;\n"
        "    if (a < b) {\n"
        "        x = 1;\n"
        "    } else {\n"
        "        x = 2;\n"
        "    }\n"
        "    return x;\n"
    )
    assert tac == [
        "func main:",
        "  a = 1",
        "  b = 2",
        "  x = 0",
        "  t1 = a < b",
        "  ifFalse t1 goto L1",
        "  x = 1",
        "  goto L2",
        "L1:",
        "  x = 2",
        "L2:",
        "  return x",
        "endfunc",
    ]


def test_plan_example_nested_call():
    """Plan (c.3): `y = f(a, g(b));` evaluates `g(b)` before emitting outer `param` lines."""
    prelude = (
        "int g(int v) {\n    return v;\n}\n"
        "int f(int p, int q) {\n    return p;\n}\n"
    )
    tac = main_tac(
        "    int a = 1;\n"
        "    int b = 2;\n"
        "    int y = 0;\n"
        "    y = f(a, g(b));\n"
        "    return y;\n",
        prelude=prelude,
    )
    assert tac == [
        "func g:",
        "  return v",
        "endfunc",
        "func f:",
        "  return p",
        "endfunc",
        "func main:",
        "  a = 1",
        "  b = 2",
        "  y = 0",
        "  param b",
        "  t1 = call g, 1",
        "  param a",
        "  param t1",
        "  t2 = call f, 2",
        "  y = t2",
        "  return y",
        "endfunc",
    ]


# ------------------------------------------------------------------ expressions, literals, unary, logical

def test_all_binary_operators_and_no_short_circuit():
    """SPEC section 11 and D-005: all 13 binary ops (including && and ||) emit plain binary instructions."""
    tac = main_tac(
        "    int a = 4;\n"
        "    int b = 2;\n"
        "    int r1 = a + b;\n"
        "    int r2 = a - b;\n"
        "    int r3 = a * b;\n"
        "    int r4 = a / b;\n"
        "    int r5 = a % b;\n"
        "    bool c1 = a < b;\n"
        "    bool c2 = a > b;\n"
        "    bool c3 = a <= b;\n"
        "    bool c4 = a >= b;\n"
        "    bool c5 = a == b;\n"
        "    bool c6 = a != b;\n"
        "    bool c7 = c1 && c2;\n"
        "    bool c8 = c3 || c4;\n"
        "    return r1;\n"
    )
    for expected in [
        "  t1 = a + b",
        "  t2 = a - b",
        "  t3 = a * b",
        "  t4 = a / b",
        "  t5 = a % b",
        "  t6 = a < b",
        "  t7 = a > b",
        "  t8 = a <= b",
        "  t9 = a >= b",
        "  t10 = a == b",
        "  t11 = a != b",
        "  t12 = c1 && c2",
        "  t13 = c3 || c4",
    ]:
        assert expected in tac
    assert not any("goto" in line for line in tac)


def test_unary_operators_and_literal_formats():
    """Plan (a) & (e): unary `x = op y` has a space after op; float, char (with escapes), bool print verbatim."""
    tac = main_tac(
        "    float f = 0.25;\n"
        "    float nf = -f;\n"
        "    char c1 = 'z';\n"
        "    char c2 = '\\t';\n"
        "    char c3 = '\\0';\n"
        "    bool t = true;\n"
        "    bool fa = false;\n"
        "    bool nt = !t;\n"
        "    return 0;\n"
    )
    assert tac == [
        "func main:",
        "  f = 0.25",
        "  t1 = - f",
        "  nf = t1",
        "  c1 = 'z'",
        "  c2 = '\\t'",
        "  c3 = '\\0'",
        "  t = true",
        "  fa = false",
        "  t2 = ! t",
        "  nt = t2",
        "  return 0",
        "endfunc",
    ]


def test_no_conversion_instructions_on_promotion():
    """SPEC section 11: no explicit int-to-float or char-to-int conversion instructions."""
    tac = main_tac(
        "    char c = 'a';\n"
        "    int i = c + 1;\n"
        "    float f = i + 2.5;\n"
        "    return i;\n"
    )
    assert tac == [
        "func main:",
        "  c = 'a'",
        "  t1 = c + 1",
        "  i = t1",
        "  t2 = i + 2.5",
        "  f = t2",
        "  return i",
        "endfunc",
    ]


# ------------------------------------------------------------------ declarations & globals

def test_uninitialized_declarations_emit_nothing():
    """Plan (d): uninitialized global and local declarations emit nothing; no `globals:` header if none initialized."""
    tac = compile_to_tac(
        "int g1;\n"
        "float g2;\n"
        "int main() {\n"
        "    int a;\n"
        "    char b;\n"
        "    return 0;\n"
        "}\n"
    )
    assert tac == [
        "func main:",
        "  return 0",
        "endfunc",
    ]


def test_globals_emitted_first_even_when_declared_after_function():
    """SPEC section 11: all initialized globals appear under `globals:` before any function."""
    tac = compile_to_tac(
        "int f() {\n    return 1;\n}\n"
        "int g = 2 + 3;\n"
        "int main() {\n    return g;\n}\n"
    )
    assert tac == [
        "globals:",
        "  t1 = 2 + 3",
        "  g = t1",
        "func f:",
        "  return 1",
        "endfunc",
        "func main:",
        "  return g",
        "endfunc",
    ]


# ------------------------------------------------------------------ control flow & additions 2, 5

def test_if_without_else_has_no_goto():
    """SPEC section 11: without `else`, no `goto L2` and no second label."""
    tac = main_tac(
        "    int x = 1;\n"
        "    if (x > 0) {\n"
        "        x = 2;\n"
        "    }\n"
        "    return x;\n"
    )
    assert tac == [
        "func main:",
        "  x = 1",
        "  t1 = x > 0",
        "  ifFalse t1 goto L1",
        "  x = 2",
        "L1:",
        "  return x",
        "endfunc",
    ]


def test_else_if_chain_with_four_branches_and_adjacent_labels():
    """Additions 2 & 5: else-if chain with >= 3 branches keeps adjacent closing labels (L6:, L4:, L2:)."""
    tac = main_tac(
        "    int x = 5;\n"
        "    int r = 0;\n"
        "    if (x == 1) {\n"
        "        r = 10;\n"
        "    } else if (x == 2) {\n"
        "        r = 20;\n"
        "    } else if (x == 3) {\n"
        "        r = 30;\n"
        "    } else {\n"
        "        r = 40;\n"
        "    }\n"
        "    return r;\n"
    )
    assert tac == [
        "func main:",
        "  x = 5",
        "  r = 0",
        "  t1 = x == 1",
        "  ifFalse t1 goto L1",
        "  r = 10",
        "  goto L2",
        "L1:",
        "  t2 = x == 2",
        "  ifFalse t2 goto L3",
        "  r = 20",
        "  goto L4",
        "L3:",
        "  t3 = x == 3",
        "  ifFalse t3 goto L5",
        "  r = 30",
        "  goto L6",
        "L5:",
        "  r = 40",
        "L6:",
        "L4:",
        "L2:",
        "  return r",
        "endfunc",
    ]


def test_return_inside_if_and_while_plus_final_return():
    """Addition 2: `return` inside an `if` branch and inside a `while` body, plus the final `return`."""
    tac = compile_to_tac(
        "int search(int n) {\n"
        "    if (n < 0) {\n"
        "        return -1;\n"
        "    }\n"
        "    int i = 0;\n"
        "    while (i < n) {\n"
        "        return i + 100;\n"
        "    }\n"
        "    return 0;\n"
        "}\n"
    )
    assert tac == [
        "func search:",
        "  t1 = n < 0",
        "  ifFalse t1 goto L1",
        "  t2 = - 1",
        "  return t2",
        "L1:",
        "  i = 0",
        "L2:",
        "  t3 = i < n",
        "  ifFalse t3 goto L3",
        "  t4 = i + 100",
        "  return t4",
        "  goto L2",
        "L3:",
        "  return 0",
        "endfunc",
    ]


def test_recursive_factorial_function():
    """Addition 2: recursive factorial function generates param and recursive call instructions."""
    tac = compile_to_tac(
        "int factorial(int n) {\n"
        "    if (n <= 1) {\n"
        "        return 1;\n"
        "    }\n"
        "    return n * factorial(n - 1);\n"
        "}\n"
    )
    assert tac == [
        "func factorial:",
        "  t1 = n <= 1",
        "  ifFalse t1 goto L1",
        "  return 1",
        "L1:",
        "  t2 = n - 1",
        "  param t2",
        "  t3 = call factorial, 1",
        "  t4 = n * t3",
        "  return t4",
        "endfunc",
    ]


def test_for_without_init_or_update():
    """`for (; cond; )` omits init and update without extra instructions."""
    tac = main_tac(
        "    int i = 0;\n"
        "    for (; i < 2; ) {\n"
        "        i = i + 1;\n"
        "    }\n"
        "    return i;\n"
    )
    assert tac == [
        "func main:",
        "  i = 0",
        "L1:",
        "  t1 = i < 2",
        "  ifFalse t1 goto L2",
        "  t2 = i + 1",
        "  i = t2",
        "  goto L1",
        "L2:",
        "  return i",
        "endfunc",
    ]


# ------------------------------------------------------------------ addition 1: no silent tac_name fallback

@pytest.mark.parametrize(
    "source",
    [
        "int g = 1;\n",
        "int main() {\n    int x = 1;\n    return 0;\n}\n",
        "int main() {\n    int x = 1;\n    x = 2;\n    return 0;\n}\n",
        "int main() {\n    return x;\n}\n",
    ],
)
def test_unanalyzed_tree_missing_tac_name_raises_error(source):
    """Addition 1: if semantic analysis did not annotate `tac_name`, `generate` raises ValueError (no fallback)."""
    errors = ErrorCollector()
    tree = parse(tokenize(source, errors), errors)
    with pytest.raises(ValueError, match="tac_name"):
        generate(tree)


# ------------------------------------------------------------------ golden file comparisons

GOLDEN_CASES = sorted(GOLDEN_DIR.glob("*.sl"))


def test_golden_directory_is_populated():
    """Guard against vacuous green if golden files are missing."""
    assert len(GOLDEN_CASES) >= 9


@pytest.mark.parametrize("sl_path", GOLDEN_CASES, ids=lambda p: p.stem)
def test_golden_files_exact_match(sl_path: Path):
    """Every `tests/golden/<name>.sl` compiles cleanly and matches `<name>.tac` line for line."""
    tac_path = sl_path.with_suffix(".tac")
    assert tac_path.is_file(), f"Missing golden file {tac_path}"
    source = sl_path.read_text(encoding="utf-8")
    expected_lines = tac_path.read_text(encoding="utf-8").splitlines()
    actual_lines = compile_to_tac(source)
    assert actual_lines == expected_lines


@pytest.mark.parametrize("sl_path", sorted(VALID_DIR.glob("*.sl")), ids=lambda p: p.name)
def test_all_valid_programs_generate_nonempty_tac(sl_path: Path):
    """Every program in `tests/valid/` generates non-empty TAC without crashing."""
    tac = compile_to_tac(sl_path.read_text(encoding="utf-8"))
    assert len(tac) > 0 and any(line.startswith("func ") for line in tac)


# ------------------------------------------------------------------ hardening (800-term and 3000-term chains)

def test_800_term_addition_chain_generates_correct_tac():
    """Requirement 4: 800-term `1 + 1 + ... + 1` chain uses a left-spine loop (799 temps, no RecursionError)."""
    chain = " + ".join(["1"] * 800)
    tac = main_tac(f"    int x = {chain};\n    return x;\n")
    assert tac[0] == "func main:"
    assert tac[1] == "  t1 = 1 + 1"
    assert tac[2] == "  t2 = t1 + 1"
    assert tac[799] == "  t799 = t798 + 1"
    assert tac[800] == "  x = t799"
    assert tac[801] == "  return x"
    assert tac[802] == "endfunc"
    assert len(tac) == 803


def run_cli(tmp_path, capsys, source: str, flags: list[str]):
    """Write `source` to a temporary `.sl` file, invoke `run`, and return `(code, stdout, stderr)`."""
    path = tmp_path / "prog.sl"
    path.write_text(source, encoding="utf-8")
    code = run(str(path), set(flags))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_cli_3000_term_chain_with_tac_alone_succeeds(tmp_path, capsys):
    """Addition 4: 3000-term `1 + 1 + ...` chain with `--tac` alone succeeds (all stages loop down left spine)."""
    source = "int main() {\n    return " + "1 + " * 3000 + "1;\n}\n"
    code, out, err = run_cli(tmp_path, capsys, source, ["--tac"])
    assert code == 0 and err == ""
    assert "== THREE-ADDRESS CODE ==" in out
    assert "  t1 = 1 + 1" in out
    assert "  t3000 = t2999 + 1" in out
    assert "  return t3000" in out


def test_cli_3000_term_chain_with_tree_and_tac_gives_one_line_error(tmp_path, capsys):
    """Requirement 4 & Addition 4: 3000-term chain with `--tree --tac` gives one-line RecursionError and exit 1."""
    source = "int main() {\n    return " + "1 + " * 3000 + "1;\n}\n"
    code, _, err = run_cli(tmp_path, capsys, source, ["--tree", "--tac"])
    assert code == 1
    assert err == "error: program is nested too deeply to process (recursion limit exceeded)\n"
    assert "Traceback" not in err


def test_cli_900_unary_chain_with_tac_skips_tac_and_exits_1(tmp_path, capsys):
    """Right-nested 900 unary minus chain reports a Semantic error and skips TAC cleanly."""
    source = "int main() {\n    return " + "-" * 900 + "1;\n}\n"
    code, out, err = run_cli(tmp_path, capsys, source, ["--tac"])
    assert code == 1 and err == ""
    assert "Program is nested too deeply to analyze" in out
    tac_section = out.split("== THREE-ADDRESS CODE ==")[1]
    assert tac_section.strip() == "(skipped: compilation errors)"


# ------------------------------------------------------------------ CLI --tac integration

def test_cli_tac_prints_section_after_errors(tmp_path, capsys):
    """Requirement 3: `--tac` prints `== THREE-ADDRESS CODE ==` after `== ERRORS ==` and exits 0 on valid input."""
    source = "int main() {\n    int x = 2 + 3;\n    return x;\n}\n"
    code, out, err = run_cli(tmp_path, capsys, source, ["--symbols", "--tac"])
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
    """Requirement 2 & 3: lexical, syntax, or semantic errors skip TAC and print one skip line."""
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

