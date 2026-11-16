"""Tests for src/symbol_table.py (SPEC sections 8 and 10, interfaces.md: symbol_table.py)."""
import pytest

from src.symbol_table import Symbol, SymbolTable


def test_symbol_dataclass_fields_and_defaults():
    sym = Symbol(name="x", type_name="int", kind="var", scope_level=0, line=4)
    assert sym.name == "x"
    assert sym.type_name == "int"
    assert sym.kind == "var"
    assert sym.scope_level == 0
    assert sym.line == 4
    assert sym.params is None
    assert sym.tac_name == ""

    sym.tac_name = "x_1"
    assert sym.tac_name == "x_1"

    fn = Symbol(
        name="average",
        type_name="float",
        kind="func",
        scope_level=0,
        line=10,
        params=[("int", "a"), ("int", "b")],
        tac_name="average",
    )
    assert fn.params == [("int", "a"), ("int", "b")]
    assert fn.tac_name == "average"


def test_scope_ids_and_current_level():
    table = SymbolTable()
    assert table.current_level() == -1
    assert table.lookup("x") is None
    assert table.lookup_current("x") is None
    assert table.dump() == ""

    s0 = table.enter_scope("global")
    assert s0 == 0
    assert table.current_level() == 0

    s1 = table.enter_scope("function f")
    assert s1 == 1
    assert table.current_level() == 1

    s2 = table.enter_scope("block")
    assert s2 == 2
    assert table.current_level() == 2

    table.exit_scope()
    assert table.current_level() == 1

    s3 = table.enter_scope("block")
    assert s3 == 3
    assert table.current_level() == 2

    table.exit_scope()
    table.exit_scope()
    assert table.current_level() == 0

    table.exit_scope()
    assert table.current_level() == -1


def test_declare_or_exit_without_active_scope_raises():
    table = SymbolTable()
    with pytest.raises(RuntimeError):
        table.exit_scope()
    with pytest.raises(RuntimeError):
        table.declare(Symbol("x", "int", "var", 0, 1))

    table.enter_scope("global")
    table.exit_scope()
    with pytest.raises(RuntimeError):
        table.exit_scope()


def test_declare_and_lookup_in_single_scope():
    table = SymbolTable()
    table.enter_scope("global")

    limit = Symbol("LIMIT", "int", "const", 0, 1)
    count = Symbol("count", "int", "var", 0, 2)
    sq = Symbol("square", "int", "func", 0, 4, params=[("int", "x")])

    assert table.declare(limit) is True
    assert table.declare(count) is True
    assert table.declare(sq) is True

    assert table.lookup("LIMIT") is limit
    assert table.lookup_current("LIMIT") is limit
    assert table.lookup("count") is count
    assert table.lookup("square") is sq
    assert table.lookup("undeclared") is None
    assert table.lookup_current("undeclared") is None


def test_redeclaration_in_same_scope_returns_false_and_keeps_original():
    table = SymbolTable()
    table.enter_scope("global")

    first = Symbol("x", "int", "var", 0, 2)
    second = Symbol("x", "float", "var", 0, 5)

    assert table.declare(first) is True
    assert table.declare(second) is False
    assert table.lookup("x") is first
    assert table.lookup_current("x") is first


def test_shadowing_in_inner_scope():
    table = SymbolTable()
    table.enter_scope("global")
    outer_x = Symbol("x", "int", "var", 0, 1)
    assert table.declare(outer_x) is True

    table.enter_scope("function main")
    mid_x = Symbol("x", "float", "var", 1, 4)
    assert table.declare(mid_x) is True
    assert table.lookup("x") is mid_x
    assert table.lookup_current("x") is mid_x

    table.enter_scope("block")
    inner_x = Symbol("x", "char", "var", 2, 6)
    assert table.declare(inner_x) is True
    assert table.lookup("x") is inner_x
    assert table.lookup_current("x") is inner_x

    table.exit_scope()
    assert table.lookup("x") is mid_x
    assert table.lookup_current("x") is mid_x

    table.exit_scope()
    assert table.lookup("x") is outer_x
    assert table.lookup_current("x") is outer_x


def test_lookup_walks_outward_and_ignores_exited_siblings():
    table = SymbolTable()
    table.enter_scope("global")
    limit = Symbol("LIMIT", "int", "const", 0, 1)
    func = Symbol("sumSquares", "int", "func", 0, 7, params=[("int", "n")])
    table.declare(limit)
    table.declare(func)

    table.enter_scope("function sumSquares")
    param_n = Symbol("n", "int", "param", 1, 7)
    total = Symbol("total", "int", "var", 1, 8)
    table.declare(param_n)
    table.declare(total)

    table.enter_scope("block")
    temp = Symbol("temp", "int", "var", 2, 10)
    table.declare(temp)
    assert table.lookup("temp") is temp
    table.exit_scope()

    table.enter_scope("block")
    step = Symbol("step", "int", "var", 2, 14)
    table.declare(step)

    # Inside the second block: finds level 2, level 1, and level 0 symbols,
    # but NOT `temp` from the already-exited first block.
    assert table.lookup("step") is step
    assert table.lookup("n") is param_n
    assert table.lookup("total") is total
    assert table.lookup("LIMIT") is limit
    assert table.lookup("sumSquares") is func
    assert table.lookup("temp") is None


def test_lookup_current_ignores_outer_scopes():
    table = SymbolTable()
    table.enter_scope("global")
    g = Symbol("g", "int", "var", 0, 1)
    table.declare(g)

    table.enter_scope("function f")
    p = Symbol("p", "int", "param", 1, 3)
    table.declare(p)

    table.enter_scope("block")
    b = Symbol("b", "bool", "var", 2, 5)
    table.declare(b)

    assert table.lookup_current("b") is b
    assert table.lookup_current("p") is None
    assert table.lookup_current("g") is None
    assert table.lookup("p") is p
    assert table.lookup("g") is g

    table.exit_scope()
    assert table.lookup_current("p") is p
    assert table.lookup_current("g") is None
    assert table.lookup_current("b") is None


def test_dump_after_scopes_were_exited_three_scope_example():
    table = SymbolTable()

    s0 = table.enter_scope("global")
    assert s0 == 0
    table.declare(Symbol("LIMIT", "int", "const", 0, 1))
    table.declare(
        Symbol("sumSquares", "int", "func", 0, 7, params=[("int", "n")])
    )
    table.declare(Symbol("main", "int", "func", 0, 20, params=[]))

    s1 = table.enter_scope("function sumSquares")
    assert s1 == 1
    table.declare(Symbol("n", "int", "param", 1, 7))
    table.declare(Symbol("total", "int", "var", 1, 8))
    table.declare(Symbol("i", "int", "var", 1, 9))

    s2 = table.enter_scope("block")
    assert s2 == 2
    table.declare(Symbol("step", "int", "var", 2, 11))

    # Exit inner scopes before dumping to verify exited scope history is preserved.
    table.exit_scope()
    table.exit_scope()
    table.exit_scope()

    expected = (
        "Scope 0 (global)\n"
        "  NAME        TYPE  KIND   LEVEL  LINE  PARAMS\n"
        "  LIMIT       int   const      0     1  -\n"
        "  sumSquares  int   func       0     7  (int n)\n"
        "  main        int   func       0    20  ()\n"
        "\n"
        "Scope 1 (function sumSquares)\n"
        "  NAME   TYPE  KIND   LEVEL  LINE  PARAMS\n"
        "  n      int   param      1     7  -\n"
        "  total  int   var        1     8  -\n"
        "  i      int   var        1     9  -\n"
        "\n"
        "Scope 2 (block)\n"
        "  NAME  TYPE  KIND  LEVEL  LINE  PARAMS\n"
        "  step  int   var       2    11  -"
    )
    assert table.dump() == expected


def test_dump_empty_scope():
    table = SymbolTable()
    table.enter_scope("global")
    table.enter_scope("block")
    table.exit_scope()
    table.exit_scope()

    assert table.dump() == (
        "Scope 0 (global)\n"
        "  (empty)\n"
        "\n"
        "Scope 1 (block)\n"
        "  (empty)"
    )


def test_redeclaration_of_shadowed_name_in_same_inner_scope_returns_false():
    table = SymbolTable()
    table.enter_scope("global")
    outer = Symbol("x", "int", "var", 0, 1)
    assert table.declare(outer) is True

    table.enter_scope("function f")
    inner_first = Symbol("x", "float", "var", 1, 3)
    inner_dup = Symbol("x", "bool", "var", 1, 4)
    assert table.declare(inner_first) is True
    assert table.declare(inner_dup) is False
    assert table.lookup("x") is inner_first


def test_redeclaring_name_in_new_sibling_scope_after_exit_succeeds():
    table = SymbolTable()
    table.enter_scope("global")
    table.enter_scope("function f")

    s_b1 = table.enter_scope("block")
    k1 = Symbol("k", "int", "var", 2, 5)
    assert table.declare(k1) is True
    table.exit_scope()

    s_b2 = table.enter_scope("block")
    k2 = Symbol("k", "int", "var", 2, 9)
    assert table.declare(k2) is True
    assert table.lookup("k") is k2
    table.exit_scope()

    assert (s_b1, s_b2) == (2, 3)
    assert table.lookup("k") is None
    dumped = table.dump()
    assert "Scope 2 (block)" in dumped
    assert "Scope 3 (block)" in dumped


def test_declare_sets_symbol_scope_level_to_current_level():
    table = SymbolTable()
    table.enter_scope("global")
    g_sym = Symbol("g", "int", "var", scope_level=99, line=1)
    assert table.declare(g_sym) is True
    assert g_sym.scope_level == 0
    assert table.lookup("g").scope_level == 0

    table.enter_scope("function f")
    f_sym = Symbol("p", "int", "param", scope_level=0, line=3)
    assert table.declare(f_sym) is True
    assert f_sym.scope_level == 1
    assert table.lookup("p").scope_level == 1

    table.enter_scope("block")
    b_sym = Symbol("local", "bool", "var", scope_level=-5, line=5)
    assert table.declare(b_sym) is True
    assert b_sym.scope_level == 2
    assert table.lookup("local").scope_level == 2


def test_dump_sibling_blocks_at_same_level_with_empty_scope():
    table = SymbolTable()
    table.enter_scope("global")
    table.declare(Symbol("f", "int", "func", 0, 1, params=[("int", "x")]))

    table.enter_scope("function f")
    table.declare(Symbol("x", "int", "param", 1, 1))

    # First block at level 2 has a declaration; second sibling block at level 2 is empty.
    table.enter_scope("block")
    table.declare(Symbol("y", "int", "var", 2, 3))
    table.exit_scope()

    table.enter_scope("block")
    table.exit_scope()

    table.exit_scope()
    table.exit_scope()

    expected = (
        "Scope 0 (global)\n"
        "  NAME  TYPE  KIND  LEVEL  LINE  PARAMS\n"
        "  f     int   func      0     1  (int x)\n"
        "\n"
        "Scope 1 (function f)\n"
        "  NAME  TYPE  KIND   LEVEL  LINE  PARAMS\n"
        "  x     int   param      1     1  -\n"
        "\n"
        "Scope 2 (block)\n"
        "  NAME  TYPE  KIND  LEVEL  LINE  PARAMS\n"
        "  y     int   var       2     3  -\n"
        "\n"
        "Scope 3 (block)\n"
        "  (empty)"
    )
    assert table.dump() == expected


