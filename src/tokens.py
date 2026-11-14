"""Token definitions shared by the lexer and the parser (interfaces.md: tokens.py)."""
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """Token classes from SPEC section 5, plus EOF (end marker) and INVALID (lexical error)."""

    KEYWORD = auto()
    IDENTIFIER = auto()
    INT_LIT = auto()
    FLOAT_LIT = auto()
    CHAR_LIT = auto()
    OPERATOR = auto()
    DELIMITER = auto()
    EOF = auto()
    INVALID = auto()


@dataclass(frozen=True)
class Token:
    """One lexical unit. Line and col both start at 1 (SPEC section 5).

    Frozen so a token can never change after the lexer creates it.
    """

    type: TokenType
    lexeme: str
    line: int
    col: int
