# PROGRESS: SmartLang Compiler

Deadline: Dec 5, 2026. Tick a phase only after the user has verified it.

## Phase checklist

- [x] Phase 0: Scaffold and shared foundation (Nov 14 to 16) - built, 17 tests pass, awaiting user verification and commit
- [ ] Phase 1: Lexical analyzer (Nov 17 to 18)
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

## Later

- Phase 2 needs the `dot` binary (`brew install graphviz`) for `--tree-png`.

## Next step

Verify Phase 0 yourself: `source .venv/bin/activate && pytest -q`, read `src/errors.py`, check
`git status` and `git diff --stat`, then commit and tag (`git add -A && git commit -m "phase-0: scaffold, tokens and errors modules with tests" && git tag phase-0`). After that, Phase 1: Lexical analyzer in a fresh conversation.
