"""Static code review of `src/*.py` against Project Rule 10 (Phase 8).

Checks every Python file in `src/` for:
1. Functions or methods over 40 lines (`end_lineno - lineno + 1 > 40`).
2. Public modules, classes, functions, or methods without a docstring.
Report only — does not modify any source file.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
MAX_LINES = 40


def review_sources() -> tuple[list[tuple[str, str, int, int, int]], list[tuple[str, str, str, int]], list[tuple[str, str, int, int, int]]]:
    """Scan `src/*.py`; return (over_40, missing_docstrings, all_functions)."""
    over_40: list[tuple[str, str, int, int, int]] = []
    missing_docs: list[tuple[str, str, str, int]] = []
    all_funcs: list[tuple[str, str, int, int, int]] = []

    for path in sorted(SRC_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        rel = f"src/{path.name}"

        if path.name != "__init__.py" and not ast.get_docstring(tree):
            missing_docs.append((rel, "module", path.name, 1))

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if not node.name.startswith("_") and not ast.get_docstring(node):
                    missing_docs.append((rel, "class", node.name, node.lineno))
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        qname = f"{node.name}.{item.name}"
                        length = (item.end_lineno or item.lineno) - item.lineno + 1
                        all_funcs.append((rel, qname, item.lineno, item.end_lineno or item.lineno, length))
                        if length > MAX_LINES:
                            over_40.append((rel, qname, item.lineno, item.end_lineno or item.lineno, length))
                        if not item.name.startswith("_") and not ast.get_docstring(item):
                            missing_docs.append((rel, "method", qname, item.lineno))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                all_funcs.append((rel, node.name, node.lineno, node.end_lineno or node.lineno, length))
                if length > MAX_LINES:
                    over_40.append((rel, node.name, node.lineno, node.end_lineno or node.lineno, length))
                if not node.name.startswith("_") and not ast.get_docstring(node):
                    missing_docs.append((rel, "function", node.name, node.lineno))

    return over_40, missing_docs, all_funcs


def main() -> int:
    """Print the code review report to stdout."""
    over_40, missing_docs, all_funcs = review_sources()
    print(f"Scanned {len(list(SRC_DIR.glob('*.py')))} files in src/, {len(all_funcs)} functions/methods total.")
    print(f"Functions over {MAX_LINES} lines: {len(over_40)}")
    for rel, name, start, end, length in over_40:
        print(f"  - {rel}:{start}-{end}  {name} ({length} lines)")
    print(f"Public classes/functions/methods without a docstring: {len(missing_docs)}")
    for rel, kind, name, line in missing_docs:
        print(f"  - {rel}:{line}  {kind} {name}")
    print("Top 5 longest functions/methods in src/:")
    for rel, name, start, end, length in sorted(all_funcs, key=lambda x: (-x[4], x[0], x[2]))[:5]:
        print(f"  - {rel}:{start}-{end}  {name}: {length} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
