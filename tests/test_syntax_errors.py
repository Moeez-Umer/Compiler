"""Phase 3 tests: syntax error messages, panic-mode recovery and partial trees (SPEC section 9)."""
import random
import re
import signal
from contextlib import contextmanager
from pathlib import Path

import pytest

from src.ast_nodes import Block, FunctionDecl, VarDecl, Return, Program
from src.errors import ErrorCollector
from src.lexer import tokenize
from src.parser import parse
from src.tokens import Token, TokenType
from src.tree_export import tree_to_text

ROOT = Path(__file__).resolve().parent.parent
INVALID_DIR = ROOT / "tests" / "invalid"
EXPECT = re.compile(r"^// EXPECT: (Lexical|Syntax) (\d+) (.*)$")


class Hang(Exception):
    """Raised by the alarm handler when a parse runs too long (hang detector)."""


@contextmanager
def time_limit(seconds: int):
    """Fail with Hang if the body runs longer than `seconds` (SIGALRM, macOS and Linux)."""
    def on_alarm(signum, frame):
        raise Hang(f"parser did not finish within {seconds} s")

    old_handler = signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def parse_source(source: str) -> tuple[Program, ErrorCollector]:
    """Lex and parse a source string; return the tree and the shared collector."""
    errors = ErrorCollector()
    return parse(tokenize(source, errors), errors), errors


def syntax_errors(source: str) -> list[str]:
    """Formatted Syntax errors for `source`, in report order of ErrorCollector.all()."""
    _, errors = parse_source(source)
    return [e.format() for e in errors.all() if e.kind == "Syntax"]


def wrap(statements: str) -> str:
    """Put statements inside `int main() { ... }` on lines 2 to N+1 (line 1 is the header)."""
    return "int main() {\n" + statements + "\n}\n"


# ------------------------------------------------- messages, lines and columns


def test_missing_semicolon_reports_expected_and_found():
    """`int b = 2` then `return`: the error is on the token that should have been `;`."""
    source = wrap("    int b = 2\n    return b;")
    assert syntax_errors(source) == [
        "[Syntax Error] Line 3, Col 5: Expected ';' but found 'return'"]


def test_missing_close_paren():
    """`if (a > 0 {` -> Expected ')' but found '{' at the brace."""
    source = wrap("    int a = 1;\n    if (a > 0 {\n        a = 2;\n    }")
    assert syntax_errors(source) == [
        "[Syntax Error] Line 3, Col 15: Expected ')' but found '{'"]


def test_missing_close_brace_at_eof():
    """An unclosed block reports once, at the end of file."""
    assert syntax_errors("int main() {\n    return 0;\n") == [
        "[Syntax Error] Line 3, Col 1: Expected '}' but found end of file"]


def test_two_unclosed_blocks_report_once():
    """Nested unclosed blocks all hit EOF at the same spot; only one message is shown."""
    source = "int main() {\n    while (true) {\n        return 0;\n"
    assert syntax_errors(source) == [
        "[Syntax Error] Line 4, Col 1: Expected '}' but found end of file"]


def test_extra_close_brace_at_top_level():
    """A second `}` after the function is garbage at top level."""
    assert syntax_errors("int main() {\n    return 0;\n}\n}\n") == [
        "[Syntax Error] Line 4, Col 1: Expected type but found '}'"]


def test_missing_function_body():
    """`int f(int x);` has no block."""
    assert syntax_errors("int f(int x);\nint main() {\n    return 0;\n}\n") == [
        "[Syntax Error] Line 1, Col 13: Expected '{' but found ';'"]


def test_bad_expression_star_after_plus():
    """`1 + * 2`: the `*` cannot start an operand."""
    assert syntax_errors(wrap("    int a = 1 + * 2;")) == [
        "[Syntax Error] Line 2, Col 17: Expected expression but found '*'"]


def test_else_without_if():
    """A stray `else` is reported once; its block does not add more errors."""
    source = wrap("    int a = 1;\n    else { a = 2; }\n    return a;")
    assert syntax_errors(source) == [
        "[Syntax Error] Line 3, Col 5: Expected statement but found 'else'"]


def test_missing_operand_before_semicolon():
    """`1 + ;` -> the `;` cannot start an operand."""
    assert syntax_errors(wrap("    int a = 1 + ;")) == [
        "[Syntax Error] Line 2, Col 17: Expected expression but found ';'"]


def test_missing_operand_in_call_and_paren():
    """Missing operands inside `( )` and argument lists are found too."""
    errors = syntax_errors(wrap("    int a = (1 + );\n    f(1, );"))
    assert errors == [
        "[Syntax Error] Line 2, Col 18: Expected expression but found ')'",
        "[Syntax Error] Line 3, Col 10: Expected expression but found ')'"]


def test_garbage_at_top_level_is_one_error():
    """A run of junk is skipped to the next `;` with a single message."""
    assert syntax_errors("42 foo bar;\nint main() {\n    return 0;\n}\n") == [
        "[Syntax Error] Line 1, Col 1: Expected type but found '42'"]


def test_return_without_value():
    """`return;` is a missing operand (every function returns a value, SPEC section 6)."""
    assert syntax_errors(wrap("    return;")) == [
        "[Syntax Error] Line 2, Col 11: Expected expression but found ';'"]


# --------------------------------------------------- several errors per file


def test_several_independent_errors_are_all_reported():
    """Four mistakes in four places give four messages."""
    source = ("int g = ;\n"
              "int f() {\n"
              "    int s = 1 + * 2;\n"
              "    return s;\n"
              "}\n"
              "int main() {\n"
              "    x = ;\n"
              "    return 0;\n"
              "}\n")
    errors = syntax_errors(source)
    assert [e.split(":")[0] for e in errors] == [
        "[Syntax Error] Line 1, Col 9", "[Syntax Error] Line 3, Col 17",
        "[Syntax Error] Line 7, Col 9"]


def test_one_mistake_gives_one_error_when_it_swallows_a_statement():
    """After recovery the parser must not repeat the same mistake on the next token."""
    errors = syntax_errors(wrap("    int a = 1 + * * 2;\n    return a;"))
    assert len(errors) == 1


@pytest.mark.parametrize("path", sorted(INVALID_DIR.glob("syntax_*.sl")), ids=lambda p: p.name)
def test_invalid_files_match_their_expect_lines(path):
    """Every tests/invalid/syntax_*.sl lists its expected errors in `// EXPECT:` lines."""
    expected = []
    for text in path.read_text().splitlines():
        match = EXPECT.match(text)
        if match:
            expected.append((match.group(1), int(match.group(2)), match.group(3)))
    assert expected, f"{path.name} has no EXPECT lines"
    _, errors = parse_source(path.read_text())
    assert [(e.kind, e.line, e.message) for e in errors.all()] == expected


def test_there_are_enough_syntax_sample_files():
    """Guard against the parametrized test above silently running zero files."""
    assert len(list(INVALID_DIR.glob("syntax_*.sl"))) >= 10


# ------------------------------------------------------------- partial tree


def names(program: Program) -> list[str]:
    """Names of the top-level items of a tree, in order."""
    return [item.name for item in program.items]


def test_partial_tree_keeps_every_top_level_item():
    """D-021: a broken function stays in the tree between the items that parsed."""
    source = ("int g = 1;\n"
              "int broken( {\n"
              "    return 1;\n"
              "}\n"
              "int h() {\n"
              "    return 2;\n"
              "}\n")
    tree, errors = parse_source(source)
    assert names(tree) == ["g", "broken", "h"]
    assert len(errors.all()) == 1


def test_partial_tree_text_shows_more_than_program():
    """The exported tree must show the functions, not just the word Program."""
    tree, _ = parse_source("int f() {\n    return 1\n}\nint main() {\n    return 0;\n}\n")
    text = tree_to_text(tree)
    assert "f" in text and "main" in text and len(text.splitlines()) > 3


def test_partial_tree_keeps_statements_around_a_bad_one():
    """Statements before and after the failed one are kept; the failed one is dropped."""
    source = wrap("    int a = 1;\n    int b = ;\n    return a;")
    tree, _ = parse_source(source)
    statements = tree.items[0].body.statements
    assert [type(s) for s in statements] == [VarDecl, Return]
    assert statements[0].name == "a"


def test_missing_body_keeps_function_with_empty_block():
    """`int f(int x);` stays as a FunctionDecl whose body is an empty Block."""
    tree, _ = parse_source("int f(int x);\nint main() {\n    return 0;\n}\n")
    func = tree.items[0]
    assert isinstance(func, FunctionDecl) and func.name == "f"
    assert isinstance(func.body, Block) and func.body.statements == []
    assert names(tree) == ["f", "main"]


def test_missing_brace_at_eof_keeps_the_statements():
    """The unclosed function keeps the statements that parsed before the end of file."""
    tree, _ = parse_source("int main() {\n    int a = 1;\n    return a;\n")
    assert [type(s) for s in tree.items[0].body.statements] == [VarDecl, Return]


def test_function_after_a_bad_function_is_still_parsed():
    """Recovery inside one function must not lose the next function."""
    source = ("int f() {\n    int a = 1 + * 2;\n    return a;\n}\n"
              "int main() {\n    return 0;\n}\n")
    tree, _ = parse_source(source)
    assert names(tree) == ["f", "main"]
    assert len(tree.items[0].body.statements) == 1


def test_else_without_if_keeps_surrounding_statements():
    """The statements on both sides of a stray else survive."""
    tree, _ = parse_source(wrap("    int a = 1;\n    else { a = 2; }\n    return a;"))
    kinds = [type(s).__name__ for s in tree.items[0].body.statements]
    assert kinds[0] == "VarDecl" and kinds[-1] == "Return"


def test_failed_if_header_keeps_its_body_as_a_block():
    """`if (a > 0 {` loses the If node but its body block is kept (D-022)."""
    source = wrap("    int a = 1;\n    if (a > 0 {\n        a = 2;\n    }\n    return a;")
    tree, _ = parse_source(source)
    kinds = [type(s).__name__ for s in tree.items[0].body.statements]
    assert kinds == ["VarDecl", "Block", "Return"]


# ------------------------------------------------- D-020 inside the recovery


def kinds_and_lines(source: str) -> list[tuple[str, int]]:
    """(kind, line) of every reported error."""
    _, errors = parse_source(source)
    return [(e.kind, e.line) for e in errors.all()]


def test_lexical_error_alone_gives_no_syntax_error():
    """`5 @ 1` loses the `@`; the follow-on error at `1` is suppressed (D-020)."""
    assert kinds_and_lines(wrap("    int a = 5 @ 1;")) == [("Lexical", 2)]


def test_lexical_error_and_real_syntax_error_in_one_file():
    """The lexical error is not repeated as syntax; the real error on another line is."""
    source = wrap("    int a = 5 @ 1;\n    int b = ;\n    return a;")
    assert kinds_and_lines(source) == [("Lexical", 2), ("Syntax", 3)]


def test_real_syntax_error_before_the_lexical_error():
    """Order does not matter: both are reported, Lexical first (SPEC section 9)."""
    source = wrap("    int b = ;\n    int a = 5 @ 1;\n    return a;")
    assert kinds_and_lines(source) == [("Lexical", 3), ("Syntax", 2)]


def test_lexical_error_between_two_syntax_errors():
    """Recovery continues past a suppressed error and finds the next real one."""
    source = wrap("    int b = ;\n    int a = 5 @ 1;\n    int c = 1 + * 2;\n    return a;")
    assert kinds_and_lines(source) == [("Lexical", 3), ("Syntax", 2), ("Syntax", 4)]


def test_unterminated_char_literal_and_later_syntax_error():
    """D-013: `'a;` swallows the `;`; the cascade is suppressed, the later error is not."""
    source = wrap("    char h = 'a;\n    int z = ;\n    return 0;")
    assert kinds_and_lines(source) == [("Lexical", 2), ("Syntax", 3)]


def test_malformed_number_and_missing_semicolon_later():
    """`9abc` vanishes as INVALID; the error after it is hidden, a later one is shown."""
    source = wrap("    int g = 9abc;\n    int k = 1\n    return k;")
    assert kinds_and_lines(source) == [("Lexical", 2), ("Syntax", 4)]


def test_known_limitation_genuine_error_right_after_invalid_is_hidden():
    """D-023: a real error directly after an INVALID token is hidden too.

    `@ else {}` : the `else` is a real mistake (stray else) but follows INVALID.
    This test documents the limitation; if it is ever fixed, update D-023.
    """
    source = wrap("    int a = 1;\n    @ else { a = 2; }\n    return a;")
    assert kinds_and_lines(source) == [("Lexical", 3)]


# ----------------------------------------------- forced progress, no crash


@pytest.mark.parametrize("source", [
    "", "}", "}}}}", ")))", "{{{{", "else else else", ";;;;", "int", "int int int",
    "int f(", "int f(int", "int f(int a,", "int f() {", "int f() { if", "int f() { if (",
    "int f() { for (", "int f() { for (;;", "int f() { return", "const", "const const",
    "int main() { else }", "int main() { } } } }", "@ @ @", "int x = ", "int x = (",
])
def test_garbage_never_crashes_or_hangs(source):
    """Truncated and nonsense inputs terminate and return a Program."""
    with time_limit(10):
        tree, errors = parse_source(source)
    assert isinstance(tree, Program)
    if source.replace("@", "").strip():
        assert errors.has_kind("Syntax") or errors.has_kind("Lexical")


def test_empty_token_list_does_not_crash():
    """interfaces.md: parse never raises, even without an EOF token."""
    errors = ErrorCollector()
    assert isinstance(parse([], errors), Program)


def test_deeply_nested_parentheses_are_reported_not_fatal():
    """RecursionError becomes a Syntax error and later items are still checked."""
    source = "int a = " + "(" * 5000 + "1" + ")" * 5000 + ";\nint b = ;\n"
    with time_limit(20):
        _, errors = parse_source(source)
    messages = [e.message for e in errors.all() if e.kind == "Syntax"]
    assert "Program is nested too deeply" in messages
    assert any(m.startswith("Expected expression") for m in messages)


# -------------------------------------------------------------------- fuzz

FUZZ_SEED = 20261116
FUZZ_RUNS = 3000
FUZZ_TIMEOUT_SECONDS = 60

FUZZ_POOL = (
    [(TokenType.KEYWORD, w) for w in
     ("int", "float", "char", "bool", "const", "if", "else", "while", "for", "return", "true", "false")]
    + [(TokenType.IDENTIFIER, w) for w in ("a", "b", "main", "f")]
    + [(TokenType.INT_LIT, "1"), (TokenType.FLOAT_LIT, "2.5"), (TokenType.CHAR_LIT, "'c'")]
    + [(TokenType.OPERATOR, w) for w in
       ("+", "-", "*", "/", "%", "=", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!")]
    + [(TokenType.DELIMITER, w) for w in ("(", ")", "{", "}", ";", ",")]
    + [(TokenType.INVALID, "@")]
)


def random_tokens(rng: random.Random) -> list[Token]:
    """A random token sequence of length 0 to 40 that always ends with EOF."""
    tokens = []
    for index in range(rng.randint(0, 40)):
        kind, lexeme = rng.choice(FUZZ_POOL)
        tokens.append(Token(kind, lexeme, 1 + index // 8, 1 + index % 8))
    tokens.append(Token(TokenType.EOF, "", 99, 1))
    return tokens


def test_fuzz_random_token_sequences_never_raise_or_hang():
    """Fixed seed, 3000 random sequences: parse() returns a Program every time, within the timeout."""
    rng = random.Random(FUZZ_SEED)
    with time_limit(FUZZ_TIMEOUT_SECONDS):
        for _ in range(FUZZ_RUNS):
            errors = ErrorCollector()
            tree = parse(random_tokens(rng), errors)
            assert isinstance(tree, Program)


def test_fuzz_is_deterministic():
    """The same seed produces the same token sequences (so a failure can be replayed)."""
    first = [random_tokens(random.Random(FUZZ_SEED)) for _ in range(2)]
    assert first[0] == first[1]


def test_ensure_progress_consumes_one_token_when_nothing_was_consumed():
    """The forward-progress guard: no movement since `start` forces one token forward."""
    from src.parser import Parser
    tokens = tokenize("} int", ErrorCollector())
    parser = Parser(tokens, ErrorCollector())
    parser.ensure_progress(0)
    assert parser.peek().lexeme == "int"
    parser.ensure_progress(0)          # already moved past 0: must not consume again
    assert parser.peek().lexeme == "int"


def test_ensure_progress_never_moves_past_eof():
    """At EOF the guard does nothing, so the loops can end."""
    from src.parser import Parser
    parser = Parser(tokenize("", ErrorCollector()), ErrorCollector())
    parser.ensure_progress(0)
    assert parser.peek().type == TokenType.EOF


# ------------------------------------------- missing `;` is inserted (D-024)

MISSING_SEMI_NEXT = "int main() {\n    int x = 1\n    x = x + 2;\n    return x;\n}\n"


def test_missing_semicolon_keeps_the_next_statement():
    """`int x = 1` newline `x = x + 2;`: one error, and all three statements stay in the tree."""
    tree, errors = parse_source(MISSING_SEMI_NEXT)
    assert [e.format() for e in errors.all()] == [
        "[Syntax Error] Line 3, Col 5: Expected ';' but found 'x'"]
    kinds = [type(s).__name__ for s in tree.items[0].body.statements]
    assert kinds == ["VarDecl", "Assign", "Return"]


def test_error_inside_the_statement_after_a_missing_semicolon_is_reported():
    """Because nothing is skipped, a real error in the next statement is found as well."""
    source = "int main() {\n    int x = 1\n    x = x + * 2;\n    return x;\n}\n"
    assert syntax_errors(source) == [
        "[Syntax Error] Line 3, Col 5: Expected ';' but found 'x'",
        "[Syntax Error] Line 3, Col 13: Expected expression but found '*'"]


def test_missing_semicolon_right_before_close_brace():
    """`int x = 1 }`: the `}` is not skipped, so the block still closes."""
    tree, errors = parse_source("int main() {\n    int x = 1 }\nint g() {\n    return 1;\n}\n")
    assert [e.format() for e in errors.all()] == [
        "[Syntax Error] Line 2, Col 15: Expected ';' but found '}'"]
    assert names(tree) == ["main", "g"]
    assert [type(s).__name__ for s in tree.items[0].body.statements] == ["VarDecl"]


def test_missing_semicolon_before_keyword_on_the_same_line():
    """A statement-start keyword also triggers insertion, even on the same line."""
    tree, errors = parse_source(wrap("    int a = 1 int b = 2;"))
    assert len(errors.all()) == 1
    assert [s.name for s in tree.items[0].body.statements] == ["a", "b"]


def test_missing_semicolon_at_end_of_file():
    """`return 1` at the end of the file: `;` is reported, then the missing `}`."""
    assert syntax_errors("int main() {\n    return 1\n") == [
        "[Syntax Error] Line 3, Col 1: Expected ';' but found end of file"]


def test_extra_token_on_the_same_line_still_skips():
    """Same line and not a keyword: the old skip behaviour stays (`int a = 1 2;`)."""
    tree, errors = parse_source(wrap("    int a = 1 2;\n    return 0;"))
    assert len(errors.all()) == 1
    assert [type(s).__name__ for s in tree.items[0].body.statements] == ["Return"]


def test_missing_semicolon_in_top_level_declaration_keeps_it():
    """`int g = 1` newline `int main()...`: the global is kept."""
    tree, errors = parse_source("int g = 1\nint main() {\n    return g;\n}\n")
    assert len(errors.all()) == 1
    assert names(tree) == ["g", "main"]


# -------------------------------------------- deep nesting through the CLI


def run_cli_on(tmp_path, source: str, capsys) -> tuple[int, str]:
    """Write `source` to a file, run the CLI stage `--tree`, return (exit code, stdout)."""
    from src.main import run
    path = tmp_path / "deep.sl"
    path.write_text(source)
    code = run(str(path), {"--tree"})
    return code, capsys.readouterr().out


@pytest.mark.parametrize("name, source", [
    ("parens", "int a = " + "(" * 5000 + "1" + ")" * 5000 + ";\n"),
    ("braces", "int main() {\n" + "{" * 5000 + "}" * 5000 + "\n}\n"),
    ("bangs", "int a = " + "!" * 5000 + "1;\n"),
])
def test_deep_nesting_gives_one_error_and_exit_code_1(tmp_path, capsys, name, source):
    """No traceback, exit code 1, and a single `nested too deeply` message (no cascade)."""
    with time_limit(30):
        code, out = run_cli_on(tmp_path, source, capsys)
    errors = [line for line in out.splitlines() if line.startswith("[Syntax Error]")]
    assert code == 1
    assert len(errors) == 1 and "nested too deeply" in errors[0]


def test_run_of_stray_close_braces_is_one_error():
    """`}}}}` at top level is one mistake, so one message."""
    assert len(syntax_errors("int main() {\n    return 0;\n}\n}}}}\n")) == 1


# ------------------------------------------------------------ raw-text fuzz

RAW_FUZZ_SEED = 20261117
RAW_FUZZ_RUNS = 2000
RAW_ALPHABET = ([chr(c) for c in range(32, 127)] + ["\n", "\t"]
                + list("(){};,=+-*/%<>!&|") * 3
                + ["int ", "float ", "char ", "bool ", "const ", "if ", "else ", "while ",
                   "for ", "return ", "true ", "false ", "main", "/*", "//", "'"])


def random_text(rng: random.Random) -> str:
    """0 to 80 random pieces: printable ASCII, SmartLang symbols, keywords, newlines."""
    return "".join(rng.choice(RAW_ALPHABET) for _ in range(rng.randint(0, 80)))


def test_fuzz_random_raw_text_never_raises_or_hangs():
    """Fixed seed, 2000 random texts through tokenize() and parse(): always a Program, no hang."""
    rng = random.Random(RAW_FUZZ_SEED)
    with time_limit(60):
        for _ in range(RAW_FUZZ_RUNS):
            tree, errors = parse_source(random_text(rng))
            assert isinstance(tree, Program)
            assert all(e.line >= 1 for e in errors.all())


def test_raw_fuzz_is_deterministic():
    """The same seed gives the same texts, so a failing input can be replayed."""
    assert random_text(random.Random(RAW_FUZZ_SEED)) == random_text(random.Random(RAW_FUZZ_SEED))

