"""Edge cases: odd bytes and sizes that must neither crash nor give wrong positions (D-044, D-045).

Inputs that cannot carry a `// EXPECT:` first line (empty file, BOM, CRLF, lone CR, missing final
newline) are built as bytes here and read through `read_source` like the CLI does.
"""
import pytest

from src.errors import ErrorCollector
from src.lexer import tokenize
from src.main import read_source
from tests.pipeline_helper import check_tac, compile_source

PROGRAM = "int main() {\n    return 1;\n}\n"
BAD_PROGRAM = "int main() {\n    int b = @;\n    return 1;\n}\n"


def read_bytes(tmp_path, data: bytes) -> str:
    """Write `data` to a file and read it back with the CLI's own `read_source`."""
    path = tmp_path / "input.sl"
    path.write_bytes(data)
    text = read_source(str(path))
    assert text is not None
    return text


def positions(source: str) -> list[tuple]:
    """(type, lexeme, line, col) of every token."""
    return [(t.type.name, t.lexeme, t.line, t.col) for t in tokenize(source, ErrorCollector())]


def messages(source: str) -> list[str]:
    """Formatted errors of a full compile."""
    return [e.format() for e in compile_source(source).errors]


# ------------------------------------------------------------------ empty and comment-only input

def test_empty_file(tmp_path):
    """No bytes at all: only EOF, no error, empty TAC."""
    source = read_bytes(tmp_path, b"")
    result = compile_source(source)
    assert [t.type.name for t in result.tokens] == ["EOF"]
    assert result.errors == [] and result.tac == []


@pytest.mark.parametrize("data", [b"// only a comment", b"// c\n/* b */\n", b"// c\r\n/* b\r\n */\r\n"])
def test_only_comments(tmp_path, data):
    """Comments only (with or without final newline, LF or CRLF) is an empty program."""
    result = compile_source(read_bytes(tmp_path, data))
    assert result.errors == [] and result.tac == []


# ------------------------------------------------------------------ line endings

def test_crlf_through_read_source_keeps_line_numbers(tmp_path):
    """read_source keeps `\\r\\n` (newline=''), and tokens/errors equal the LF version."""
    source = read_bytes(tmp_path, BAD_PROGRAM.replace("\n", "\r\n").encode())
    assert "\r\n" in source
    assert positions(source) == positions(BAD_PROGRAM)
    assert messages(source) == messages(BAD_PROGRAM)
    assert messages(source) == ["[Lexical Error] Line 2, Col 13: Invalid character '@'"]


def test_crlf_through_tokenize_directly():
    """tokenize on a `\\r\\n` string: one line break per pair, columns unchanged."""
    crlf = "int a;\r\nint b;\r\n"
    assert positions(crlf) == positions("int a;\nint b;\n")
    assert [t.line for t in tokenize(crlf, ErrorCollector())][-1] == 3     # EOF after two breaks


def test_crlf_inside_a_line_comment():
    """The `\\r` before the newline is part of the comment text, not a token."""
    assert positions("// c\r\nint x;") == positions("// c\nint x;")


def test_lone_cr_is_whitespace_not_a_line_break():
    """Pinned (D-045): only `\\n` ends a line, so a lone `\\r` is skipped like a space."""
    tokens = positions("int a;\rint b;")
    assert [t[2] for t in tokens] == [1] * len(tokens)                     # everything on line 1
    assert ("IDENTIFIER", "b", 1, 12) in tokens
    assert messages("int a;\rint b = @;") == ["[Lexical Error] Line 1, Col 16: Invalid character '@'"]


def test_no_trailing_newline(tmp_path):
    """A valid program without a final newline compiles; so does a last-line comment."""
    for data in (PROGRAM.rstrip("\n"), PROGRAM + "// end"):
        result = compile_source(read_bytes(tmp_path, data.encode()))
        assert result.errors == [] and result.tac is not None


# ------------------------------------------------------------------ tabs and non-ASCII

def test_tab_is_one_column():
    """D-014: a tab counts as one column."""
    assert messages("\tint x = @;") == ["[Lexical Error] Line 1, Col 10: Invalid character '@'"]


def test_non_ascii_text_inside_comments(tmp_path):
    """Non-ASCII letters are fine inside comments (UTF-8), and columns count characters."""
    data = "// héllo 日本語 ✓\n/* é */ int x = 1;\nint main() { return x; }\n".encode("utf-8")
    source = read_bytes(tmp_path, data)
    assert messages(source) == []
    assert ("IDENTIFIER", "x", 2, 13) in positions(source)


def test_non_ascii_outside_comments_is_an_error():
    """D-014: identifiers are ASCII only, so a letter such as 'é' in code is a lexical error."""
    assert messages("int é = 1;") == ["[Lexical Error] Line 1, Col 5: Invalid character 'é'"]


def test_invalid_utf8_is_a_read_error(tmp_path, capsys):
    """Not UTF-8: read_source returns None and prints one error line (exit 2 in the CLI)."""
    path = tmp_path / "bad.sl"
    path.write_bytes(b"int x; \xff\xfe")
    assert read_source(str(path)) is None
    assert capsys.readouterr().err.startswith("error: cannot read")


# ------------------------------------------------------------------ BOM (D-045)

def test_lexer_treats_bom_text_as_an_invalid_character():
    """tokenize itself never strips anything: U+FEFF in the text is an invalid character."""
    assert messages("\ufeffint a;") == ["[Lexical Error] Line 1, Col 1: Invalid character '\ufeff'"]


def test_bom_at_start_does_not_shift_columns_on_line_1(tmp_path):
    """With the approved fix read_source drops a leading BOM: same tokens as the BOM-free file."""
    plain = PROGRAM.encode("utf-8")
    source = read_bytes(tmp_path, b"\xef\xbb\xbf" + plain)
    assert positions(source) == positions(PROGRAM)
    assert messages(source) == []


def test_bom_only_file_is_an_empty_program(tmp_path):
    """A file that is just a BOM has no code."""
    assert messages(read_bytes(tmp_path, b"\xef\xbb\xbf")) == []


def test_bom_in_the_middle_is_still_an_error(tmp_path):
    """Only a LEADING BOM is stripped; a BOM inside the text is an invalid character."""
    data = "int a\ufeff = 1;\n".encode("utf-8")
    assert messages(read_bytes(tmp_path, data)) == [
        "[Lexical Error] Line 1, Col 6: Invalid character '\ufeff'"]


def test_second_bom_after_a_leading_bom_is_still_an_error(tmp_path):
    """Even with the fix only ONE leading BOM goes: a doubled BOM keeps an error."""
    data = b"\xef\xbb\xbf\xef\xbb\xbfint a;\n"
    assert any("Invalid character" in m for m in messages(read_bytes(tmp_path, data)))


# ------------------------------------------------------------------ size and depth

def test_expression_nested_30_parentheses_deep():
    """30 nested parentheses: correct, one temporary-free literal."""
    source = "int main() { return " + "(" * 30 + "1" + ")" * 30 + "; }"
    result = compile_source(source)
    assert result.errors == [] and result.tac[-2:] == ["  return 1", "endfunc"]


def test_expression_nested_30_operator_levels_deep():
    """30 levels of operator nesting: `(1 + (1 + (1 + ...)))` gives 30 additions."""
    expr = "1"
    for _ in range(30):
        expr = f"(1 + {expr})"
    result = compile_source(f"int main() {{ return {expr}; }}")
    assert result.errors == [] and sum(" + " in line for line in result.tac) == 30
    assert check_tac(result.tac) == []


def test_blocks_nested_100_deep():
    """100 nested blocks, with a variable used at the bottom."""
    source = "int main() {\n    int x = 1;\n" + "{\n" * 100 + "x = x + 1;\n" + "}\n" * 100 + "    return x;\n}\n"
    result = compile_source(source)
    assert result.errors == [] and check_tac(result.tac) == []
    assert sum("Scope" in line for line in result.table.dump().splitlines()) == 102   # global, main, 100 blocks


def generated_program(function_count: int) -> str:
    """A valid program of 4 lines per function; each function calls the one before it."""
    lines = ["int f0(int a) {", "    return a;", "}", ""]
    for i in range(1, function_count):
        lines += [f"int f{i}(int a) {{", f"    int b = a + {i};", f"    return f{i - 1}(b);", "}"]
    lines += ["int main() {", "    return f%d(1);" % (function_count - 1), "}"]
    return "\n".join(lines) + "\n"


def test_generated_program_of_1000_lines():
    """A 1000+ line program compiles; TAC is well-formed and has one func per function."""
    source = generated_program(250)
    assert source.count("\n") >= 1000
    result = compile_source(source)
    assert result.errors == []
    assert sum(line.startswith("func ") for line in result.tac) == 251
    assert check_tac(result.tac) == []


def test_parentheses_beyond_the_limit_give_one_error_not_a_crash():
    """Limitation (D-025, D-046): about 64 nested parentheses work; 200 give a clean error."""
    ok = compile_source("int main() { return " + "(" * 60 + "1" + ")" * 60 + "; }")
    deep = compile_source("int main() { return " + "(" * 200 + "1" + ")" * 200 + "; }")
    assert ok.errors == []
    assert any("nested too deeply" in e.message for e in deep.errors)


def test_braces_beyond_the_limit_give_a_clean_error_not_a_crash():
    """Limitation (D-025, D-046): about 325 nested blocks work; 600 give a clean error."""
    ok = compile_source("int main() " + "{" * 300 + "}" * 300 + "\n")
    deep = compile_source("int main() " + "{" * 600 + "return 1;" + "}" * 600)
    assert not any("too deeply" in e.message for e in ok.errors)
    assert any("nested too deeply" in e.message for e in deep.errors)
