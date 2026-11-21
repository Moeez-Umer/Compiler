# PROGRESS: SmartLang Compiler

Deadline: Dec 5, 2026. Tick a phase only after the user has verified it.

## Phase checklist

- [x] Phase 0: Scaffold and shared foundation (Nov 14 to 16) - verified and committed (`dd89427`, tag `phase-0`)
- [x] Phase 1: Lexical analyzer (Nov 17 to 18) - committed (`6eb841c`, `3ff3215`), tag `phase-1` (per `git log`)
- [~] Phase 2: Parser and parse tree (Nov 19 to 22) - committed (`efc5123` labelled "Phase 0 corrections", then `dd69ba0`), tag `phase-2` (per `git log`); box left `[~]` until you confirm verification
- [~] Phase 3: Syntax error detection and recovery (Nov 23 to 24) - committed (`ad37d5f`), tag `phase-3` (per `git log`); box left `[~]` until you confirm verification
- [~] Phase 4: Symbol table (Nov 25) - committed (`d43c03b`), tag `phase-4` (per `git log`); box left `[~]` until you confirm verification
- [~] Phase 5: Semantic analyzer (Nov 26 to 29)
  - [~] 5a: scopes, declarations, expression typing - committed (`e515e18`, tag `phase-5a`, per `git log`); box left `[~]` until you confirm verification
  - [~] 5b: callee, arity and argument types, return checks, missing return - committed (`f40c71c`, tag `phase-5b`, per `git log`); box left `[~]` until you confirm verification
- [~] Phase 6: Three-address code generator (Nov 30 to Dec 1) - committed (`ff904c9`, tag `phase-6`, per `git log`); box left `[~]` until you confirm verification
- [~] Phase 7: CLI integration and output polish (Dec 1 to 2) - committed (`03891e9`, tag `phase-7`, per `git log`); box left `[~]` until you confirm verification
- [~] Phase 8: Test suite, hardening, clean-clone check (Dec 2 to 3) - committed (`6a4af9a`), tag `phase-8` (per `git log`); Phase 8b (Python 3.10+ version guard in `src/main.py`, `README.md` setup update, `requirements.txt` minimum pins, `Decisions.md` D-047 to D-049) built and awaiting your verification and commit; box left `[~]` until you confirm verification
- [ ] Phase 9: Report and viva prep (Dec 3 to 4)

## Open issues

- Phase 8b (D-047, D-048, D-049): added startup `sys.version_info < (3, 10)` guard in `src/main.py` before `from src...` imports (prints one line to `stderr` with the found version and exits with code 2; protects `python src/main.py` only, while `pytest` on Python 3.9 still fails at collection); updated `README.md` to state the Python 3.10+ requirement (developed and tested on 3.12) and warn that macOS's default `python3` may be too old; pinned `graphviz>=0.20` and `pytest>=8` in `requirements.txt`; logged D-047, D-048, and D-049 (`report/assets/*.png` committed and removed from `.gitignore`).

- Phase 8 (D-044): `tests/test_programs.py` and `tests/pipeline_helper.py` run all 104 `.sl` files (`tests/valid`: 11, `tests/invalid`: 84, `tests/golden`: 9) through `tokenize`, `parse`, `analyze`, and `generate` directly. Every existing `.sl` file already had a valid `// EXPECT:` header (0 files lacked a header). Added 4 new edge-case `.sl` files (`valid/edge_comments_only.sl`, `valid/edge_tabs.sl`, `invalid/edge_empty_function_body.sl`, `invalid/edge_empty_function_body_literal.sl`). Because `edge_comments_only.sl` intentionally has 0 code tokens and empty TAC, `test_lexer.py::test_valid_files_have_no_lexical_errors` (`len(tokens) > 10`) and `test_tacgen.py::test_all_valid_programs_generate_nonempty_tac` (`len(tac) > 0`) exclude that one file while `test_programs.py` and `test_edge_cases.py` test it end-to-end.
- Phase 8 (D-045): Approved 1-line `encoding="utf-8-sig"` change applied in `src/main.py:read_source`; a leading UTF-8 BOM is stripped without shifting line-1 columns while an interior BOM remains a lexical error.
- Phase 8 (D-046): `tests/test_fuzz_pipeline.py` runs 1500 random raw-text inputs (`{'lexical': 1423, 'syntax': 58, 'tac': 19}`) and 4000 source-offset mutants (`{'lexical': 35, 'syntax': 2702, 'semantic': 816, 'tac': 447}`) with `random.Random(426)` and a 2.0 s per-case `SIGVTALRM` timer; 0 bugs found in `src/`. Two deliberately injected bugs (in `src/tacgen.py` and `src/semantic.py`) were caught by the fuzzer and immediately reverted.
- Phase 8: `report/make_test_table.py` generated `report/assets/test_table.md` (104/104 PASS); `report/make_assets.py` generated 4 parse-tree PNGs, 5 CLI output `.txt` captures, and `spec_program.tac` in `report/assets/`; `report/code_review.py` audited `src/*.py` (0 functions over 40 lines; max is 27 lines in `src/symbol_table.py:_format_scope`; 0 missing docstrings after adding the 22 approved one-line docstrings to `label`/`children` in `src/ast_nodes.py`).
- Phase 8: `README.md` CLI examples were re-run and verified byte-for-byte against actual CLI output.
- Phase 7 (D-041): flags only choose what is printed; the lexer and parser always run, semantic only without Lexical/Syntax errors, TAC only without errors. Tests changed by this: `test_cli_tokens_only_still_runs_semantic_stage` (was "--tokens alone does not run the semantic stage"), `--tokens` added to the flag sets of two section-order tests (TOKENS is no longer always printed).
- Phase 7 (D-042): all CLI tests moved to `tests/test_cli.py` (paths made absolute via `Path(__file__)`); the deep-chain `--tree` tests now expect `(skipped: nested too deeply to print)`, exit 1 and empty stderr (resolves the D-037 caveat).
- Phase 7 (D-043): `--tree-png` writes `wrote PATH` to stderr (stdout identical); PNG errors exit 1 (too deep) or 2 (Graphviz/dot/file) and never hide sections.
- Phase 7 (not changed, out of scope): `tests/test_syntax_errors.py` still holds one CLI test (`test_deep_nesting_gives_one_error_and_exit_code_1`); it passes unchanged. `tree_export.py` is still recursive, so trees about 3000 deep cannot be printed or drawn.
- Phase 7: `samples/` has five files: three end-to-end demos (`valid_program.sl`, `errors_lexical_syntax.sl`, `errors_semantic.sl`) and two lexer demos (`valid_all_tokens.sl`, `invalid_lexical.sl`), plus `valid_program_tree.png` (an old Phase 2 output).

- Phase 6 (D-038): assignments and initialized declarations always emit a copy instruction (`t2 = a + t1`, then `x = t2`), and `else-if` chains preserve stacked closing labels (`L6:`, `L4:`, `L2:`) without peephole merging (optimization is out of scope, SPEC section 15).
- Phase 6 (D-039): `generate(tree)` raises `ValueError` if any `VarDecl`, `Assign`, or `Identifier` has `tac_name=None` (no silent fallback to `node.name`). Notice also that because `semantic.py` assigns `tac_name` from a program-wide `used_names` set (D-029), a local variable whose name appeared as a parameter in an earlier function gets `name_1` (observed in `tests/golden/calls.tac`: `a_1`, `b_1` in `main` after `combine(int a, int b)`).
- Phase 6 (D-040): because `tokenize`, `parse_binary_level`, `type_binary`, and `gen_binary` all use iterative left-spine loops, a 3000-term `1 + 1 + ... + 1` chain run with `--tac` alone succeeds (exit 0); running it with `--tree --tac` hits `tree_to_text`'s recursion limit and exits 1 with the one-line error from D-037.

- Phase 5b (D-035): missing return is strict: an if/else where BOTH branches return, a trailing `{ return 1; }` block, and a trailing loop with a return all still report `Missing return`.
- Phase 5b (D-036): after an arity error the per-argument type check is skipped (one mistake, one message); a call to a variable has type `error`.
- Phase 5b (D-037): the 3000-term `--tree` / `--tree-png` crash (RecursionError in `tree_export.py`, not touched) is now one stderr line and exit 1. With `--tree-png` the `== ERRORS == (none)` section is printed before the failure, which can look like success; stderr and exit code say otherwise. Making `tree_export` iterative is not done.
- Phase 5b (D-034): approved parser change `Block.end_line/end_col`; the full suite stayed green right after (479 passed), no test in `test_parser.py`/`test_syntax_errors.py` was edited.
- Phase 5b: one 5a test helper changed: `type_of` in `tests/test_semantic.py` ignores `Cannot return ...` messages because those typing probes return float/bool from `int main`.
- Phase 5a (D-030): declaration errors (initializer mismatch, const without initializer, redeclaration) are reported at the declaration's first token (`int`/`const`), not at the name; assignment-statement errors are at the name.
- Phase 5a (D-032): the analyzer crashed on an 800-term `1+1+...` chain during testing (my own code); fixed with a left-spine loop and a `RecursionError` safety net; 900 stacked unary minus signs give one `Program is nested too deeply to analyze` error.
- Phase 5a: with only `--tokens` (or no parser flag) the semantic stage does not run (D-019/D-031); Phase 7 makes the full pipeline the default.
- Phase 5a: `tests/valid/*.sl` are now checked by the semantic analyzer (`test_valid_files_have_no_errors`); all existing files passed without edits.
- Git: Phase 2 commit message is misleading (`efc5123` "Phase 0 corrections"); not rewritten by the agent.
- Phase 4 (D-027): `SymbolTable` starts with no active scopes (`current_level() == -1`) and requires `enter_scope("global")` to open `Scope 0 (global)`; `declare()` sets `symbol.scope_level` to the current scope level so a stored symbol never disagrees with its scope. `symbol_table.py` is standalone in Phase 4 and will be wired into `semantic.py` and `main.py --symbols` in Phase 5.
- Phase 3 (D-023): a genuine syntax error directly after an INVALID token is hidden (D-020); documented limitation with a test.
- Phase 3 (D-025): the partial tree drops failed statements and loses the node of a failed `if`/`while`/`for` header; nesting deeper than about 330 levels gives one `nested too deeply` error.
- Phase 3 (D-024): a clearly forgotten `;` is inserted (nothing skipped); same-line junk after a statement still skips it.
- Phase 3 (D-026): root `conftest.py` adds a 10-second `SIGALRM` per-test timeout (`TimeoutExceeded`), no-op on Windows.
- Phase 3: the parser runs only with `--tree`/`--tree-png`, so syntax errors are only visible with those flags until Phase 7.
- Phase 3: `src/parser.py` was the only source file changed; `Parser.__init__` now takes `(tokens, errors)` (internal; `parse()` is unchanged).
- Phase 2: `--tree-png` output (`samples/valid_program_tree.png`) is about 175 KB, 3112 x 827 px, wide but readable when zoomed.
- Unterminated char literal swallows the rest of its line, and unterminated `/*` swallows the rest of the file (D-013); known limitation.
- `tests/valid/*.sl` now pass the parser but are not yet checked by the semantic analyzer (D-016); `parser_*.sl` were written to be type-correct.

## Later

- Phase 5b MUST items: all done in 5b (see D-033 to D-037); `test_5b_not_checked_yet` was deleted.
- Parser (later, needs approval): store the NAME position on `VarDecl` and `Param` so declaration errors can point at the name instead of the type keyword (D-030).
- Phase 7: done (parser in the default pipeline, flag handling replaced, no flag means `--all`; D-041).
- Phase 8: done (`test_programs.py`, `test_edge_cases.py`, `test_fuzz_pipeline.py`, `report/make_test_table.py`, `report/make_assets.py`, `report/code_review.py`, approved `utf-8-sig` in `src/main.py` and 22 one-line docstrings in `src/ast_nodes.py`; D-044 to D-046; committed as `6a4af9a`, tag `phase-8`).
- Phase 8b: done (Python 3.10+ startup guard in `src/main.py`, `README.md` Python 3.10+/macOS `python3` note, `requirements.txt` pins `graphviz>=0.20` and `pytest>=8`, `Decisions.md` D-047 to D-049).
- Phase 9: term project report and viva preparation using the assets in `report/assets/`.

## Next step

Verify Phase 8b yourself: `source .venv/bin/activate && pytest -q`, `git diff`, `git status`.
Then commit (`phase-8b: Python 3.10+ version guard, README setup note and pinned requirements`) and optionally tag `git tag phase-8b`.
Then Phase 9 (report and viva prep).

## Hand-traced golden file walk-through (viva reference)

File: [nested_loops.sl](file:///Users/moeezumer/Documents/smartlang/tests/golden/nested_loops.sl) → [nested_loops.tac](file:///Users/moeezumer/Documents/smartlang/tests/golden/nested_loops.tac)

Source:
```c
// EXPECT: OK
int main() {
    int total = 0;
    for (int i = 0; i < 3; i = i + 1) {
        int j = 0;
        while (j < 2) {
            if (i == j) {
                total = total + 10;
            } else {
                total = total + 1;
            }
            j = j + 1;
        }
    }
    return total;
}
```

Step-by-step trace through `TACGenerator`:
1. **`gen_globals(tree.items)`**: no top-level `VarDecl` exists, so `globals:` is not emitted.
2. **`gen_function(main)`**: emits `func main:` at column 0.
3. **`int total = 0;`** (`gen_var_decl`): `Literal("0")` returns `"0"` (no temporary); emits `  total = 0`.
4. **Outer `for (int i = 0; i < 3; i = i + 1)`** (`gen_for`):
   - `init` (`int i = 0`): emits `  i = 0`.
   - Allocates `start_label = L1`, `end_label = L2` **before** generating the condition, body, or update (D-039).
   - Emits `L1:`.
   - `condition` (`i < 3`): `gen_binary` allocates `t1`, emits `  t1 = i < 3`, returns `"t1"`.
   - Emits `  ifFalse t1 goto L2`.
5. **Outer `for` body**:
   - `int j = 0;`: emits `  j = 0`.
   - **Inner `while (j < 2)`** (`gen_while`):
     - Allocates `start_label = L3`, `end_label = L4` **before** generating its body.
     - Emits `L3:`.
     - `condition` (`j < 2`): allocates `t2`, emits `  t2 = j < 2`, returns `"t2"`.
     - Emits `  ifFalse t2 goto L4`.
   - **Innermost `if (i == j) { ... } else { ... }`** (`gen_if`):
     - `condition` (`i == j`): allocates `t3`, emits `  t3 = i == j`, returns `"t3"`.
     - Allocates `else_label = L5`, `end_label = L6`.
     - Emits `  ifFalse t3 goto L5`.
     - `then_block` (`total = total + 10;`): allocates `t4`, emits `  t4 = total + 10`, then `  total = t4`.
     - Emits `  goto L6` to jump over the `else` branch.
     - Emits `L5:`.
     - `else_branch` (`total = total + 1;`): allocates `t5`, emits `  t5 = total + 1`, then `  total = t5`.
     - Emits `L6:`.
   - **`j = j + 1;`** (end of `while` body): allocates `t6`, emits `  t6 = j + 1`, then `  j = t6`.
   - End of `gen_while`: emits `  goto L3`, then `L4:`.
6. **Outer `for` update and back-edge**:
   - `update` (`i = i + 1`): allocates `t7`, emits `  t7 = i + 1`, then `  i = t7`.
   - Emits `  goto L1`, then `L2:`.
7. **`return total;`** and end of function: emits `  return total`, then `endfunc` at column 0.
