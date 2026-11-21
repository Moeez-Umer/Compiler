"""SmartLang compiler command line (SPEC section 12, interfaces.md: main.py).

Phase 6: --tokens, --tree / --tree-png, --symbols and --tac exist. Later phases add polish (D-007).
This is the only module that prints.
"""
import os
import sys

# `python src/main.py` puts src/ (not the repo root) on sys.path, so add the root
# BEFORE the `src.` imports below. Harmless when imported by pytest.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.errors import ErrorCollector  # noqa: E402
from src.lexer import tokenize  # noqa: E402
from src.parser import parse  # noqa: E402
from src.semantic import analyze  # noqa: E402
from src.tacgen import generate  # noqa: E402
from src.tokens import Token  # noqa: E402
from src.tree_export import export_png, tree_to_text  # noqa: E402

EXIT_OK = 0
EXIT_COMPILE_ERROR = 1
EXIT_USAGE = 2

KNOWN_FLAGS = {"--tokens", "--tree", "--tree-png", "--symbols", "--tac"}
USAGE = "usage: python src/main.py prog.sl [--tokens] [--tree] [--tree-png PATH] [--symbols] [--tac]"


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


def run(path: str, flags: set[str], png_path: str | None = None) -> int:
    """Compile one file and print the requested sections. Returns the exit code.

    `png_path` is the PATH argument of --tree-png (D-019); `flags` holds the flag names.
    """
    source = read_source(path)
    if source is None:
        return EXIT_USAGE
    try:
        return run_stages(source, flags, png_path)
    except RecursionError:
        # SPEC section 9: never crash. Tree printing, drawing and the analyzer are recursive, so an
        # absurdly deep program ends here with one line on stderr (exit 1: a compile failure, not usage).
        print("error: program is nested too deeply to process (recursion limit exceeded)", file=sys.stderr)
        return EXIT_COMPILE_ERROR


def run_stages(source: str, flags: set[str], png_path: str | None) -> int:
    """Lex, parse, analyze and print the requested sections; may raise RecursionError (see `run`)."""
    errors = ErrorCollector()
    tokens = tokenize(source, errors)
    print("== TOKENS ==")
    print(format_token_table(tokens))
    print()
    # Parse only when a parser-based output was asked for; syntax errors are reported then (D-019).
    tree = parse(tokens, errors) if wants_tree(flags) else None
    if tree is not None and "--tree" in flags:
        print("== PARSE TREE ==")
        print(tree_to_text(tree))
        print()
    run_semantic_stage(tree, flags, errors)
    print("== ERRORS ==")
    for error in errors.all():
        print(error.format())
    if not errors.has_errors():
        print("(none)")
    run_tac_stage(tree, flags, errors)
    if tree is not None and "--tree-png" in flags:
        if not write_png(tree, png_path):
            return EXIT_USAGE
    return EXIT_COMPILE_ERROR if errors.has_errors() else EXIT_OK


def wants_tree(flags: set[str]) -> bool:
    """True if any requested output needs the parser (and so the semantic stage)."""
    return bool(flags & {"--tree", "--tree-png", "--symbols", "--tac"})


def run_tac_stage(tree, flags: set[str], errors: ErrorCollector) -> None:
    """Print `== THREE-ADDRESS CODE ==` when `--tac` is requested (SPEC sections 11 and 12).

    TAC is generated ONLY when there are zero errors; otherwise one skip line is printed.
    """
    if "--tac" not in flags:
        return
    print()
    print("== THREE-ADDRESS CODE ==")
    if tree is None or errors.has_errors():
        print("(skipped: compilation errors)")
        return
    lines = generate(tree)
    print("\n".join(lines) if lines else "(none)")


def run_semantic_stage(tree, flags: set[str], errors: ErrorCollector) -> None:
    """Analyze the tree when the parser ran and found no Lexical or Syntax errors (SPEC section 9).

    Semantic errors go into `errors` (printed under == ERRORS ==). With --symbols the tables are
    printed even when semantic errors exist; after lexical or syntax errors a skip note is printed.
    """
    if tree is None:
        return
    if errors.has_kind("Lexical") or errors.has_kind("Syntax"):
        if "--symbols" in flags:
            print("== SYMBOL TABLES ==")
            print("(skipped: lexical or syntax errors)")
            print()
        return
    table = analyze(tree, errors)
    if "--symbols" in flags:
        print("== SYMBOL TABLES ==")
        print(table.dump())
        print()


def write_png(tree, png_path: str | None) -> bool:
    """Write the tree image and report it; on failure print the reason to stderr."""
    try:
        export_png(tree, png_path)
    except RecursionError:
        raise   # a RuntimeError subclass: let `run` give the clear "nested too deeply" message and exit 1
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return False
    print(f"PNG written: {png_path}")
    return True


def parse_args(argv: list[str]) -> tuple[str, set[str], str | None] | None:
    """Split argv into (path, flags, png_path); None on a usage error.

    `--tree-png` must be followed by a path, which is not counted as the source file.
    """
    paths: list[str] = []
    flags: set[str] = set()
    png_path = None
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--tree-png":
            if index + 1 >= len(argv):
                return None
            png_path = argv[index + 1]
            index += 1
        if arg.startswith("-"):
            flags.add(arg)
        else:
            paths.append(arg)
        index += 1
    if len(paths) != 1 or not flags <= KNOWN_FLAGS:
        return None
    return paths[0], flags, png_path


def main(argv: list[str]) -> int:
    """Entry point: validate arguments, then run."""
    parsed = parse_args(argv)
    if parsed is None:
        print(USAGE, file=sys.stderr)
        return EXIT_USAGE
    path, flags, png_path = parsed
    return run(path, flags, png_path)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
