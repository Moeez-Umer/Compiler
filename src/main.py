"""SmartLang compiler command line (SPEC sections 9 and 12, interfaces.md: main.py).

Phase 7: the full pipeline always runs as far as the errors allow (D-041), every section's text
is built first and printed afterwards in a fixed order (D-042), and PNG problems are reported on
stderr without hiding the sections (D-043). This is the only module that prints.
"""
import os
import sys
from dataclasses import dataclass

# `python src/main.py` puts src/ (not the repo root) on sys.path, so add the root
# BEFORE the `src.` imports below. Harmless when imported by pytest.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ast_nodes import Program  # noqa: E402
from src.errors import ErrorCollector  # noqa: E402
from src.lexer import tokenize  # noqa: E402
from src.parser import parse  # noqa: E402
from src.semantic import analyze  # noqa: E402
from src.symbol_table import SymbolTable  # noqa: E402
from src.tacgen import generate  # noqa: E402
from src.tokens import Token  # noqa: E402
from src.tree_export import export_png, tree_to_text  # noqa: E402

EXIT_OK = 0
EXIT_COMPILE_ERROR = 1
EXIT_USAGE = 2

SECTION_FLAGS = ("--tokens", "--tree", "--symbols", "--tac")
KNOWN_FLAGS = set(SECTION_FLAGS) | {"--tree-png", "--all"}
USAGE = ("usage: python src/main.py prog.sl [--tokens] [--tree] [--tree-png PATH] "
         "[--symbols] [--tac] [--all]")


@dataclass
class Compiled:
    """Everything the pipeline produced; a stage that was skipped leaves its field None."""
    tokens: list[Token]
    tree: Program
    errors: ErrorCollector
    table: SymbolTable | None = None
    tac: list[str] | None = None


# ------------------------------------------------------------------ pipeline

def run_pipeline(source: str) -> Compiled:
    """Lexer and parser always run; semantic only without Lexical/Syntax errors; TAC only
    without any error (SPEC section 9). May raise RecursionError (see `run`)."""
    errors = ErrorCollector()
    tokens = tokenize(source, errors)
    tree = parse(tokens, errors)
    result = Compiled(tokens, tree, errors)
    if not (errors.has_kind("Lexical") or errors.has_kind("Syntax")):
        result.table = analyze(tree, errors)
    if not errors.has_errors():
        result.tac = generate(tree)
    return result


# ------------------------------------------------------------------ sections

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


def build_tokens_section(compiled: Compiled) -> str:
    """`== TOKENS ==` and the token table."""
    return "== TOKENS ==\n" + format_token_table(compiled.tokens)


def build_tree_section(compiled: Compiled) -> tuple[str, bool]:
    """`== PARSE TREE ==`; returns (text, ok). Printing is recursive, so a very deep tree
    gives a skip line and ok=False (the exit code becomes 1, D-043)."""
    try:
        return "== PARSE TREE ==\n" + tree_to_text(compiled.tree), True
    except RecursionError:
        return "== PARSE TREE ==\n(skipped: nested too deeply to print)", False


def build_symbols_section(compiled: Compiled) -> str:
    """`== SYMBOL TABLES ==`, or a skip line when the semantic stage did not run."""
    if compiled.table is None:
        return "== SYMBOL TABLES ==\n(skipped: lexical or syntax errors)"
    return "== SYMBOL TABLES ==\n" + compiled.table.dump()


def build_errors_section(compiled: Compiled) -> str:
    """`== ERRORS ==`: one formatted line per error, or `(none)`. Always printed."""
    lines = [error.format() for error in compiled.errors.all()]
    return "== ERRORS ==\n" + ("\n".join(lines) if lines else "(none)")


def build_tac_section(compiled: Compiled) -> str:
    """`== THREE-ADDRESS CODE ==`, or a skip line when any error exists."""
    if compiled.tac is None:
        return "== THREE-ADDRESS CODE ==\n(skipped: compilation errors)"
    return "== THREE-ADDRESS CODE ==\n" + ("\n".join(compiled.tac) if compiled.tac else "(none)")


def resolve_flags(flags: set[str]) -> set[str]:
    """`--all`, or no section flag at all, means every section (the PNG is never implied)."""
    if "--all" in flags or not flags & set(SECTION_FLAGS):
        return set(SECTION_FLAGS)
    return flags & set(SECTION_FLAGS)


def build_sections(compiled: Compiled, flags: set[str]) -> tuple[list[str], bool]:
    """All requested sections as text, in the fixed order; the bool is False if the tree failed."""
    active = resolve_flags(flags)
    sections: list[str] = []
    tree_ok = True
    if "--tokens" in active:
        sections.append(build_tokens_section(compiled))
    if "--tree" in active:
        text, tree_ok = build_tree_section(compiled)
        sections.append(text)
    if "--symbols" in active:
        sections.append(build_symbols_section(compiled))
    sections.append(build_errors_section(compiled))
    if "--tac" in active:
        sections.append(build_tac_section(compiled))
    return sections, tree_ok


# ------------------------------------------------------------------ PNG and run

def one_line(text: object) -> str:
    """Collapse any message to a single line (stderr messages are one line)."""
    return " ".join(str(text).split())


def write_png(tree: Program, png_path: str | None) -> int:
    """Write the tree image; return 0, or the exit code of the failure (D-043).

    Recursion too deep to draw is 1; a Graphviz, `dot` or file problem is 2.
    """
    if png_path is None:
        print("error: --tree-png needs a PATH", file=sys.stderr)
        return EXIT_USAGE
    try:
        export_png(tree, png_path)
    except RecursionError:
        print("error: cannot draw PNG: tree nested too deeply", file=sys.stderr)
        return EXIT_COMPILE_ERROR
    except (RuntimeError, OSError) as exc:
        print(f"error: {one_line(exc)}", file=sys.stderr)
        return EXIT_USAGE
    print(f"wrote {png_path}", file=sys.stderr)
    return EXIT_OK


def read_source(path: str) -> str | None:
    """Return the file text, or None if it cannot be read as UTF-8 text."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read '{path}': {one_line(exc)}", file=sys.stderr)
        return None


def run(path: str, flags: set[str], png_path: str | None = None) -> int:
    """Compile one file and print the requested sections. Returns the exit code.

    `png_path` is the PATH argument of --tree-png (D-019); `flags` holds the flag names.
    Sections are built before anything is printed, so a failure cannot leave half an output.
    """
    source = read_source(path)
    if source is None:
        return EXIT_USAGE
    try:
        compiled = run_pipeline(source)
        sections, tree_ok = build_sections(compiled, flags)
    except RecursionError:
        # Safety net (SPEC section 9: never crash): nothing has been printed yet.
        print("error: program is nested too deeply to process (recursion limit exceeded)",
              file=sys.stderr)
        return EXIT_COMPILE_ERROR
    print("\n\n".join(sections))
    code = EXIT_COMPILE_ERROR if compiled.errors.has_errors() or not tree_ok else EXIT_OK
    if "--tree-png" in flags:
        code = max(code, write_png(compiled.tree, png_path))
    return code


# ------------------------------------------------------------------ arguments

def parse_args(argv: list[str]) -> tuple[str, set[str], str | None] | None:
    """Split argv into (path, flags, png_path) in any order; None on a usage error.

    `--tree-png` must be followed by a PATH (not a flag); the PATH is not the source file.
    """
    paths: list[str] = []
    flags: set[str] = set()
    png_path = None
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--tree-png":
            if index + 1 >= len(argv) or argv[index + 1].startswith("-"):
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
