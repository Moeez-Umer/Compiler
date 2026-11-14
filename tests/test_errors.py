"""Tests for src/errors.py (SPEC section 9, interfaces.md: errors.py)."""
import dataclasses

import pytest

from src.errors import CompilerError, ErrorCollector


def test_format_lexical():
    err = CompilerError("Lexical", 5, 12, "Invalid character '@'")
    assert err.format() == "[Lexical Error] Line 5, Col 12: Invalid character '@'"


def test_format_syntax():
    err = CompilerError("Syntax", 9, 1, "Expected ';' but found '}'")
    assert err.format() == "[Syntax Error] Line 9, Col 1: Expected ';' but found '}'"


def test_format_semantic():
    err = CompilerError("Semantic", 14, 5, "Cannot assign float to int variable 'x'")
    assert err.format() == (
        "[Semantic Error] Line 14, Col 5: Cannot assign float to int variable 'x'"
    )


def test_compiler_error_is_frozen():
    err = CompilerError("Syntax", 1, 1, "m")
    with pytest.raises(dataclasses.FrozenInstanceError):
        err.line = 2


def test_empty_collector():
    ec = ErrorCollector()
    assert ec.has_errors() is False
    assert ec.has_kind("Lexical") is False
    assert ec.all() == []


def test_has_errors_after_report():
    ec = ErrorCollector()
    ec.report("Syntax", 1, 1, "x")
    assert ec.has_errors() is True


def test_has_kind():
    ec = ErrorCollector()
    ec.report("Syntax", 1, 1, "x")
    assert ec.has_kind("Syntax") is True
    assert ec.has_kind("Lexical") is False
    assert ec.has_kind("Semantic") is False


def test_all_groups_by_kind_then_sorts_by_line_col():
    ec = ErrorCollector()
    # Reported in scrambled order on purpose.
    ec.report("Semantic", 1, 1, "sem-early")
    ec.report("Syntax", 8, 2, "syn-late")
    ec.report("Lexical", 20, 1, "lex-late")
    ec.report("Syntax", 3, 9, "syn-early")
    ec.report("Lexical", 2, 4, "lex-early")
    ec.report("Semantic", 7, 1, "sem-late")
    assert [e.message for e in ec.all()] == [
        "lex-early", "lex-late",
        "syn-early", "syn-late",
        "sem-early", "sem-late",
    ]


def test_all_sorts_by_col_when_line_equal():
    ec = ErrorCollector()
    ec.report("Lexical", 4, 9, "b")
    ec.report("Lexical", 4, 2, "a")
    assert [e.message for e in ec.all()] == ["a", "b"]


def test_all_keeps_report_order_for_equal_positions():
    ec = ErrorCollector()
    ec.report("Syntax", 4, 2, "first")
    ec.report("Syntax", 4, 2, "second")
    assert [e.message for e in ec.all()] == ["first", "second"]


def test_all_returns_a_copy():
    ec = ErrorCollector()
    ec.report("Syntax", 1, 1, "x")
    ec.all().clear()
    assert len(ec.all()) == 1


def test_unknown_kind_is_rejected():
    ec = ErrorCollector()
    with pytest.raises(ValueError):
        ec.report("Bogus", 1, 1, "x")
    assert ec.has_errors() is False
