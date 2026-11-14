"""Tests for src/tokens.py (interfaces.md: tokens.py)."""
import dataclasses

import pytest

from src.tokens import Token, TokenType


def test_token_type_has_all_members():
    """SPEC section 5 token classes, plus EOF and INVALID."""
    names = {t.name for t in TokenType}
    assert names == {
        "KEYWORD", "IDENTIFIER", "INT_LIT", "FLOAT_LIT", "CHAR_LIT",
        "OPERATOR", "DELIMITER", "EOF", "INVALID",
    }


def test_token_fields():
    tok = Token(TokenType.KEYWORD, "int", 1, 1)
    assert tok.type is TokenType.KEYWORD
    assert tok.lexeme == "int"
    assert tok.line == 1
    assert tok.col == 1


def test_token_equality():
    a = Token(TokenType.IDENTIFIER, "x", 2, 5)
    b = Token(TokenType.IDENTIFIER, "x", 2, 5)
    c = Token(TokenType.IDENTIFIER, "x", 2, 6)
    assert a == b
    assert a != c


def test_token_is_frozen():
    tok = Token(TokenType.INT_LIT, "42", 3, 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        tok.lexeme = "43"


def test_token_is_hashable():
    tok = Token(TokenType.EOF, "", 9, 1)
    assert tok in {tok}
