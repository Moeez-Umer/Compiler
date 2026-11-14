# PROJECT RULES: SmartLang Compiler (standing rules, every session)

## Start of every session
1. Read `docs/SPEC.md`, `docs/interfaces.md`, `docs/Decisions.md`, `docs/Flow.md`, `docs/PROGRESS.md`.
2. State the current phase and restate its goal in 2 to 3 lines.
3. Do ONLY the phase the user names. Never start the next phase. Note future needs under "Later" in PROGRESS.md.

## Plan first
4. Show a numbered plan (files to touch, tests to write, risks) and WAIT for the user to say "go".
5. Touch only the folders and files named in the phase scope. If something outside scope needs changing, ask.

## Build
6. Tests first for pure logic (lexer, symbol table, type rules). Write the failing test, then the code.
7. Follow `docs/interfaces.md` exactly. Never change a frozen interface without approval and a Decisions.md entry.
8. Never add language features that are not in SPEC.md (see SPEC section 15).
9. Python 3.12, standard library plus `graphviz` and `pytest` only. No lexer or parser generators.
10. Code must be explainable in a viva: functions under about 40 lines, one job each, parser methods named
    after grammar rules (`parse_if_stmt`), a docstring on every class and function that names the grammar
    rule or type rule it implements, comments that explain WHY. No metaprogramming, no clever one-liners.
11. Errors go through `ErrorCollector` using the exact format in SPEC section 9. No `print` in library code
    (only `main.py` prints). The compiler must never crash or hang on any input.
12. No global mutable state. Pass collectors and tables explicitly.
13. `src/main.py` grows one stage per phase (tokens in Phase 1, tree in Phase 2, and so on) so every phase
    has something runnable to verify. The full CLI polish happens in its own phase.

## Verify with real output
14. Run the commands. Paste VERBATIM output (pytest, CLI runs). Never reconstruct, summarize or paraphrase
    command output. If you did not run it, say you did not run it.
15. Run the FULL test suite at the end of every phase, not only the new tests.
16. Treat suspiciously easy results as suspect (everything passes first try, zero errors on a bad file,
    empty output). Explain them before accepting them.
17. End every phase report with a section "NOT OBSERVED / UNVERIFIED": what you did not run or cannot prove.

## Update the docs (end of every phase, without being asked)
18. `docs/PROGRESS.md`: tick the phase checklist, list open issues and bugs, give the next step.
19. `docs/Decisions.md`: one entry per non-obvious choice: context, options considered, decision, trade-offs.
    Record cuts and limitations honestly (documented trade-offs are good prioritization).
20. `docs/Flow.md`: tag sections `[PLANNED]` until built, then `[BUILT]`. Keep the pipeline diagram (Mermaid)
    and the data each stage passes on current.
21. If a bug from an earlier phase appears: report it, log it in Decisions.md and PROGRESS.md, fix it only after approval.

## Git
22. Do NOT commit or tag. At the end of a phase propose the commit message `phase-N: <summary>` and the tag
    `git tag phase-N`. The user commits after verifying.

## Stop and ask when
23. A requirement is ambiguous or SPEC and code disagree.
24. A test fails after two fix attempts: stop, state your root-cause hypothesis, ask for direction. Do not rewrite large parts.
25. You want to add a dependency, rename or delete files, or change the folder tree.

## Safety
26. No destructive commands (`rm -rf`, `sudo`, force git operations, global installs). Use `.venv` only.

## Report format at the end of each phase
- Files created or changed
- VERBATIM test and CLI output
- Decisions made (with Decisions.md entry ids)
- NOT OBSERVED / UNVERIFIED
- Proposed commit message and tag

27. At the start of every session run `git status` and `git log --oneline --decorate -5` and paste the output
    VERBATIM. Never describe git state (committed, pushed, tagged) from memory or from docs. If a doc says
    something about git state that the commands contradict, fix the doc.