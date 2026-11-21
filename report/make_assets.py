"""Generate report assets from real compiler runs into `report/assets/` (Phase 8).

Assets generated:
1. Parse tree PNGs:
   - `tree_spec_full.png`: full SPEC section 14 program (`samples/valid_program.sl`)
   - `tree_spec_main.png`: `main` `FunctionDecl` subtree of the SPEC section 14 program
   - `tree_expr_a_plus_b_mul_c.png`: the expression `a + b * c` (`BinaryOp` subtree)
   - `tree_syntax_error_partial.png`: partial parse tree from `samples/errors_lexical_syntax.sl`
2. CLI output captures (`.txt`) for each of the five samples in `samples/`:
   - `cli_valid_program.txt`
   - `cli_errors_lexical_syntax.txt`
   - `cli_errors_semantic.txt`
   - `cli_valid_all_tokens.txt`
   - `cli_invalid_lexical.txt`
3. TAC output for the SPEC section 14 program:
   - `spec_program.tac`
"""
import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ast_nodes import FunctionDecl, Return  # noqa: E402
from src.errors import ErrorCollector  # noqa: E402
from src.lexer import tokenize  # noqa: E402
from src.main import run  # noqa: E402
from src.parser import parse  # noqa: E402
from src.semantic import analyze  # noqa: E402
from src.tacgen import generate  # noqa: E402
from src.tree_export import export_png  # noqa: E402

ASSETS_DIR = ROOT / "report" / "assets"
SAMPLES_DIR = ROOT / "samples"


def parse_text(source: str):
    """Tokenize and parse `source`, returning `(tree, errors)`."""
    errors = ErrorCollector()
    tokens = tokenize(source, errors)
    tree = parse(tokens, errors)
    return tree, errors


def make_tree_pngs() -> list[Path]:
    """Generate the four required parse-tree PNGs."""
    created: list[Path] = []

    spec_source = (SAMPLES_DIR / "valid_program.sl").read_text(encoding="utf-8")
    spec_tree, spec_errors = parse_text(spec_source)
    assert not spec_errors.has_errors()

    full_png = ASSETS_DIR / "tree_spec_full.png"
    export_png(spec_tree, str(full_png))
    created.append(full_png)

    main_fn = next(
        item for item in spec_tree.items
        if isinstance(item, FunctionDecl) and item.name == "main"
    )
    main_png = ASSETS_DIR / "tree_spec_main.png"
    export_png(main_fn, str(main_png))
    created.append(main_png)

    expr_source = "int f(int a, int b, int c) { return a + b * c; }\n"
    expr_tree, expr_errors = parse_text(expr_source)
    assert not expr_errors.has_errors()
    fn_decl = expr_tree.items[0]
    assert isinstance(fn_decl, FunctionDecl)
    ret_stmt = fn_decl.body.statements[0]
    assert isinstance(ret_stmt, Return)
    expr_png = ASSETS_DIR / "tree_expr_a_plus_b_mul_c.png"
    export_png(ret_stmt.value, str(expr_png))
    created.append(expr_png)

    bad_source = (SAMPLES_DIR / "errors_lexical_syntax.sl").read_text(encoding="utf-8")
    bad_tree, bad_errors = parse_text(bad_source)
    assert bad_errors.has_kind("Syntax")
    partial_png = ASSETS_DIR / "tree_syntax_error_partial.png"
    export_png(bad_tree, str(partial_png))
    created.append(partial_png)

    return created


def make_cli_captures() -> list[Path]:
    """Run `src.main.run` on each of the five samples and save stdout to `.txt` files."""
    samples = (
        ("valid_program.sl", 0),
        ("errors_lexical_syntax.sl", 1),
        ("errors_semantic.sl", 1),
        ("valid_all_tokens.sl", 0),
        ("invalid_lexical.sl", 1),
    )
    created: list[Path] = []
    for filename, expected_code in samples:
        sample_path = SAMPLES_DIR / filename
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            code = run(str(sample_path), set())
        assert code == expected_code, f"{filename}: expected exit {expected_code}, got {code}"
        assert err_buf.getvalue() == ""
        out_path = ASSETS_DIR / f"cli_{Path(filename).stem}.txt"
        out_path.write_text(out_buf.getvalue(), encoding="utf-8")
        created.append(out_path)
    return created


def make_spec_tac() -> Path:
    """Compile `samples/valid_program.sl` (SPEC section 14) and write `spec_program.tac`."""
    spec_source = (SAMPLES_DIR / "valid_program.sl").read_text(encoding="utf-8")
    tree, errors = parse_text(spec_source)
    analyze(tree, errors)
    assert not errors.has_errors()
    tac_lines = generate(tree)
    out_path = ASSETS_DIR / "spec_program.tac"
    out_path.write_text("\n".join(tac_lines) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    """Generate all report assets and print their paths and byte sizes."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    created = make_tree_pngs() + make_cli_captures() + [make_spec_tac()]
    for path in created:
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
