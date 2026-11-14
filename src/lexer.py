"""Hand-written lexical analyzer (SPEC section 5, interfaces.md: lexer.py).

A single left-to-right scan. Each token class has its own small method.
Invalid input never stops the scan: it produces an INVALID token and a
Lexical error, then scanning continues (SPEC section 9).
"""
from src.errors import ErrorCollector
from src.tokens import Token, TokenType

KEYWORDS = frozenset({
    "int", "float", "char", "bool", "const", "if", "else",
    "for", "while", "return", "true", "false"})

# Explicit ASCII sets: str.isalpha()/isdigit() would accept Unicode letters and digits.
LETTERS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
DIGITS = frozenset("0123456789")
IDENT_CHARS = LETTERS | DIGITS

# Two-character operators are tried first so the longest match wins (SPEC section 5).
TWO_CHAR_OPERATORS = frozenset({"==", "!=", "<=", ">=", "&&", "||"})
ONE_CHAR_OPERATORS = frozenset("+-*/%=<>!")
DELIMITERS = frozenset("(){};,")

# Characters allowed after a backslash inside a char literal.
ESCAPE_CHARS = frozenset("nt\\'0")


class Lexer:
    """Scans one source string. Tracks position, line (from 1) and column (from 1)."""

    def __init__(self, source: str, errors: ErrorCollector) -> None:
        """Remember the source and the shared collector; start at line 1, col 1."""
        self.source = source
        self.errors = errors
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    # ---------- low-level cursor helpers ----------

    def peek(self, offset: int = 0) -> str:
        """Character at pos+offset, or "" past the end (so comparisons never raise)."""
        index = self.pos + offset
        return self.source[index] if index < len(self.source) else ""

    def advance(self) -> str:
        """Consume one character and update line/col.

        Only "\\n" breaks a line, so CRLF counts as one break; the "\\r" just
        advances the column on a line that is about to end.
        """
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def emit(self, token_type: TokenType, lexeme: str, line: int, col: int) -> None:
        """Append a token that started at (line, col)."""
        self.tokens.append(Token(token_type, lexeme, line, col))

    def emit_invalid(self, lexeme: str, line: int, col: int, message: str) -> None:
        """Append an INVALID token and report the Lexical error at its start."""
        self.emit(TokenType.INVALID, lexeme, line, col)
        self.errors.report("Lexical", line, col, message)

    # ---------- main loop ----------

    def run(self) -> list[Token]:
        """Scan the whole source; the result always ends with EOF."""
        while self.pos < len(self.source):
            self.scan_next()
        self.emit(TokenType.EOF, "", self.line, self.col)
        return self.tokens

    def scan_next(self) -> None:
        """Skip whitespace/comments or scan exactly one token, chosen by its first character."""
        ch = self.peek()
        if ch in " \t\r\n":
            self.advance()
        elif ch == "/" and self.peek(1) == "/":
            self.skip_line_comment()
        elif ch == "/" and self.peek(1) == "*":
            self.skip_block_comment()
        elif ch in LETTERS:
            self.scan_word()
        elif ch in DIGITS or (ch == "." and self.peek(1) in DIGITS):
            self.scan_number()
        elif ch == "'":
            self.scan_char()
        else:
            self.scan_operator_or_delimiter()

    # ---------- comments ----------

    def skip_line_comment(self) -> None:
        """Skip '//' up to (not including) the end of the line."""
        while self.pos < len(self.source) and self.peek() != "\n":
            self.advance()

    def skip_block_comment(self) -> None:
        """Skip '/* ... */' (non-nesting). If unclosed, report at the line it started."""
        line, col = self.line, self.col
        self.advance()
        self.advance()  # consume "/*"
        while self.pos < len(self.source):
            if self.peek() == "*" and self.peek(1) == "/":
                self.advance()
                self.advance()
                return
            self.advance()
        self.emit_invalid("/*", line, col, "Unterminated block comment")

    # ---------- words and numbers ----------

    def scan_word(self) -> None:
        """identifier or keyword: [A-Za-z_][A-Za-z0-9_]*; keyword if in KEYWORDS."""
        line, col = self.line, self.col
        text = ""
        while self.peek() in IDENT_CHARS and self.peek() != "":
            text += self.advance()
        kind = TokenType.KEYWORD if text in KEYWORDS else TokenType.IDENTIFIER
        self.emit(kind, text, line, col)

    def scan_number(self) -> None:
        """INT_LIT or FLOAT_LIT, or one INVALID token for a malformed number.

        WHY take the whole run of digits, letters and dots first: '3.4.5', '3.',
        '.5' and '9abc' are then each ONE bad token and ONE error, instead of a
        confusing cascade of small tokens.
        """
        line, col = self.line, self.col
        text = ""
        while self.peek() != "" and (self.peek() in IDENT_CHARS or self.peek() == "."):
            text += self.advance()
        kind = classify_number(text)
        if kind is not None:
            self.emit(kind, text, line, col)
        elif any(c in LETTERS for c in text):
            self.emit_invalid(text, line, col, f"Number '{text}' is glued to letters")
        else:
            self.emit_invalid(text, line, col, f"Malformed number '{text}'")

    # ---------- char literals ----------

    def scan_char(self) -> None:
        """CHAR_LIT: one character or one escape between single quotes.

        Reads to the closing quote or to the end of the line, whichever comes
        first, so one bad literal is one INVALID token.
        """
        line, col = self.line, self.col
        text = self.advance()  # opening quote
        closed = False
        while self.peek() not in ("", "\n"):
            ch = self.advance()
            text += ch
            if ch == "\\" and self.peek() not in ("", "\n"):
                text += self.advance()  # the escaped char, even if it is a quote
            elif ch == "'":
                closed = True
                break
        self.finish_char(text, closed, line, col)

    def finish_char(self, text: str, closed: bool, line: int, col: int) -> None:
        """Decide whether the scanned text is a valid char literal; else report why."""
        body = text[1:-1] if closed else text[1:]
        if not closed:
            self.emit_invalid(text, line, col, f"Unterminated char literal {text}")
        elif body == "":
            self.emit_invalid(text, line, col, "Empty char literal ''")
        elif len(body) == 1 and body != "\\":
            self.emit(TokenType.CHAR_LIT, text, line, col)
        elif len(body) == 2 and body[0] == "\\" and body[1] in ESCAPE_CHARS:
            self.emit(TokenType.CHAR_LIT, text, line, col)
        elif len(body) == 2 and body[0] == "\\":
            self.emit_invalid(text, line, col, f"Bad escape sequence in char literal {text}")
        else:
            self.emit_invalid(text, line, col, f"Char literal {text} is too long")

    # ---------- operators, delimiters, unknown characters ----------

    def scan_operator_or_delimiter(self) -> None:
        """Operator (longest match first), delimiter, or an invalid character."""
        line, col = self.line, self.col
        pair = self.peek() + self.peek(1)
        if pair in TWO_CHAR_OPERATORS:
            self.advance()
            self.advance()
            self.emit(TokenType.OPERATOR, pair, line, col)
            return
        ch = self.advance()
        if ch in ONE_CHAR_OPERATORS:
            self.emit(TokenType.OPERATOR, ch, line, col)
        elif ch in DELIMITERS:
            self.emit(TokenType.DELIMITER, ch, line, col)
        else:
            # Covers '@', a single '&' or '|', and any other character not in SPEC.
            self.emit_invalid(ch, line, col, f"Invalid character '{ch}'")


def classify_number(text: str) -> TokenType | None:
    """INT_LIT for [0-9]+, FLOAT_LIT for [0-9]+.[0-9]+, otherwise None (malformed)."""
    if text != "" and all(c in DIGITS for c in text):
        return TokenType.INT_LIT
    whole, dot, fraction = text.partition(".")
    digits_only = whole != "" and fraction != "" and all(c in DIGITS for c in whole + fraction)
    if dot == "." and digits_only:
        return TokenType.FLOAT_LIT
    return None


def tokenize(source: str, errors: ErrorCollector) -> list[Token]:
    """Turn source text into tokens. Always ends with EOF (interfaces.md: lexer.py)."""
    return Lexer(source, errors).run()
