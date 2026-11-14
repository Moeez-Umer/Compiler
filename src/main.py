"""SmartLang compiler command line (SPEC section 12, interfaces.md: main.py).

Phase 1: only the --tokens stage exists. Later phases add one stage each (D-007).
This is the only module that prints.
"""
import os
import sys

# `python src/main.py` puts src/ (not the repo root) on sys.path, so add the root
# BEFORE the `src.` imports below. Harmless when imported by pytest.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.errors import ErrorCollector  # noqa: E402
from src.lexer import tokenize  # noqa: E402
from src.tokens import Token  # noqa: E402

EXIT_OK = 0
EXIT_COMPILE_ERROR = 1
EXIT_USAGE = 2

KNOWN_FLAGS = {"--tokens"}
USAGE = "usage: python src/main.py prog.sl [--tokens]"


def format_token_table(tokens: list[Token]) -> str:
    """Render tokens as an aligned table: type, lexeme, line, col."""
    rows = [(t.type.name, t.lexeme, str(t.line), str(t.col)) for t in tokens]
    header = ("TYPE", "LEXEME", "LINE", "COL")
    widths = [max(len(r[i]) for r in rows + [header]) for i in range(4)]
    lines = []
    for row in [header] + rows:
        lines.append(
            f"{row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}  "
            f"{row[2]:>{widths[2]}}  {row[3]:>{widths[3]}}")
    return "\n".join(lines)


def read_source(path: str) -> str | None:
    """Return the file text, or None if it cannot be read as UTF-8 text."""
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read '{path}': {exc}", file=sys.stderr)
        return None


def run(path: str, flags: set[str]) -> int:
    """Compile one file and print the requested sections. Returns the exit code."""
    source = read_source(path)
    if source is None:
        return EXIT_USAGE
    errors = ErrorCollector()
    tokens = tokenize(source, errors)
    # Phase 1 has only one stage, so every flag combination prints the token table.
    print("== TOKENS ==")
    print(format_token_table(tokens))
    print()
    print("== ERRORS ==")
    for error in errors.all():
        print(error.format())
    if not errors.has_errors():
        print("(none)")
    return EXIT_COMPILE_ERROR if errors.has_errors() else EXIT_OK


def parse_args(argv: list[str]) -> tuple[str, set[str]] | None:
    """Split argv into (path, flags); None on a usage error."""
    paths = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if len(paths) != 1 or not flags <= KNOWN_FLAGS:
        return None
    return paths[0], flags


def main(argv: list[str]) -> int:
    """Entry point: validate arguments, then run."""
    parsed = parse_args(argv)
    if parsed is None:
        print(USAGE, file=sys.stderr)
        return EXIT_USAGE
    return run(*parsed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
