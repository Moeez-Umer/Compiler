"""Tests for the lexer (SPEC section 5, interfaces.md: lexer.py)."""
from pathlib import Path

import pytest

from src.errors import ErrorCollector
from src.lexer import tokenize
from src.tokens import Token, TokenType

T = TokenType


def lex(source):
    """Tokenize and return (tokens, errors)."""
    errors = ErrorCollector()
    return tokenize(source, errors), errors


def kinds(tokens):
    """Token types without the final EOF."""
    return [t.type for t in tokens[:-1]]


def lexemes(tokens):
    """Lexemes without the final EOF."""
    return [t.lexeme for t in tokens[:-1]]


# ---------- basics ----------

def test_empty_input_gives_only_eof():
    tokens, errors = lex("")
    assert tokens == [Token(T.EOF, "", 1, 1)]
    assert not errors.has_errors()


def test_whitespace_only_gives_only_eof():
    tokens, _ = lex("  \t\n\n  ")
    assert [t.type for t in tokens] == [T.EOF]
    assert (tokens[0].line, tokens[0].col) == (3, 3)


# ---------- each token class ----------

@pytest.mark.parametrize("word", [
    "int", "float", "char", "bool", "const", "if", "else", "for",
    "while", "return", "true", "false"])
def test_keywords(word):
    tokens, errors = lex(word)
    assert tokens[0] == Token(T.KEYWORD, word, 1, 1)
    assert not errors.has_errors()


@pytest.mark.parametrize("name", ["x", "_a", "abc123", "A_b_9", "integer", "iff", "True"])
def test_identifiers_including_keyword_prefixes(name):
    tokens, _ = lex(name)
    assert tokens[0] == Token(T.IDENTIFIER, name, 1, 1)


def test_int_literal():
    tokens, _ = lex("0 42 007")
    assert kinds(tokens) == [T.INT_LIT] * 3
    assert lexemes(tokens) == ["0", "42", "007"]


def test_float_literal():
    tokens, _ = lex("3.14 0.5")
    assert kinds(tokens) == [T.FLOAT_LIT, T.FLOAT_LIT]
    assert lexemes(tokens) == ["3.14", "0.5"]


@pytest.mark.parametrize("lit", [r"'a'", r"'\n'", r"'\t'", r"'\\'", r"'\''", r"'\0'", "' '", "'9'"])
def test_char_literals(lit):
    tokens, errors = lex(lit)
    assert tokens[0] == Token(T.CHAR_LIT, lit, 1, 1)
    assert not errors.has_errors()


@pytest.mark.parametrize("op", ["+", "-", "*", "/", "%", "=", "<", ">", "!"])
def test_single_char_operators(op):
    tokens, _ = lex(op)
    assert tokens[0] == Token(T.OPERATOR, op, 1, 1)


@pytest.mark.parametrize("op", ["==", "!=", "<=", ">=", "&&", "||"])
def test_two_char_operators(op):
    tokens, errors = lex(op)
    assert tokens[0] == Token(T.OPERATOR, op, 1, 1)
    assert len(tokens) == 2
    assert not errors.has_errors()


@pytest.mark.parametrize("d", list("(){};,"))
def test_delimiters(d):
    tokens, _ = lex(d)
    assert tokens[0] == Token(T.DELIMITER, d, 1, 1)


# ---------- longest match ----------

def test_le_vs_lt():
    assert lexemes(lex("a <= b")[0]) == ["a", "<=", "b"]
    assert lexemes(lex("a < b")[0]) == ["a", "<", "b"]
    assert lexemes(lex("a < = b")[0]) == ["a", "<", "=", "b"]


def test_ge_vs_gt():
    assert lexemes(lex("a>=b")[0]) == ["a", ">=", "b"]
    assert lexemes(lex("a>b")[0]) == ["a", ">", "b"]


def test_eq_vs_assign():
    assert lexemes(lex("x == 1")[0]) == ["x", "==", "1"]
    assert lexemes(lex("x = 1")[0]) == ["x", "=", "1"]


def test_not_vs_not_equal():
    assert lexemes(lex("!a")[0]) == ["!", "a"]
    assert lexemes(lex("a!=b")[0]) == ["a", "!=", "b"]


def test_triple_equals_is_eq_then_assign():
    assert lexemes(lex("===")[0]) == ["==", "="]


def test_and_or_operators():
    tokens, errors = lex("a && b || c")
    assert lexemes(tokens) == ["a", "&&", "b", "||", "c"]
    assert not errors.has_errors()


def test_no_spaces_expression():
    tokens, _ = lex("x=a+1*2;")
    assert lexemes(tokens) == ["x", "=", "a", "+", "1", "*", "2", ";"]


def test_float_vs_int_then_identifier_boundary():
    assert kinds(lex("1.5+2")[0]) == [T.FLOAT_LIT, T.OPERATOR, T.INT_LIT]


# ---------- positions ----------

def test_columns_on_one_line():
    tokens, _ = lex("int x = 10;")
    assert [(t.lexeme, t.line, t.col) for t in tokens[:-1]] == [
        ("int", 1, 1), ("x", 1, 5), ("=", 1, 7), ("10", 1, 9), (";", 1, 11)]


def test_multi_line_columns_reset():
    tokens, _ = lex("a\n  bb\n\tc")
    assert [(t.lexeme, t.line, t.col) for t in tokens[:-1]] == [
        ("a", 1, 1), ("bb", 2, 3), ("c", 3, 2)]


def test_eof_position():
    tokens, _ = lex("a\nb")
    assert tokens[-1] == Token(T.EOF, "", 2, 2)


def test_crlf_line_endings():
    tokens, _ = lex("a\r\nb")
    assert [(t.lexeme, t.line, t.col) for t in tokens[:-1]] == [("a", 1, 1), ("b", 2, 1)]


# ---------- comments ----------

def test_line_comment_is_skipped():
    tokens, errors = lex("a // hello @ #\nb")
    assert lexemes(tokens) == ["a", "b"]
    assert tokens[1].line == 2
    assert not errors.has_errors()


def test_line_comment_at_end_without_newline():
    assert lexemes(lex("a // end")[0]) == ["a"]


def test_block_comment_is_skipped():
    tokens, errors = lex("a /* x @ y */ b")
    assert [(t.lexeme, t.col) for t in tokens[:-1]] == [("a", 1), ("b", 15)]
    assert not errors.has_errors()


def test_multi_line_block_comment_updates_line_and_col():
    tokens, _ = lex("a /* one\ntwo\n  three */ b")
    assert (tokens[1].lexeme, tokens[1].line, tokens[1].col) == ("b", 3, 12)


def test_block_comments_do_not_nest():
    tokens, _ = lex("/* /* */ x */")
    assert lexemes(tokens) == ["x", "*", "/"]


def test_slash_alone_is_division():
    assert lexemes(lex("a / b")[0]) == ["a", "/", "b"]


def test_empty_block_comment():
    tokens, errors = lex("/**/x")
    assert lexemes(tokens) == ["x"]
    assert not errors.has_errors()


# ---------- invalid cases (SPEC section 5), one test each ----------

def assert_one_invalid(source, lexeme, line, col, message_part):
    """Exactly one INVALID token and one Lexical error, then EOF."""
    tokens, errors = lex(source)
    invalid = [t for t in tokens if t.type is T.INVALID]
    assert invalid == [Token(T.INVALID, lexeme, line, col)]
    errs = errors.all()
    assert len(errs) == 1
    assert (errs[0].kind, errs[0].line, errs[0].col) == ("Lexical", line, col)
    assert message_part in errs[0].message
    assert tokens[-1].type is T.EOF


@pytest.mark.parametrize("ch", list("@#$~^?:.[]\\`") + ["é"])
def test_invalid_unknown_character(ch):
    assert_one_invalid(f"x {ch} y", ch, 1, 3, "Invalid character")


def test_invalid_message_format_matches_spec():
    _, errors = lex("a\n  @")
    assert errors.all()[0].format() == "[Lexical Error] Line 2, Col 3: Invalid character '@'"


def test_invalid_single_ampersand():
    assert_one_invalid("a & b", "&", 1, 3, "Invalid character '&'")


def test_invalid_single_pipe():
    assert_one_invalid("a | b", "|", 1, 3, "Invalid character '|'")


def test_invalid_malformed_number_two_dots():
    assert_one_invalid("x = 3.4.5;", "3.4.5", 1, 5, "Malformed number")


def test_invalid_malformed_number_trailing_dot():
    assert_one_invalid("x = 3.;", "3.", 1, 5, "Malformed number")


def test_invalid_malformed_number_leading_dot():
    assert_one_invalid("x = .5;", ".5", 1, 5, "Malformed number")


def test_invalid_number_glued_to_letters():
    assert_one_invalid("x = 9abc;", "9abc", 1, 5, "letters")


def test_invalid_char_unterminated():
    assert_one_invalid("c = 'a", "'a", 1, 5, "Unterminated char")


def test_invalid_char_unterminated_stops_at_end_of_line():
    tokens, errors = lex("c = 'a\nint")
    assert [t.lexeme for t in tokens if t.type is T.INVALID] == ["'a"]
    assert tokens[-2] == Token(T.KEYWORD, "int", 2, 1)
    assert len(errors.all()) == 1


def test_invalid_char_lone_quote_at_end():
    assert_one_invalid("'", "'", 1, 1, "Unterminated char")


def test_invalid_char_empty():
    assert_one_invalid("c = '';", "''", 1, 5, "Empty char")


def test_invalid_char_too_long():
    assert_one_invalid("c = 'ab';", "'ab'", 1, 5, "too long")


def test_invalid_char_bad_escape():
    assert_one_invalid(r"c = '\q';", r"'\q'", 1, 5, "escape")


def test_invalid_unterminated_block_comment_reports_start_line():
    tokens, errors = lex("a\n  /* never closed\nmore\n")
    assert [t.lexeme for t in tokens if t.type is T.INVALID] == ["/*"]
    err = errors.all()[0]
    assert (err.kind, err.line, err.col) == ("Lexical", 2, 3)
    assert "Unterminated block comment" in err.message
    assert tokens[-1].type is T.EOF


# ---------- never stop at the first error ----------

def test_many_errors_are_all_reported_and_lexing_continues():
    tokens, errors = lex("int a = 3.4.5;\nint b = @;\nint c = 1 & 2;\nint d = 5;")
    assert len(errors.all()) == 3
    assert [e.line for e in errors.all()] == [1, 2, 3]
    assert lexemes(tokens)[-5:] == ["int", "d", "=", "5", ";"]
    assert tokens[-1].type is T.EOF


def test_only_invalid_input_still_ends_with_eof():
    tokens, errors = lex("@#$")
    assert [t.type for t in tokens] == [T.INVALID] * 3 + [T.EOF]
    assert len(errors.all()) == 3


def test_adjacent_invalid_after_valid_token():
    tokens, _ = lex("a@b")
    assert kinds(tokens) == [T.IDENTIFIER, T.INVALID, T.IDENTIFIER]


@pytest.mark.parametrize("source", ["'", "/*", "3.", "&", "'\\", "\x00", "'\\'", "9", "\"abc\""])
def test_never_crashes_on_odd_input(source):
    tokens, _ = lex(source)
    assert tokens[-1].type is T.EOF


# ---------- the .sl files in tests/ and samples/ ----------

ROOT = Path(__file__).resolve().parent.parent
INVALID_FILES = sorted((ROOT / "tests" / "invalid").glob("lexical_*.sl"))
VALID_FILES = sorted((ROOT / "tests" / "valid").glob("*.sl")) + [ROOT / "samples" / "valid_all_tokens.sl"]


def read_expectations(text):
    """Parse leading `// EXPECT: Lexical <line> <substring>` lines (SPEC section 13)."""
    found = []
    for row in text.splitlines():
        if not row.startswith("// EXPECT:"):
            break
        kind, line, message = row[len("// EXPECT:"):].strip().split(" ", 2)
        found.append((kind, int(line), message))
    return found


def test_invalid_files_exist():
    assert len(INVALID_FILES) >= 12


@pytest.mark.parametrize("path", INVALID_FILES, ids=lambda p: p.name)
def test_invalid_file_matches_expect_lines(path):
    text = path.read_text(encoding="utf-8")
    tokens, errors = lex(text)
    actual = [(e.kind, e.line, e.message) for e in errors.all()]
    expected = read_expectations(text)
    assert len(actual) == len(expected)
    for (kind, line, msg), (a_kind, a_line, a_msg) in zip(expected, actual):
        assert (kind, line) == (a_kind, a_line)
        assert msg in a_msg
    assert tokens[-1].type is T.EOF


@pytest.mark.parametrize("path", VALID_FILES, ids=lambda p: p.name)
def test_valid_files_have_no_lexical_errors(path):
    tokens, errors = lex(path.read_text(encoding="utf-8"))
    assert not errors.has_errors()
    assert T.INVALID not in [t.type for t in tokens]
    assert len(tokens) > 10


def test_valid_dir_has_token_samples():
    assert len(VALID_FILES) >= 3
