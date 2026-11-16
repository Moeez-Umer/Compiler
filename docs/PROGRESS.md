# PROGRESS: SmartLang Compiler

Deadline: Dec 5, 2026. Tick a phase only after the user has verified it.

## Phase checklist

- [x] Phase 0: Scaffold and shared foundation (Nov 14 to 16) - verified and committed (`dd89427`, tag `phase-0`)
- [x] Phase 1: Lexical analyzer (Nov 17 to 18) - committed (`6eb841c`, `3ff3215`), tag `phase-1` (per `git log`)
- [~] Phase 2: Parser and parse tree (Nov 19 to 22) - built, 232 tests pass (full suite), awaiting user verification and commit
- [ ] Phase 3: Syntax error detection and recovery (Nov 23 to 24)
- [ ] Phase 4: Symbol table (Nov 25)
- [ ] Phase 5: Semantic analyzer (Nov 26 to 29)
- [ ] Phase 6: Three-address code generator (Nov 30 to Dec 1)
- [ ] Phase 7: CLI integration and output polish (Dec 1 to 2)
- [ ] Phase 8: Test suite, hardening, clean-clone check (Dec 2 to 3)
- [ ] Phase 9: Report and viva prep (Dec 3 to 4)

## Open issues

- Phase 2: `run()` gained an optional `png_path` parameter (D-019); interfaces.md is not edited yet, needs approval.
- Phase 2: only the first syntax error is reported, no recovery (D-018); Phase 3.
- Phase 2: `--tree-png` output (`samples/valid_program_tree.png`) is about 175 KB, 3112 x 827 px, wide but readable when zoomed.

- Unterminated char literal swallows the rest of its line, and unterminated `/*` swallows the rest of the file (D-013); known limitation.
- `tests/valid/*.sl` now pass the parser (Phase 2) but are not yet checked by the semantic analyzer (D-016); `parser_*.sl` were written to be type-correct.

## Later

- Phase 3: add panic-mode recovery on top of `ParseError`; keep tests for INVALID tokens (skipped silently in `Parser.__init__`).
- Phase 7: the parser currently only runs with `--tree`/`--tree-png`; make it part of the default pipeline.
- Phase 3: syntax tests that contain INVALID tokens may produce follow-on syntax errors; decide how to handle them.
- Phase 7: replace the Phase 1 flag handling in `main.py` (D-015); no flag must mean `--all`.
- Phase 8: `test_programs.py` should run `tests/valid` and `tests/invalid` end to end (EXPECT lines are already in place for lexical cases).

## Next step

Verify Phase 2 yourself: `source .venv/bin/activate && pytest -v`, `python src/main.py samples/valid_program.sl --tree`, open
`samples/valid_program_tree.png`, check `git status`, then commit (`phase-2: parser, parse tree, tree export`) and `git tag phase-2`.
Then Phase 3: syntax error detection and recovery, in a fresh conversation.
