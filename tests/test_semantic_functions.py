"""Phase 5b tests: function rules of SPEC section 8 (calls, arguments, return, missing return).

The `tests/invalid/semantic_*.sl` files for these rules are run by `test_semantic.py`
(`test_invalid_files_report_expected_errors`); this file holds the column checks and the edge cases.
"""
import pytest

from src.ast_nodes import Call, CallStmt
from tests.test_semantic import analyze_source, semantic

ADD = "int add(int a, int b) {\n    return a + b;\n}\n"      # lines 1 to 3


def messages(source: str) -> list[tuple[int, int, str]]:
    """The Semantic errors of `source` as (line, col, message)."""
    return semantic(analyze_source(source)[2])


def in_main(statements: str, extra: str = "") -> str:
    """`extra` (functions) followed by `main` whose body starts on the line after `int main() {`."""
    return extra + "int main() {\n" + statements + "    return 0;\n}\n"


# ------------------------------------------------------------------ callee (rule: variable cannot be called)

@pytest.mark.parametrize("decl", ["int x = 1;", "const int x = 1;"])
def test_call_variable_or_constant(decl):
    """E2 at the call's name token."""
    assert messages(in_main(f"    {decl}\n    int y = x(3);\n")) == [
        (3, 13, "Cannot call 'x': it is a variable, not a function")]


def test_call_parameter():
    source = "int f(int p) {\n    return p(1);\n}\n"
    assert messages(source) == [(2, 12, "Cannot call 'p': it is a variable, not a function")]


def test_call_variable_is_error_type_no_cascade():
    """The failed call has type `error`, so `x(3) + true` adds nothing."""
    assert len(messages(in_main("    int x = 1;\n    int y = x(3) + true;\n"))) == 1


def test_call_variable_still_types_arguments():
    errs = messages(in_main("    int x = 1;\n    int y = x(true + 1);\n"))
    assert [m for _, _, m in errs] == [
        "Cannot call 'x': it is a variable, not a function",
        "Operator '+' requires numeric operands, found bool and int"]


def test_call_undeclared_function_still_reported():
    assert messages(in_main("    int y = ghost(1);\n")) == [(2, 13, "Call to undeclared function 'ghost'")]


def test_variable_shadowing_a_function_cannot_be_called():
    """A local `add` hides the function; calling it is E2."""
    source = in_main("    int add = 1;\n    int y = add(1, 2);\n", ADD)
    assert messages(source) == [(6, 13, "Cannot call 'add': it is a variable, not a function")]


# ------------------------------------------------------------------ arity

@pytest.mark.parametrize("args,found", [("", 0), ("1", 1), ("1, 2, 3", 3)])
def test_arity_mismatch_message_and_position(args, found):
    errs = messages(in_main(f"    int y = add({args});\n", ADD))
    assert errs == [(5, 13, f"Function 'add' expects 2 arguments, found {found}")]


def test_arity_singular_and_zero():
    source = "int one(int a) {\n    return a;\n}\nint zero() {\n    return 0;\n}\n"
    assert messages(in_main("    int y = one();\n    int z = zero(1);\n", source)) == [
        (8, 13, "Function 'one' expects 1 argument, found 0"),
        (9, 13, "Function 'zero' expects 0 arguments, found 1")]


def test_arity_mismatch_skips_argument_types_but_types_arguments():
    """One mistake, one message: `add(true)` is an arity error only; errors INSIDE arguments still show."""
    assert len(messages(in_main("    int y = add(true);\n", ADD))) == 1
    inner = messages(in_main("    int y = add(1, 2 % 1.5, 3);\n", ADD))
    assert [m for _, _, m in inner] == ["Function 'add' expects 2 arguments, found 3",
                                        "Operator '%' requires int or char operands, found int and float"]


def test_arity_error_call_keeps_return_type():
    """After an arity error the call still has the function's type, so `int y = f(...)` is not a second error."""
    source = in_main("    float z = fl(1);\n    bool w = fl(1);\n", "float fl() {\n    return 1.5;\n}\n")
    errs = messages(source)
    assert [m for _, _, m in errs] == ["Function 'fl' expects 0 arguments, found 1",
                                       "Cannot assign float to bool variable 'w'",   # col 5, before the call
                                       "Function 'fl' expects 0 arguments, found 1"]


# ------------------------------------------------------------------ argument types

@pytest.mark.parametrize("param,value,ok", [
    ("int", "1", True), ("int", "'a'", True), ("int", "1.5", False), ("int", "true", False),
    ("float", "1", True), ("float", "'a'", True), ("float", "1.5", True), ("float", "true", False),
    ("char", "'a'", True), ("char", "1", False), ("char", "1.5", False), ("char", "true", False),
    ("bool", "true", True), ("bool", "1", False), ("bool", "'a'", False), ("bool", "1.5", False)])
def test_argument_assignability_table(param, value, ok):
    """All 16 cells of the SPEC table, through a parameter. E4 is reported at the argument."""
    source = f"int g({param} p) {{\n    return 0;\n}}\n"
    errs = messages(in_main(f"    int y = g({value});\n", source))
    if ok:
        assert errs == []
    else:
        found = {"1": "int", "'a'": "char", "1.5": "float", "true": "bool"}[value]
        assert errs == [(5, 15, f"Argument 1 of 'g': cannot pass {found} to {param} parameter 'p'")]


def test_argument_error_reported_at_expression_start_convention():
    """A binary-operator argument is reported at its operator token (D-030), here the `+` at column 24."""
    errs = messages(in_main("    int y = add(1, 2.5 + 1);\n", ADD))
    assert errs == [(5, 24, "Argument 2 of 'add': cannot pass float to int parameter 'b'")]


def test_each_bad_argument_reported():
    errs = messages(in_main("    int y = add(1.5, true);\n", ADD))
    assert [m for _, _, m in errs] == ["Argument 1 of 'add': cannot pass float to int parameter 'a'",
                                       "Argument 2 of 'add': cannot pass bool to int parameter 'b'"]


def test_error_typed_argument_is_silent():
    """`ghost` is already reported; passing it on adds no argument error."""
    errs = messages(in_main("    int y = add(ghost, 1);\n", ADD))
    assert [m for _, _, m in errs] == ["Undeclared identifier 'ghost'"]


def test_argument_is_a_call_result():
    source = in_main("    int y = add(fl(), 1);\n", ADD + "float fl() {\n    return 1.5;\n}\n")
    assert [m for _, _, m in messages(source)] == ["Argument 1 of 'add': cannot pass float to int parameter 'a'"]


# ------------------------------------------------------------------ call result type

@pytest.mark.parametrize("type_name", ["int", "float", "char", "bool"])
def test_call_has_declared_return_type(type_name):
    value = {"int": "1", "float": "1.5", "char": "'a'", "bool": "true"}[type_name]
    source = f"{type_name} g() {{\n    return {value};\n}}\nint main() {{\n    return g();\n}}\n"
    tree, _, _ = analyze_source(source)
    assert tree.items[1].body.statements[0].value.expr_type == type_name


def test_call_statement_discards_result_but_is_checked():
    """CallStmt: arity and argument errors are reported, a good call is silent."""
    assert messages(in_main("    add(1, 2);\n", ADD)) == []
    tree, _, _ = analyze_source(in_main("    add(1, 2);\n", ADD))
    stmt = tree.items[1].body.statements[0]
    assert isinstance(stmt, CallStmt) and isinstance(stmt.call, Call) and stmt.call.expr_type == "int"
    assert messages(in_main("    add(1);\n", ADD)) == [(5, 5, "Function 'add' expects 2 arguments, found 1")]
    assert messages(in_main("    add(1, 2.5);\n", ADD)) == [
        (5, 12, "Argument 2 of 'add': cannot pass float to int parameter 'b'")]


def test_call_statement_on_variable():
    assert messages(in_main("    int x = 1;\n    x(2);\n")) == [
        (3, 5, "Cannot call 'x': it is a variable, not a function")]


def test_forward_call_and_recursion_have_argument_checks():
    """Pass 1 makes signatures known before bodies: a forward call is checked like any other call."""
    source = "int a() {\n    return b(1.5);\n}\nint b(int n) {\n    return b(n);\n}\n"
    assert messages(source) == [(2, 14, "Argument 1 of 'b': cannot pass float to int parameter 'n'")]


# ------------------------------------------------------------------ return type

@pytest.mark.parametrize("ret,value,ok", [
    ("int", "1", True), ("int", "'a'", True), ("int", "1.5", False), ("int", "true", False),
    ("float", "1", True), ("float", "'a'", True), ("float", "1.5", True), ("float", "true", False),
    ("char", "'a'", True), ("char", "1", False), ("char", "1.5", False), ("char", "true", False),
    ("bool", "true", True), ("bool", "1", False), ("bool", "'a'", False), ("bool", "1.5", False)])
def test_return_assignability_table(ret, value, ok):
    """All 16 cells of the SPEC table through `return`; E5 is at the `return` keyword."""
    errs = messages(f"{ret} f() {{\n    return {value};\n}}\n")
    if ok:
        assert errs == []
    else:
        found = {"1": "int", "'a'": "char", "1.5": "float", "true": "bool"}[value]
        assert errs == [(2, 5, f"Cannot return {found} from function 'f' returning {ret}")]


def test_return_checked_against_its_own_function():
    """Two functions with different return types: each `return` uses the type of the function it is in."""
    source = "int a() {\n    return 1;\n}\nfloat b() {\n    return 1.5;\n}\nchar c() {\n    return 1.5;\n}\n"
    assert messages(source) == [(8, 5, "Cannot return float from function 'c' returning char")]


def test_return_in_nested_block_if_for_while():
    source = ("int f(int n) {\n    if (n > 0) {\n        return 1.5;\n    } else {\n        return true;\n    }\n"
              "    for (int i = 0; i < n; i = i + 1) {\n        { return 'a'; }\n    }\n    return 0;\n}\n")
    assert messages(source) == [(3, 9, "Cannot return float from function 'f' returning int"),
                                (5, 9, "Cannot return bool from function 'f' returning int")]


def test_return_with_error_expression_is_silent():
    assert [m for _, _, m in messages("int f() {\n    return ghost;\n}\n")] == ["Undeclared identifier 'ghost'"]


def test_return_value_is_a_call():
    source = "float g() {\n    return 1.5;\n}\nint f() {\n    return g();\n}\n"
    assert messages(source) == [(5, 5, "Cannot return float from function 'f' returning int")]


# ------------------------------------------------------------------ missing return

def test_missing_return_empty_body_position():
    """E6 is at the closing brace, not at the header."""
    assert messages("int f() {\n}\n") == [(2, 1, "Missing return at end of function 'f'")]


def test_missing_return_position_one_line_function():
    """`int f() { }`: the `}` is column 11 of line 1."""
    assert messages("int f() { }\n") == [(1, 11, "Missing return at end of function 'f'")]


def test_missing_return_position_multi_line_with_indent():
    source = "int f(int a) {\n    a = a + 1;\n    int b = a;\n    }\n"
    assert messages(source) == [(4, 5, "Missing return at end of function 'f'")]


def test_return_not_last_is_missing():
    """A return in the MIDDLE does not count: the LAST statement must be a return (SPEC)."""
    source = "int f() {\n    return 1;\n    int x = 2;\n}\n"
    assert messages(source) == [(4, 1, "Missing return at end of function 'f'")]


def test_return_last_is_fine_even_with_code_before():
    assert messages("int f(int n) {\n    int x = n;\n    x = x + 1;\n    return x;\n}\n") == []


def test_if_else_both_return_is_still_missing_return():
    """D-035: the SPEC rule is strict; both branches returning does not satisfy it."""
    source = "int f(bool b) {\n    if (b) {\n        return 1;\n    } else {\n        return 2;\n    }\n}\n"
    assert messages(source) == [(7, 1, "Missing return at end of function 'f'")]


def test_if_else_both_return_then_final_return_is_valid():
    source = ("int f(bool b) {\n    if (b) {\n        return 1;\n    } else {\n        return 2;\n    }\n"
              "    return 0;\n}\n")
    assert messages(source) == []


@pytest.mark.parametrize("last", ["{ return 1; }", "while (true) { return 1; }",
                                  "for (int i = 0; i < 1; i = i + 1) { return 1; }", "f2();"])
def test_other_last_statements_are_missing_return(last):
    source = f"int f2() {{\n    return 1;\n}}\nint f() {{\n    {last}\n}}\n"
    assert messages(source) == [(6, 1, "Missing return at end of function 'f'")]


def test_missing_return_in_each_function_reported():
    source = "int a() {\n}\nint b() {\n    return 1;\n}\nint c() {\n}\n"
    assert messages(source) == [(2, 1, "Missing return at end of function 'a'"),
                                (7, 1, "Missing return at end of function 'c'")]


def test_wrong_return_and_missing_return_both_reported():
    errs = messages("int f() {\n    return 1.5;\n    int x = 1;\n}\n")
    assert errs == [(2, 5, "Cannot return float from function 'f' returning int"),
                    (4, 1, "Missing return at end of function 'f'")]


def test_missing_return_when_end_position_unknown_falls_back_to_header():
    """A hand-built Block has end_line 0 (D-034): the error then uses the function header position."""
    from src.errors import ErrorCollector
    from src.semantic import analyze
    tree, _, _ = analyze_source("int f() {\n    return 1;\n}\n")
    tree.items[0].body.statements.clear()
    tree.items[0].body.end_line = 0
    errors = ErrorCollector()
    analyze(tree, errors)
    assert semantic(errors) == [(1, 1, "Missing return at end of function 'f'")]


def test_block_records_closing_brace_position():
    """D-034: parse_block stores the position of its `}`."""
    tree, _, _ = analyze_source("int f() {\n    return 1;\n  }\n")
    body = tree.items[0].body
    assert (body.end_line, body.end_col) == (3, 3)
