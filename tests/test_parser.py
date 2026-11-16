"""Phase 2 tests: parser, node classes, tree export and the --tree CLI stage."""
import shutil
from pathlib import Path

import pytest

from src.ast_nodes import (
    Assign, BinaryOp, Block, Call, CallStmt, For, FunctionDecl, Identifier,
    If, Literal, Node, Param, Program, Return, UnaryOp, VarDecl, While)
from src.errors import ErrorCollector
from src.lexer import tokenize
from src.main import run
from src.parser import parse
from src.tree_export import export_png, tree_to_dot, tree_to_text

ROOT = Path(__file__).resolve().parent.parent
SPEC_SAMPLE = ROOT / "samples" / "valid_program.sl"


def parse_source(source: str) -> tuple[Program, ErrorCollector]:
    """Lex and parse a source string; return the tree and the shared collector."""
    errors = ErrorCollector()
    return parse(tokenize(source, errors), errors), errors


def parse_ok(source: str) -> Program:
    """Parse source that must be valid; fail the test on any error."""
    tree, errors = parse_source(source)
    assert [e.format() for e in errors.all()] == []
    return tree


def expr_of(text: str):
    """Parse `int main() { return <text>; }` and return the returned expression."""
    tree = parse_ok("int main() { return " + text + "; }")
    return tree.items[0].body.statements[0].value


def body_of(statements: str) -> list:
    """Parse statements inside main() and return the statement nodes."""
    tree = parse_ok("int main() { " + statements + " return 0; }")
    return tree.items[0].body.statements[:-1]


def shape(node) -> str:
    """Compact prefix form of an expression, e.g. (+ 1 (* 2 3)). Used to check precedence."""
    if isinstance(node, BinaryOp):
        return f"({node.op} {shape(node.left)} {shape(node.right)})"
    if isinstance(node, UnaryOp):
        return f"({node.op} {shape(node.operand)})"
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Identifier):
        return node.name
    if isinstance(node, Call):
        return f"{node.name}({', '.join(shape(a) for a in node.args)})"
    raise AssertionError(f"unexpected node {node!r}")


# ---------------------------------------------------------------- top level

def test_top_level_items_in_order():
    tree = parse_ok("const int A = 1; int g; int f() { return A; }")
    assert [type(i) for i in tree.items] == [VarDecl, VarDecl, FunctionDecl]
    assert tree.items[0].is_const and tree.items[0].init is not None
    assert not tree.items[1].is_const and tree.items[1].init is None


def test_empty_program():
    tree = parse_ok("")
    assert tree.items == []


def test_global_var_with_initializer():
    decl = parse_ok("float rate = 2.5;").items[0]
    assert (decl.type_name, decl.name, decl.is_const) == ("float", "rate", False)
    assert shape(decl.init) == "2.5"


def test_function_with_multiple_parameters():
    func = parse_ok("float avg(int a, char b, bool c) { return 1; }").items[0]
    assert func.return_type == "float" and func.name == "avg"
    assert [(p.type_name, p.name) for p in func.params] == [
        ("int", "a"), ("char", "b"), ("bool", "c")]
    assert all(isinstance(p, Param) for p in func.params)


def test_function_without_parameters():
    func = parse_ok("int main() { return 0; }").items[0]
    assert func.params == []
    assert isinstance(func.body, Block)


# --------------------------------------------------------------- statements

def test_local_var_decl_and_const():
    plain, const, bare = body_of("int a = 1; const int B = 2; bool c;")
    assert (plain.name, plain.is_const) == ("a", False)
    assert (const.name, const.is_const) == ("B", True)
    assert bare.init is None and bare.type_name == "bool"


def test_assign_statement():
    stmt = body_of("x = y + 1;")[0]
    assert isinstance(stmt, Assign) and stmt.name == "x"
    assert shape(stmt.value) == "(+ y 1)"


def test_call_statement():
    stmt = body_of("f(1, x);")[0]
    assert isinstance(stmt, CallStmt)
    assert isinstance(stmt.call, Call) and shape(stmt.call) == "f(1, x)"


def test_call_statement_without_arguments():
    stmt = body_of("f();")[0]
    assert isinstance(stmt, CallStmt) and stmt.call.args == []


def test_return_statement():
    tree = parse_ok("int f() { return 1 + 2; }")
    ret = tree.items[0].body.statements[0]
    assert isinstance(ret, Return) and shape(ret.value) == "(+ 1 2)"


def test_nested_block_statement():
    stmt = body_of("{ int a = 1; { a = 2; } }")[0]
    assert isinstance(stmt, Block)
    assert isinstance(stmt.statements[0], VarDecl)
    assert isinstance(stmt.statements[1], Block)


def test_if_without_else():
    stmt = body_of("if (a < b) { x = 1; }")[0]
    assert isinstance(stmt, If)
    assert shape(stmt.condition) == "(< a b)"
    assert isinstance(stmt.then_block, Block) and stmt.else_branch is None


def test_if_else():
    stmt = body_of("if (a) { x = 1; } else { x = 2; }")[0]
    assert isinstance(stmt.else_branch, Block)


def test_else_if_chain_nests_as_if_in_else_branch():
    stmt = body_of(
        "if (a) { x = 1; } else if (b) { x = 2; } else if (c) { x = 3; } "
        "else { x = 4; }")[0]
    second = stmt.else_branch
    third = second.else_branch
    assert isinstance(second, If) and shape(second.condition) == "b"
    assert isinstance(third, If) and shape(third.condition) == "c"
    assert isinstance(third.else_branch, Block)


def test_else_if_without_final_else():
    stmt = body_of("if (a) { x = 1; } else if (b) { x = 2; }")[0]
    assert isinstance(stmt.else_branch, If) and stmt.else_branch.else_branch is None


def test_nested_if_inside_if():
    stmt = body_of("if (a) { if (b) { x = 1; } else { x = 2; } }")[0]
    inner = stmt.then_block.statements[0]
    assert isinstance(inner, If) and isinstance(inner.else_branch, Block)
    assert stmt.else_branch is None


def test_while_statement():
    stmt = body_of("while (i <= n) { i = i + 1; }")[0]
    assert isinstance(stmt, While) and shape(stmt.condition) == "(<= i n)"
    assert len(stmt.body.statements) == 1


def test_for_with_declaration_init():
    stmt = body_of("for (int k = 0; k < 3; k = k + 1) { r = r + k; }")[0]
    assert isinstance(stmt, For)
    assert isinstance(stmt.init, VarDecl) and stmt.init.name == "k"
    assert shape(stmt.condition) == "(< k 3)"
    assert isinstance(stmt.update, Assign) and stmt.update.name == "k"


def test_for_with_assignment_init():
    stmt = body_of("for (k = 0; k < 3; k = k + 1) { }")[0]
    assert isinstance(stmt.init, Assign) and stmt.init.name == "k"


def test_for_without_init_and_update():
    stmt = body_of("for (; i < 3; ) { i = i + 1; }")[0]
    assert stmt.init is None and stmt.update is None
    assert shape(stmt.condition) == "(< i 3)"


def test_for_without_init_only():
    stmt = body_of("for (; i < 3; i = i + 1) { }")[0]
    assert stmt.init is None and isinstance(stmt.update, Assign)


def test_for_without_update_only():
    stmt = body_of("for (int i = 0; i < 3; ) { }")[0]
    assert isinstance(stmt.init, VarDecl) and stmt.update is None


def test_nested_loops():
    stmt = body_of(
        "for (int i = 0; i < 3; i = i + 1) { "
        "  while (j < i) { for (int k = 0; k < j; k = k + 1) { s = s + k; } } }")[0]
    inner_while = stmt.body.statements[0]
    inner_for = inner_while.body.statements[0]
    assert isinstance(stmt, For) and isinstance(inner_while, While)
    assert isinstance(inner_for, For)


# --------------------------------------------------------------- expressions

def test_precedence_mul_over_add():
    assert shape(expr_of("1 + 2 * 3")) == "(+ 1 (* 2 3))"


def test_precedence_mul_on_left_still_binds_tighter():
    assert shape(expr_of("1 * 2 + 3")) == "(+ (* 1 2) 3)"


def test_precedence_and_over_or():
    assert shape(expr_of("a || b && c")) == "(|| a (&& b c))"


def test_precedence_or_with_and_on_left():
    assert shape(expr_of("a && b || c")) == "(|| (&& a b) c)"


def test_precedence_relational_over_equality():
    assert shape(expr_of("a == b < c")) == "(== a (< b c))"


def test_precedence_equality_over_and():
    assert shape(expr_of("a && b == c")) == "(&& a (== b c))"


def test_precedence_add_over_relational():
    assert shape(expr_of("a + 1 < b - 2")) == "(< (+ a 1) (- b 2))"


def test_precedence_unary_over_multiplication():
    assert shape(expr_of("-a * b")) == "(* (- a) b)"


def test_unary_not_and_double_unary():
    assert shape(expr_of("!!a")) == "(! (! a))"
    assert shape(expr_of("- -a")) == "(- (- a))"


def test_parentheses_override_precedence():
    assert shape(expr_of("(1 + 2) * 3")) == "(* (+ 1 2) 3)"


def test_left_associative_subtraction():
    assert shape(expr_of("a - b - c")) == "(- (- a b) c)"


def test_left_associative_division_and_modulo():
    assert shape(expr_of("a / b % c")) == "(% (/ a b) c)"


def test_left_associative_comparison_chain():
    assert shape(expr_of("a < b < c")) == "(< (< a b) c)"
    assert shape(expr_of("a == b != c")) == "(!= (== a b) c)"


def test_left_associative_logical_chains():
    assert shape(expr_of("a || b || c")) == "(|| (|| a b) c)"
    assert shape(expr_of("a && b && c")) == "(&& (&& a b) c)"


def test_all_relational_operators():
    for op in ("<", ">", "<=", ">=", "==", "!="):
        assert shape(expr_of(f"a {op} b")) == f"({op} a b)"


def test_call_in_expression():
    assert shape(expr_of("f(1) + g(2, 3) * 4")) == "(+ f(1) (* g(2, 3) 4))"


def test_nested_call_arguments():
    assert shape(expr_of("f(g(1), h(x + 1, 2))")) == "f(g(1), h((+ x 1), 2))"


def test_literal_types():
    assert (expr_of("5").type_name, expr_of("5").value) == ("int", "5")
    assert (expr_of("2.5").type_name, expr_of("2.5").value) == ("float", "2.5")
    assert (expr_of("'a'").type_name, expr_of("'a'").value) == ("char", "'a'")
    assert (expr_of("true").type_name, expr_of("true").value) == ("bool", "true")
    assert (expr_of("false").type_name, expr_of("false").value) == ("bool", "false")


# ------------------------------------------------- D-004: chains collapse

def test_single_operand_levels_collapse_to_the_operand():
    assert isinstance(expr_of("5"), Literal)
    assert isinstance(expr_of("x"), Identifier)
    assert isinstance(expr_of("(x)"), Identifier)
    assert isinstance(expr_of("f(1)"), Call)


def test_collapsed_tree_text_has_no_wrapper_levels():
    text = tree_to_text(parse_ok("int main() { return 5; }"))
    assert text.splitlines() == [
        "Program",
        "  FunctionDecl int main",
        "    Block",
        "      Return",
        "        Literal 5 (int)",
    ]


# ------------------------------------------------------------ positions

def test_nodes_record_line_and_col():
    tree = parse_ok("int a;\n\nint f() {\n    return a + 1;\n}\n")
    func = tree.items[1]
    ret = func.body.statements[0]
    assert (tree.items[0].line, tree.items[0].col) == (1, 1)
    assert (func.line, func.col) == (3, 1)
    assert (ret.line, ret.col) == (4, 5)
    assert (ret.value.line, ret.value.col) == (4, 14)   # the `+` operator token


# ----------------------------------------------------- label and children

def test_every_node_has_label_and_children():
    lit = Literal(value="1", type_name="int", line=1, col=1)
    ident = Identifier(name="x", line=1, col=1)
    call = Call(name="f", args=[lit], line=1, col=1)
    block = Block(statements=[], line=1, col=1)
    assign = Assign(name="x", value=lit, line=1, col=1)
    decl = VarDecl(type_name="int", name="x", init=lit, is_const=True, line=1, col=1)
    nodes = [
        Program(items=[decl], line=1, col=1),
        FunctionDecl(return_type="int", name="f", params=[], body=block, line=1, col=1),
        Param(type_name="int", name="p", line=1, col=1),
        decl, block, assign,
        If(condition=ident, then_block=block, else_branch=None, line=1, col=1),
        While(condition=ident, body=block, line=1, col=1),
        For(init=None, condition=ident, update=None, body=block, line=1, col=1),
        Return(value=lit, line=1, col=1),
        CallStmt(call=call, line=1, col=1),
        BinaryOp(op="+", left=lit, right=ident, line=1, col=1),
        UnaryOp(op="-", operand=lit, line=1, col=1),
        lit, ident, call,
    ]
    for node in nodes:
        assert isinstance(node, Node)
        assert isinstance(node.label(), str) and node.label()
        assert isinstance(node.children(), list)
        assert all(isinstance(c, Node) for c in node.children())


def test_labels():
    lit = Literal(value="10", type_name="int", line=1, col=1)
    assert lit.label() == "Literal 10 (int)"
    assert Identifier(name="x", line=1, col=1).label() == "Identifier x"
    assert Call(name="f", args=[], line=1, col=1).label() == "Call f"
    assert BinaryOp(op="+", left=lit, right=lit, line=1, col=1).label() == "BinaryOp +"
    assert UnaryOp(op="!", operand=lit, line=1, col=1).label() == "UnaryOp !"
    assert Assign(name="x", value=lit, line=1, col=1).label() == "Assign x"
    assert Param(type_name="int", name="n", line=1, col=1).label() == "Param int n"
    assert VarDecl(type_name="int", name="L", init=None, is_const=True,
                   line=1, col=1).label() == "VarDecl const int L"
    assert VarDecl(type_name="bool", name="b", init=None, is_const=False,
                   line=1, col=1).label() == "VarDecl bool b"


def test_children_skip_missing_optional_parts():
    ident = Identifier(name="x", line=1, col=1)
    block = Block(statements=[], line=1, col=1)
    loop = For(init=None, condition=ident, update=None, body=block, line=1, col=1)
    assert loop.children() == [ident, block]
    cond = If(condition=ident, then_block=block, else_branch=None, line=1, col=1)
    assert cond.children() == [ident, block]
    decl = VarDecl(type_name="int", name="x", init=None, is_const=False, line=1, col=1)
    assert decl.children() == []


def test_annotations_default_to_none():
    ident = Identifier(name="x", line=1, col=1)
    assert ident.expr_type is None and ident.tac_name is None
    assert Block(statements=[], line=1, col=1).scope_id is None


# ------------------------------------------------------------- exports

def test_tree_to_text_for_if_else_if():
    tree = parse_ok(
        "int f(int a) { if (a) { return 1; } else if (a) { return 2; } return 3; }")
    lines = tree_to_text(tree).splitlines()
    assert lines[0] == "Program"
    assert "  FunctionDecl int f" in lines
    assert "    Param int a" in lines
    assert lines.count("      If") == 1       # the outer if, inside the function Block
    assert lines.count("        If") == 1     # the else-if, one level deeper


def test_tree_to_dot_has_nodes_and_edges():
    dot = tree_to_dot(parse_ok("int main() { return 1 + 2; }"))
    assert dot.startswith("digraph")
    assert "BinaryOp +" in dot and "Literal 1 (int)" in dot
    assert dot.count("->") == dot.count("[label=") - 1   # a tree: nodes minus one edges


def test_tree_to_dot_escapes_quotes():
    dot = tree_to_dot(parse_ok("char c = '\"';"))
    assert '\\"' in dot or "&quot;" in dot


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz `dot` not installed")
def test_export_png_writes_a_file(tmp_path):
    target = tmp_path / "tree.png"
    export_png(parse_ok("int main() { return 1; }"), str(target))
    assert target.exists() and target.stat().st_size > 0
    assert target.read_bytes()[:4] == b"\x89PNG"


def test_export_png_reports_missing_dot(tmp_path, monkeypatch):
    monkeypatch.setattr("src.tree_export.shutil.which", lambda name: None)
    with pytest.raises(RuntimeError, match="dot"):
        export_png(parse_ok("int main() { return 1; }"), str(tmp_path / "t.png"))


# ------------------------------------------------------- whole programs

def test_spec_section_14_sample_shape():
    tree = parse_ok(SPEC_SAMPLE.read_text(encoding="utf-8"))
    names = [(type(i).__name__, i.name) for i in tree.items]
    assert names == [("VarDecl", "LIMIT"), ("FunctionDecl", "square"),
                     ("FunctionDecl", "sumSquares"), ("FunctionDecl", "average"),
                     ("FunctionDecl", "main")]
    main = tree.items[4]
    kinds = [type(s).__name__ for s in main.body.statements]
    assert kinds == ["VarDecl", "VarDecl", "If", "For", "Return"]
    big = main.body.statements[1]
    assert shape(big.init) == "(&& (> r 100) (!= LIMIT 0))"
    if_stmt = main.body.statements[2]
    assert isinstance(if_stmt.else_branch, If)
    assert isinstance(if_stmt.else_branch.else_branch, Block)
    loop = main.body.statements[3]
    assert isinstance(loop.init, VarDecl) and loop.init.name == "k"
    average = tree.items[3]
    assert [p.name for p in average.params] == ["a", "b"]
    total = tree.items[2].body.statements[2].body.statements[0]
    assert shape(total.value) == "(+ total square(i))"


@pytest.mark.parametrize(
    "path", sorted((ROOT / "tests" / "valid").glob("*.sl")), ids=lambda p: p.name)
def test_every_valid_program_parses_without_errors(path):
    tree, errors = parse_source(path.read_text(encoding="utf-8"))
    assert [e.format() for e in errors.all()] == []
    assert isinstance(tree, Program)


# ------------------------------------------- Phase 2 stopgap on bad input

def test_syntax_error_is_reported_not_raised():
    tree, errors = parse_source("int main() { int x = ; return 0; }")
    assert isinstance(tree, Program)
    assert errors.has_kind("Syntax")
    first = errors.all()[0]
    assert (first.kind, first.line) == ("Syntax", 1)


def test_missing_semicolon_message_format():
    _, errors = parse_source("int main() {\n  int x = 1\n}\n")
    assert errors.all()[0].format() == (
        "[Syntax Error] Line 3, Col 1: Expected ';' but found '}'")


def test_invalid_tokens_are_skipped_silently():
    tree, errors = parse_source("int main() { int x = 1 @ ; return x; }")
    assert [e.kind for e in errors.all()] == ["Lexical"]
    assert isinstance(tree.items[0], FunctionDecl)


@pytest.mark.parametrize("source", [
    "", "int", "int main(", "int main() {", "}", "if", "int x = ", "((((",
    "int f() { return ; }", "int f( { }", "const", "int 5;",
])
def test_garbage_never_crashes(source):
    tree, _ = parse_source(source)
    assert isinstance(tree, Program)


# ------------------------------------------------------------------ CLI

def test_cli_tree_prints_section(tmp_path, capsys):
    program = tmp_path / "p.sl"
    program.write_text("int main() { return 1 + 2 * 3; }\n", encoding="utf-8")
    code = run(str(program), {"--tree"})
    out = capsys.readouterr().out
    assert code == 0
    assert "== PARSE TREE ==" in out
    assert "BinaryOp +" in out and "BinaryOp *" in out
    assert out.index("== TOKENS ==") < out.index("== PARSE TREE ==") < out.index("== ERRORS ==")


def test_cli_tree_with_syntax_error_exit_code(tmp_path, capsys):
    program = tmp_path / "bad.sl"
    program.write_text("int main() { int x = 1 }\n", encoding="utf-8")
    code = run(str(program), {"--tree"})
    out = capsys.readouterr().out
    assert code == 1
    assert "[Syntax Error] Line 1" in out


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz `dot` not installed")
def test_cli_tree_png_writes_file(tmp_path, capsys):
    program = tmp_path / "p.sl"
    program.write_text("int main() { return 1; }\n", encoding="utf-8")
    png = tmp_path / "out.png"
    code = run(str(program), {"--tree-png"}, png_path=str(png))
    assert code == 0 and png.exists() and png.stat().st_size > 0
    assert str(png) in capsys.readouterr().out


def test_cli_tree_png_missing_dot_gives_clear_message(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("src.tree_export.shutil.which", lambda name: None)
    program = tmp_path / "p.sl"
    program.write_text("int main() { return 1; }\n", encoding="utf-8")
    code = run(str(program), {"--tree-png"}, png_path=str(tmp_path / "o.png"))
    captured = capsys.readouterr()
    assert code == 2
    assert "dot" in captured.err and "graphviz" in captured.err.lower()


# ------------------------------------- D-020: INVALID tokens and follow-on errors

def kinds_and_lines(errors: ErrorCollector) -> list[tuple[str, int]]:
    """Short summary of collected errors: (kind, line) in report order."""
    return [(e.kind, e.line) for e in errors.all()]


def test_glued_number_gives_one_lexical_error_and_no_syntax_error():
    _, errors = parse_source("int g = 9abc;\n")
    assert kinds_and_lines(errors) == [("Lexical", 1)]


def test_unterminated_char_literal_gives_no_follow_on_syntax_error():
    # The INVALID token `'a;` swallows the `;`, so the next token is the closing brace.
    _, errors = parse_source("int main() {\n  char h = 'a;\n}\n")
    assert kinds_and_lines(errors) == [("Lexical", 2)]


def test_invalid_token_between_operands_gives_no_follow_on_syntax_error():
    # `5 @ 1`: the parser would otherwise complain about the `1` after the `@`.
    _, errors = parse_source("int main() { int a = 5 @ 1; return a; }")
    assert kinds_and_lines(errors) == [("Lexical", 1)]


def test_syntax_error_far_from_an_invalid_token_is_reported():
    _, errors = parse_source("int main() {\n  int x = 1\n  return x; @\n}\n")
    assert kinds_and_lines(errors) == [("Lexical", 3), ("Syntax", 3)]


def test_invalid_token_at_end_of_file_is_silent():
    _, errors = parse_source("int main() { return 1; } /*")
    assert kinds_and_lines(errors) == [("Lexical", 1)]


def test_valid_program_with_invalid_token_keeps_earlier_items():
    tree, errors = parse_source("int a = 1;\nint b = 9abc;\n")
    assert [i.name for i in tree.items] == ["a"]
    assert kinds_and_lines(errors) == [("Lexical", 2)]


def test_cli_invalid_lexical_sample_has_no_follow_on_syntax_error(capsys):
    code = run("samples/invalid_lexical.sl", {"--tree"})
    out = capsys.readouterr().out
    assert code == 1
    assert "[Syntax Error]" not in out
