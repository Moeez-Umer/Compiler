# PROGRESS: SmartLang Compiler

Deadline: Dec 5, 2026. Tick a phase only after the user has verified it.

## Phase checklist

- [x] Phase 0: Scaffold and shared foundation (Nov 14 to 16) - verified and committed (`dd89427`, tag `phase-0`)
- [x] Phase 1: Lexical analyzer (Nov 17 to 18) - committed (`6eb841c`, `3ff3215`), tag `phase-1` (per `git log`)
- [~] Phase 2: Parser and parse tree (Nov 19 to 22) - committed (`efc5123` labelled "Phase 0 corrections", then `dd69ba0`), tag `phase-2` (per `git log`); box left `[~]` until you confirm verification
- [~] Phase 3: Syntax error detection and recovery (Nov 23 to 24) - committed (`ad37d5f`), tag `phase-3` (per `git log`); box left `[~]` until you confirm verification
- [~] Phase 4: Symbol table (Nov 25) - built, awaiting your verification and commit (`phase-4`)
- [ ] Phase 5: Semantic analyzer (Nov 26 to 29)
- [ ] Phase 6: Three-address code generator (Nov 30 to Dec 1)
- [ ] Phase 7: CLI integration and output polish (Dec 1 to 2)
- [ ] Phase 8: Test suite, hardening, clean-clone check (Dec 2 to 3)
- [ ] Phase 9: Report and viva prep (Dec 3 to 4)

## Open issues

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

- Phase 5: wire `SymbolTable` into `src/semantic.py` and add `--symbols` to `src/main.py`.
- Phase 7: the parser currently only runs with `--tree`/`--tree-png`; make it part of the default pipeline.
- Phase 7: replace the Phase 1 flag handling in `main.py` (D-015); no flag must mean `--all`.
- Phase 8: `test_programs.py` should run `tests/valid` and `tests/invalid` end to end (EXPECT lines are in place for lexical and syntax cases; `test_syntax_errors.py` already checks the syntax ones).

## Next step

Verify Phase 4 yourself: `source .venv/bin/activate && pytest -v`, `git status`.
Then commit (`phase-4: symbol table with lexical scope stack and history dump`) and `git tag phase-4`.
Then Phase 5: semantic analyzer, in a fresh conversation.
