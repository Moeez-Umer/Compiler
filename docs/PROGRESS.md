# PROGRESS: SmartLang Compiler

Deadline: Dec 5, 2026. Tick a phase only after the user has verified it.

## Phase checklist

- [x] Phase 0: Scaffold and shared foundation (Nov 14 to 16) - verified and committed (`dd89427`, tag `phase-0`)
- [~] Phase 1: Lexical analyzer (Nov 17 to 18) - built, 151 tests pass (full suite), awaiting user verification and commit
- [ ] Phase 2: Parser and parse tree (Nov 19 to 22)
- [ ] Phase 3: Syntax error detection and recovery (Nov 23 to 24)
- [ ] Phase 4: Symbol table (Nov 25)
- [ ] Phase 5: Semantic analyzer (Nov 26 to 29)
- [ ] Phase 6: Three-address code generator (Nov 30 to Dec 1)
- [ ] Phase 7: CLI integration and output polish (Dec 1 to 2)
- [ ] Phase 8: Test suite, hardening, clean-clone check (Dec 2 to 3)
- [ ] Phase 9: Report and viva prep (Dec 3 to 4)

## Open issues

- `brew install graphviz` was not run (global install, outside the rules); the `dot` binary is not verified yet (needed in Phase 2).

- Unterminated char literal swallows the rest of its line, and unterminated `/*` swallows the rest of the file (D-013); known limitation.
- `tests/valid/tokens_*.sl` are not yet checked by a parser or semantic analyzer (D-016).

## Later

- Phase 2 needs the `dot` binary (`brew install graphviz`) for `--tree-png`.
- Phase 2: parser must skip INVALID tokens silently (interfaces.md); re-run `tests/valid/*.sl` through the parser.
- Phase 3: syntax tests that contain INVALID tokens may produce follow-on syntax errors; decide how to handle them.
- Phase 7: replace the Phase 1 flag handling in `main.py` (D-015); no flag must mean `--all`.
- Phase 8: `test_programs.py` should run `tests/valid` and `tests/invalid` end to end (EXPECT lines are already in place for lexical cases).

## Next step

Verify Phase 1 follow-up yourself: `source .venv/bin/activate && pytest -v`, check `git status` and `git diff`,
then commit and update the tag if desired.
Then Phase 2: Parser and parse tree, in a fresh conversation.
