"""Phase 5a tests: scopes, declarations and expression typing (SPEC section 8).

Call arity, argument types, return checks and missing return are Phase 5b and are NOT tested here,
except `test_5b_not_checked_yet`, which pins the current behaviour.
"""
import re
import shutil
from pathlib import Path

import pytest

from src.ast_nodes import Call, For, FunctionDecl
from src.errors import ErrorCollector
from src.lexer import tokenize
from src.main import run
from src.parser import parse
from src.semantic import analyze

ROOT = Path(__file__).resolve().parent.parent
INVALID_DIR = ROOT / "tests" / "invalid"
VALID_DIR = ROOT / "tests" / "valid"
EXPECT = re.compile(r"^// EXPECT: Semantic (\d+) (.*)$")

PRELUDE = "    int i = 1;\n    float f = 1.5;\n    char c = 'a';\n    bool b = true;\n"
VALUE = {"int": "i", "float": "f", "char": "c", "bool": "b"}


def analyze_source(source: str):
    """Lex, parse and analyze `source`; return (tree, symbol table, collector)."""
    errors = ErrorCollector()
    tree = parse(tokenize(source, errors), errors)
    table = analyze(tree, errors)
    return tree, table, errors


def semantic(errors: ErrorCollector) -> list[tuple[int, int, str]]:
    """The Semantic errors as (line, col, message)."""
    return [(e.line, e.col, e.message) for e in errors.all() if e.kind == "Semantic"]


def main_body(statements: str) -> str:
    """Wrap statements in `int main() { PRELUDE ... return 0; }` (prelude is lines 2 to 5)."""
    return "int main() {\n" + PRELUDE + statements + "    return 0;\n}\n"


def type_of(expr: str):
    """Return (expr_type of `return EXPR;`, messages) inside a function with i, f, c, b declared."""
    tree, _, errors = analyze_source(f"int main() {{\n{PRELUDE}    return {expr};\n}}\n")
    ret = tree.items[0].body.statements[-1]
    return ret.value.expr_type, [m for _, _, m in semantic(errors)]


# ------------------------------------------------------------ assignability (SPEC table)

LEGAL = {("int", "int"), ("int", "float"), ("float", "float"), ("char", "int"),
         ("char", "float"), ("char", "char"), ("bool", "bool")}


@pytest.mark.parametrize("target", ["int", "float", "char", "bool"])
@pytest.mark.parametrize("value", ["int", "float", "char", "bool"])
def test_assign_table(value, target):
    """All 16 cells of the SPEC assignability table, through an initializer."""
    _, _, errors = analyze_source(main_body(f"    {target} x = {VALUE[value]};\n"))
    found = semantic(errors)
    if (value, target) in LEGAL:
        assert found == []
    else:
        assert found == [(6, 5, f"Cannot assign {value} to {target} variable 'x'")]


@pytest.mark.parametrize("value,target", [("float", "int"), ("int", "char"), ("bool", "int"), ("int", "bool")])
def test_assign_statement_mismatch_position(value, target):
    """An assignment statement reports at the target name (Line 7, Col 5)."""
    source = main_body(f"    {target} x = {VALUE[target]};\n    x = {VALUE[value]};\n")
    assert semantic(analyze_source(source)[2]) == [(7, 5, f"Cannot assign {value} to {target} variable 'x'")]


def test_literal_types():
    """INT_LIT int, FLOAT_LIT float, CHAR_LIT char, true/false bool."""
    assert [type_of(e)[0] for e in ("1", "1.5", "'a'", "true", "false")] == ["int", "float", "char", "bool", "bool"]


# ------------------------------------------------------------------- expression typing

@pytest.mark.parametrize("expr,expected", [
    ("i + i", "int"), ("i - c", "int"), ("c * c", "int"), ("c / i", "int"),
    ("i + f", "float"), ("f * c", "float"), ("f / f", "float"), ("1 + 'a'", "int"),
])
def test_arith_result_types(expr, expected):
    """`+ - * /`: float if either side is float, else int (char promoted to int)."""
    assert type_of(expr) == (expected, [])


def test_char_plus_char_is_int():
    """char is promoted to int in arithmetic, so the result is int, not char."""
    assert type_of("c + c") == ("int", [])


@pytest.mark.parametrize("expr", ["b + 1", "1 - b", "b * b", "f / b"])
def test_arith_rejects_bool(expr):
    """bool is never allowed in arithmetic."""
    result, messages = type_of(expr)
    assert result == "error" and len(messages) == 1 and "requires numeric operands" in messages[0]


@pytest.mark.parametrize("expr,expected", [("i % i", "int"), ("c % i", "int"), ("c % c", "int")])
def test_mod_int_char(expr, expected):
    """`%` accepts int and char."""
    assert type_of(expr) == (expected, [])


@pytest.mark.parametrize("expr", ["f % i", "i % f", "f % f", "b % i"])
def test_mod_rejects_float_and_bool(expr):
    """`%` rejects float and bool operands."""
    result, messages = type_of(expr)
    assert result == "error" and len(messages) == 1 and "'%' requires int or char operands" in messages[0]


def test_unary_minus_types():
    """Unary minus: int for int/char, float for float, error for bool."""
    assert type_of("-i") == ("int", [])
    assert type_of("-c") == ("int", [])
    assert type_of("-f") == ("float", [])
    assert type_of("-b")[0] == "error"


@pytest.mark.parametrize("op", ["<", ">", "<=", ">="])
def test_relational_numeric(op):
    """Relational operators accept any two numeric types and give bool; bool operands are rejected."""
    assert type_of(f"i {op} f") == ("bool", [])
    assert type_of(f"c {op} i") == ("bool", [])
    result, messages = type_of(f"b {op} b")
    assert result == "error" and f"Operator '{op}' requires numeric operands, found bool and bool" in messages


@pytest.mark.parametrize("op", ["==", "!="])
def test_equality_rules(op):
    """== and != accept numeric/numeric and bool/bool only."""
    assert type_of(f"i {op} f") == ("bool", [])
    assert type_of(f"c {op} c") == ("bool", [])
    assert type_of(f"b {op} true") == ("bool", [])
    result, messages = type_of(f"i {op} b")
    assert result == "error"
    assert messages == [f"Operator '{op}' requires two numeric or two bool operands, found int and bool"]


@pytest.mark.parametrize("op", ["&&", "||"])
def test_logical_bool(op):
    """&& and || need two bools."""
    assert type_of(f"b {op} false") == ("bool", [])
    assert type_of(f"i {op} b")[0] == "error"
    assert type_of(f"b {op} 1")[0] == "error"


def test_not_bool():
    """`!` needs a bool."""
    assert type_of("!b") == ("bool", [])
    assert type_of("!i") == ("error", ["Operator '!' requires a bool operand, found int"])


def test_error_type_no_cascade():
    """One mistake gives one error even when wrapped in more operators and conditions."""
    _, _, errors = analyze_source(main_body("    int x = (b + 1) * 2 + 3;\n    if ((b - 1) * 2 < 3 && !(b + 1)) {\n    }\n"))
    assert len(semantic(errors)) == 3   # three independent mistakes, nothing extra


def test_failed_declaration_keeps_declared_type():
    """A bad initializer does not make later uses of the variable errors."""
    _, _, errors = analyze_source(main_body("    int x = 2.5;\n    x = x + 1;\n"))
    assert len(semantic(errors)) == 1


# ------------------------------------------------------------------------ conditions

@pytest.mark.parametrize("keyword,stmt", [
    ("if", "    if (1) {\n    }\n"),
    ("while", "    while (1) {\n    }\n"),
    ("for", "    for (int k = 0; k; k = k + 1) {\n    }\n"),
])
def test_condition_bool(keyword, stmt):
    """if, while and for conditions must be bool; the error is at the condition expression."""
    found = semantic(analyze_source(main_body(stmt))[2])
    assert found == [(6, found[0][1], f"Condition of '{keyword}' must be bool, found int")]


def test_condition_bool_accepted():
    """bool conditions of all three statements are accepted."""
    stmt = "    if (b) {\n    }\n    while (b && i < 3) {\n    }\n    for (int k = 0; k < 3; k = k + 1) {\n    }\n"
    assert semantic(analyze_source(main_body(stmt))[2]) == []


# ------------------------------------------------------------------------------ scopes

def test_shadow_allowed():
    """Shadowing an outer name in an inner block is legal."""
    assert semantic(analyze_source(main_body("    {\n        float i = 2.5;\n    }\n"))[2]) == []


def test_redeclare_same_scope_reports_previous_line():
    """Redeclaration in the same scope is an error naming the first declaration's line."""
    found = semantic(analyze_source(main_body("    int i = 2;\n"))[2])
    assert found == [(6, 5, "'i' is already declared in this scope (line 2)")]


def test_duplicate_parameter_names():
    """`int f(int a, int a)`: the second parameter is a redeclaration in the function scope."""
    found = semantic(analyze_source("int f(int a, int a) {\n    return a;\n}\n")[2])
    assert found == [(1, 14, "'a' is already declared in this scope (line 1)")]


def test_param_and_body_share_scope():
    """Redeclaring a parameter at the body's top level is an error; in a nested block it is shadowing."""
    top = semantic(analyze_source("int f(int a) {\n    int a = 1;\n    return a;\n}\n")[2])
    assert top == [(2, 5, "'a' is already declared in this scope (line 1)")]
    nested = semantic(analyze_source("int f(int a) {\n    {\n        int a = 1;\n    }\n    return a;\n}\n")[2])
    assert nested == []


def test_block_scope_ends():
    """A name declared in a block is gone after the closing brace."""
    found = semantic(analyze_source("int main() {\n    {\n        int inner = 1;\n    }\n    inner = 2;\n    return 0;\n}\n")[2])
    assert found == [(5, 5, "Undeclared identifier 'inner'")]


def test_for_init_scoped():
    """The for init variable lives in the for scope, not after the loop; its body may shadow it."""
    ok = "int main() {\n    for (int k = 0; k < 3; k = k + 1) {\n        int k = 5;\n    }\n    return 0;\n}\n"
    assert semantic(analyze_source(ok)[2]) == []
    bad = "int main() {\n    for (int k = 0; k < 3; k = k + 1) {\n    }\n    return k;\n}\n"
    assert semantic(analyze_source(bad)[2]) == [(4, 12, "Undeclared identifier 'k'")]


def test_global_after_decl():
    """A global variable is visible after its declaration (also inside later functions)."""
    source = "int g = 1;\nint f() {\n    return g;\n}\n"
    assert semantic(analyze_source(source)[2]) == []


def test_global_before_decl():
    """A function placed before a global cannot see the global."""
    source = "int early() {\n    return late;\n}\nint late = 5;\n"
    assert semantic(analyze_source(source)[2]) == [(2, 12, "Undeclared identifier 'late'")]


def test_self_reference_in_initializer():
    """`int x = x;` reports an undeclared x: the name is declared after its initializer (D-028)."""
    found = semantic(analyze_source("int main() {\n    int x = x;\n    return x;\n}\n")[2])
    assert found == [(2, 13, "Undeclared identifier 'x'")]


def test_function_forward_call_and_recursion():
    """Functions are visible everywhere: forward calls and recursion are legal."""
    source = "int a() {\n    return b();\n}\nint b() {\n    return b();\n}\n"
    assert semantic(analyze_source(source)[2]) == []


def test_duplicate_function():
    """A second function with the same name is an error; the first declaration stays in force."""
    source = "int f() {\n    return 1;\n}\nfloat f() {\n    return 2.5;\n}\nint g() {\n    return f();\n}\n"
    tree, _, errors = analyze_source(source)
    assert semantic(errors) == [(4, 1, "Function 'f' is already declared (line 1)")]
    assert tree.items[2].body.statements[0].value.expr_type == "int"


def test_undeclared_function_and_variable():
    """Undeclared identifier and call to an undeclared function."""
    source = "int main() {\n    int a = y;\n    return nope(1);\n}\n"
    assert semantic(analyze_source(source)[2]) == [
        (2, 13, "Undeclared identifier 'y'"), (3, 12, "Call to undeclared function 'nope'")]


# ---------------------------------------------------------------------- const and functions

def test_const_without_initializer_local_and_global():
    """`const` needs an initializer, both inside a function and at top level."""
    local = semantic(analyze_source("int main() {\n    const int c;\n    return 0;\n}\n")[2])
    assert local == [(2, 5, "Constant 'c' must have an initializer")]
    top = semantic(analyze_source("const int C;\n")[2])
    assert top == [(1, 1, "Constant 'C' must have an initializer")]


def test_const_reassignment():
    """Assigning to a const is an error at the target name."""
    source = "int main() {\n    const int c = 1;\n    c = 2;\n    return c;\n}\n"
    assert semantic(analyze_source(source)[2]) == [(3, 5, "Cannot assign to constant 'c'")]


def test_const_initialized_with_wrong_type():
    """A const initializer follows the same assignability rule as a variable."""
    found = semantic(analyze_source("const int C = 1.5;\nconst char D = 66;\n")[2])
    assert found == [(1, 1, "Cannot assign float to int variable 'C'"),
                     (2, 1, "Cannot assign int to char variable 'D'")]


def test_const_as_for_loop_variable():
    """Init and update both assign to the const: two errors."""
    source = "int main() {\n    const int i = 0;\n    for (i = 0; i < 3; i = i + 1) {\n    }\n    return 0;\n}\n"
    assert semantic(analyze_source(source)[2]) == [
        (3, 10, "Cannot assign to constant 'i'"), (3, 24, "Cannot assign to constant 'i'")]


def test_function_name_as_value_and_target():
    """A function name cannot be read or assigned as a variable."""
    source = "int f() {\n    return 1;\n}\nint main() {\n    int x = f;\n    f = 2;\n    return x;\n}\n"
    assert semantic(analyze_source(source)[2]) == [
        (5, 13, "Function 'f' cannot be used as a variable"), (6, 5, "Cannot assign to function 'f'")]


def test_call_has_return_type():
    """A call has the function's return type; its arguments are typed (errors inside are reported)."""
    source = "float half(int a) {\n    return a / 2;\n}\nint main() {\n    float h = half(true + 1);\n    return 0;\n}\n"
    tree, _, errors = analyze_source(source)
    assert semantic(errors) == [(5, 25, "Operator '+' requires numeric operands, found bool and int")]
    assert tree.items[1].body.statements[0].init.expr_type == "float"


def test_5b_not_checked_yet():
    # Phase 5b MUST replace this test: arity, argument types and return types will become errors.
    source = ("int f(int a) {\n    return 1.5;\n}\nint main() {\n    int x = f(1, 2, true);\n"
              "    x = 1;\n    return x(3);\n}\n")
    assert semantic(analyze_source(source)[2]) == []


def test_long_operator_chain_does_not_crash():
    """2000 chained `+` (a deep left-nested tree) is analyzed without hitting the recursion limit."""
    source = "int main() {\n    return " + "1 + " * 2000 + "1;\n}\n"
    tree, _, errors = analyze_source(source)
    assert semantic(errors) == [] and tree.items[0].body.statements[0].value.expr_type == "int"


def test_extreme_nesting_is_an_error_not_a_crash():
    """900 stacked unary minus signs pass the parser; the analyzer must report, never raise."""
    source = "int main() {\n    return " + "-" * 900 + "1;\n}\n"
    _, _, errors = analyze_source(source)
    assert all(e.kind == "Semantic" for e in errors.all())   # either fine or one nesting error


# ------------------------------------------------------------------------ tac_name

def test_tac_names_shadowing():
    """Shadowing declarations get x, x_1, x_2 (unique over the whole program)."""
    source = "int x = 1;\nint main() {\n    int x = 2;\n    {\n        int x = 3;\n    }\n    return x;\n}\n"
    tree, _, _ = analyze_source(source)
    assert tree.items[0].tac_name == "x"
    assert tree.items[1].body.statements[0].tac_name == "x_1"
    assert tree.items[1].body.statements[1].statements[0].tac_name == "x_2"
    assert tree.items[1].body.statements[2].value.tac_name == "x_1"   # `return x` sees the middle x


def test_tac_name_skips_user_x_1():
    """A user variable literally named x_1 is never reused for a shadowing x."""
    source = "int main() {\n    int x = 1;\n    int x_1 = 2;\n    {\n        int x = 3;\n    }\n    return 0;\n}\n"
    tree, _, _ = analyze_source(source)
    names = [s.tac_name for s in tree.items[0].body.statements[:2]] + [tree.items[0].body.statements[2].statements[0].tac_name]
    assert names == ["x", "x_1", "x_2"]


def test_tac_name_never_collides_with_temporaries_and_labels():
    """Names shaped like t<digits> or L<digits> count as taken: t1 becomes t1_1, L2 becomes L2_1."""
    source = ("int t1 = 1;\nint main() {\n    int L2 = 2;\n    int t1 = 3;\n    int t = 4;\n    int L = 5;\n"
              "    return t1;\n}\n")
    tree, _, _ = analyze_source(source)
    body = tree.items[1].body.statements
    assert [tree.items[0].tac_name, body[0].tac_name, body[1].tac_name, body[2].tac_name, body[3].tac_name] == [
        "t1_1", "L2_1", "t1_2", "t", "L"]
    assert body[4].value.tac_name == "t1_2"


def test_annotations_present():
    """expr_type, tac_name and scope_id are filled in; function scope is shared with its body."""
    source = ("int f(int a) {\n    for (int k = 0; k < a; k = k + 1) {\n        a = a + k;\n    }\n"
              "    return a;\n}\n")
    tree, table, errors = analyze_source(source)
    assert semantic(errors) == []
    fn: FunctionDecl = tree.items[0]
    loop: For = fn.body.statements[0]
    assert fn.scope_id == fn.body.scope_id == 1
    assert loop.scope_id == 2 and loop.body.scope_id == 3
    assert fn.params[0].tac_name == "a" and loop.init.tac_name == "k"
    assert loop.condition.expr_type == "bool" and loop.condition.left.tac_name == "k"
    assert loop.update.tac_name == "k"
    dump = table.dump()
    assert "Scope 0 (global)" in dump and "Scope 1 (function f)" in dump and "Scope 2 (for)" in dump
    assert "Scope 3 (block)" in dump


def test_call_expr_type_annotated():
    """Call nodes carry the callee's return type."""
    tree, _, _ = analyze_source("char g() {\n    return 'a';\n}\nint main() {\n    g();\n    return 0;\n}\n")
    call = tree.items[1].body.statements[0].call
    assert isinstance(call, Call) and call.expr_type == "char"


# ----------------------------------------------------------- files in tests/valid, tests/invalid

@pytest.mark.parametrize("path", sorted(VALID_DIR.glob("*.sl")), ids=lambda p: p.name)
def test_valid_files_have_no_errors(path):
    """Every tests/valid file passes lexer, parser and the semantic analyzer with zero errors."""
    _, _, errors = analyze_source(path.read_text(encoding="utf-8"))
    assert [e.format() for e in errors.all()] == []


@pytest.mark.parametrize("path", sorted(INVALID_DIR.glob("semantic_*.sl")), ids=lambda p: p.name)
def test_invalid_files_report_expected_errors(path):
    """Each `// EXPECT: Semantic <line> <substring>` is matched by exactly one error; nothing else is reported."""
    text = path.read_text(encoding="utf-8")
    expected = [(int(m.group(1)), m.group(2)) for m in map(EXPECT.match, text.splitlines()) if m]
    assert expected, f"{path.name} has no EXPECT lines"
    _, _, errors = analyze_source(text)
    assert not errors.has_kind("Lexical") and not errors.has_kind("Syntax")
    remaining = semantic(errors)
    for line, fragment in expected:
        match = next((e for e in remaining if e[0] == line and fragment in e[2]), None)
        assert match is not None, f"{path.name}: no error at line {line} containing {fragment!r}; got {remaining}"
        remaining.remove(match)
    assert remaining == [], f"{path.name}: unexpected extra errors {remaining}"


# ------------------------------------------------------------------------------ CLI

TYPE_ERROR = "int main() {\n    int x = 2.5;\n    return x;\n}\n"
SYNTAX_PLUS_TYPE = "int main() {\n    int x = 2.5;\n    int y = 1\n    return x;\n}\n"
GOOD = "int main() {\n    int x = 2;\n    return x;\n}\n"
SPEC_ERROR_LINE = "[Semantic Error] Line 2, Col 5: Cannot assign float to int variable 'x'"


def run_cli(tmp_path, capsys, source, flags):
    """Write `source`, run the CLI, return (exit code, stdout)."""
    path = tmp_path / "prog.sl"
    path.write_text(source, encoding="utf-8")
    code = run(str(path), set(flags))
    return code, capsys.readouterr().out


@pytest.mark.parametrize("flags", [["--tree"], ["--symbols"], ["--tree", "--symbols"]])
def test_cli_semantic_error_only(tmp_path, capsys, flags):
    """A type error shows under == ERRORS == and gives exit 1; --symbols still prints the tables."""
    code, out = run_cli(tmp_path, capsys, TYPE_ERROR, flags)
    assert code == 1
    assert SPEC_ERROR_LINE in out.split("== ERRORS ==")[1]
    if "--symbols" in flags:
        assert "== SYMBOL TABLES ==" in out and "Scope 1 (function main)" in out
        assert out.index("== SYMBOL TABLES ==") < out.index("== ERRORS ==")


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz dot binary not installed")
def test_cli_semantic_error_with_tree_png(tmp_path, capsys):
    """--tree-png also runs the semantic stage."""
    path = tmp_path / "prog.sl"
    path.write_text(TYPE_ERROR, encoding="utf-8")
    code = run(str(path), {"--tree-png"}, str(tmp_path / "t.png"))
    assert code == 1 and SPEC_ERROR_LINE in capsys.readouterr().out


@pytest.mark.parametrize("flags", [["--tree"], ["--symbols"]])
def test_cli_syntax_error_hides_type_error(tmp_path, capsys, flags):
    """Syntax error plus type error: only the syntax error is reported; --symbols says the stage was skipped."""
    code, out = run_cli(tmp_path, capsys, SYNTAX_PLUS_TYPE, flags)
    assert code == 1
    errors_section = out.split("== ERRORS ==")[1]
    assert "[Syntax Error]" in errors_section and "[Semantic Error]" not in errors_section
    if "--symbols" in flags:
        symbols = out.split("== SYMBOL TABLES ==")[1].split("== ERRORS ==")[0]
        assert symbols.strip() == "(skipped: lexical or syntax errors)"


def test_cli_valid_file(tmp_path, capsys):
    """A valid file exits 0, prints the tables and `(none)` under errors."""
    code, out = run_cli(tmp_path, capsys, GOOD, ["--symbols"])
    assert code == 0 and "Scope 0 (global)" in out and out.rstrip().endswith("(none)")


def test_cli_without_parser_flags_skips_semantics(tmp_path, capsys):
    """Only --tokens: the parser (and so the semantic stage) does not run yet (D-019; Phase 7 changes this)."""
    code, out = run_cli(tmp_path, capsys, TYPE_ERROR, ["--tokens"])
    assert code == 0 and "Semantic" not in out
