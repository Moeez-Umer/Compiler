# DECISIONS: SmartLang Compiler

One entry per non-obvious choice: context, options considered, decision, trade-offs.
Changes to SPEC.md or frozen interfaces must be logged here.

---

## D-001 Python 3.12 over C/C++ with Flex/Bison

- **Context**: CS426 term project (10 marks, due Dec 5, 2026), team of 2 or 3, code defended in a viva.
  Development machine is macOS (Apple Silicon M4). The deliverable is a compiler front-end, not a fast one.
- **Options considered**:
  1. C or C++ with Flex and Bison (the traditional toolchain).
  2. Python 3.12, hand-written, standard library plus `graphviz` and `pytest`.
  3. Java or another JVM language with a generator such as ANTLR.
- **Decision**: Python 3.12 (SPEC section 3).
- **Trade-offs**:
  - (+) Short, readable code that is easy to explain in a viva; fast edit-test loop; `pytest` for tests;
    `graphviz` for parse-tree PNGs.
  - (+) No build system or memory-management bugs to debug.
  - (-) Slower at run time (irrelevant at this input size).
  - (-) No static typing enforced; mitigated by dataclasses and type hints.
  - (-) Does not exercise the Flex/Bison workflow taught in some courses; D-002 explains why this is intended.

## D-002 Hand-written lexer and recursive descent LL(1) parser over generators

- **Context**: The grammar (SPEC section 6) is already LL(1), left recursion removed and left-factored.
  The project rules forbid ply, lark, antlr, flex, bison and any other generator.
- **Options considered**:
  1. Lexer and parser generators (Flex/Bison, ply, lark, ANTLR).
  2. Hand-written lexer plus table-driven LL(1) parser.
  3. Hand-written lexer plus recursive descent parser, one method per grammar rule.
- **Decision**: Hand-written lexer and recursive descent parser, methods named after grammar rules
  (for example `parse_if_stmt`).
- **Trade-offs**:
  - (+) Code mirrors the grammar one-to-one, so it can be explained and traced by hand in a viva.
  - (+) Full control over error messages and recovery (see D-003).
  - (+) Demonstrates the course concepts directly instead of hiding them in a tool.
  - (-) More code to write and test than a generator.
  - (-) Grammar changes must be mirrored manually in the parser.
  - (-) Limited to one token of lookahead; acceptable because the grammar is LL(1).

## D-003 Panic-mode error recovery

- **Context**: SPEC section 9 requires collecting as many independent errors as possible per run, and the
  compiler must never crash or hang.
- **Options considered**:
  1. Stop at the first syntax error.
  2. Panic mode: record the error, skip to a synchronizing token, continue.
  3. Phrase-level recovery (local repair such as inserting a missing `;`).
  4. Error productions in the grammar.
- **Decision**: Panic mode. A private `ParseError` is raised, caught at statement or top-level boundaries,
  and the parser skips to `;`, `}` or a statement-starting keyword. Every recovery must consume at least
  one token or reach EOF, which guarantees forward progress.
- **Trade-offs**:
  - (+) Simple, predictable, easy to prove terminating.
  - (+) Reports several independent errors in one run.
  - (-) Can skip valid code after the first error and may produce follow-on errors.
  - (-) Less precise than phrase-level repair. Accepted for a term project.

## D-004 Parse tree collapses single-child expression chains

- **Context**: Precedence is implemented by rule layering (`orExpr` to `andExpr` to ... to `primary`).
  A literal `5` would otherwise produce a ten-level chain of single-child nodes.
- **Options considered**:
  1. Full concrete parse tree with every grammar level.
  2. Abstract syntax tree with only meaningful nodes (`BinaryOp`, `UnaryOp`, `Literal`, ...).
  3. Concrete tree with an extra export-time collapsing pass.
- **Decision**: Parser builds nodes only when an operator is actually applied; a level with a single
  operand returns that operand unchanged (SPEC section 7, `ast_nodes.py` in interfaces.md).
- **Trade-offs**:
  - (+) Readable tree output and PNG; simpler semantic analyzer and TAC generator.
  - (-) The tree is not a literal derivation tree, so the precedence layers are not visible in it.
    They are documented separately in the report diagrams (Phase 9).

## D-005 No short-circuit evaluation in TAC (`&&` and `||` are plain binary ops)

- **Context**: SPEC section 11 defines TAC. Real languages evaluate `a && b` lazily, which needs
  extra labels and jumps.
- **Options considered**:
  1. Short-circuit translation with jumps and labels.
  2. Emit `x = y && z` and `x = y || z` as ordinary binary instructions.
- **Decision**: Option 2. SmartLang has no side-effecting expressions except function calls, and no
  output statements, so this is a simplification rather than a visible bug.
- **Trade-offs**:
  - (+) Uniform instruction set; simpler generator and golden tests.
  - (-) Semantics differ from C/Java when the right operand has side effects, for example a call that
    would not run under short-circuit rules. Listed under "Known limitations".

## D-006 Lexical and syntax errors skip semantic analysis and TAC

- **Context**: A tree built after a lexical or syntax error is partial. Semantic checks on it would
  produce misleading follow-on errors.
- **Options considered**:
  1. Always run every stage, whatever the errors.
  2. Stop after parsing when there are lexical or syntax errors; stop before TAC when there are
     semantic errors.
- **Decision**: Option 2 (SPEC section 9). Tokens are always printed; the tree is printed if the parser
  produced one. Exit code is 1 on any compile error.
- **Trade-offs**:
  - (+) No cascading, confusing diagnostics; TAC precondition (zero errors) always holds.
  - (-) The user does not see semantic errors until syntax errors are fixed.

## D-007 main.py grows one stage per phase

- **Context**: Every phase should have something runnable to verify (project rule 13), but the full CLI
  needs all stages.
- **Options considered**:
  1. Write `main.py` once at the end.
  2. Add one stage per phase: tokens in Phase 1, tree in Phase 2, symbols in Phase 5, TAC in Phase 6,
     polish in Phase 7.
- **Decision**: Option 2.
- **Trade-offs**:
  - (+) Each phase has an end-to-end check; integration problems appear early.
  - (-) `main.py` is edited in several phases and must be kept consistent with `run()` in interfaces.md.
  - (-) Intermediate CLI behavior (flags, headers) can differ from the final one until Phase 7.

## D-008 Both while and for implemented although the assignment says "OR"

- **Context**: The assignment asks for loops with wording that reads as "while OR for". Either would satisfy it.
- **Options considered**:
  1. Implement only `while`.
  2. Implement only `for`.
  3. Implement both.
- **Decision**: Implement both (SPEC sections 6 and 11).
- **Trade-offs**:
  - (+) Covers either reading of the requirement and shows two loop shapes in TAC.
  - (-) More grammar, semantic rules (the `for` scope) and tests to maintain.
  - (-) Slightly more viva surface area.

## D-009 ErrorCollector.report rejects unknown error kinds

- **Context**: interfaces.md gives `kind` as `"Lexical" | "Syntax" | "Semantic"` but says nothing about other values.
  A typo such as `"Syntx"` would otherwise be stored and then sorted or filtered wrongly.
- **Options considered**:
  1. Accept any string.
  2. Raise `ValueError` on an unknown kind.
- **Decision**: Option 2. The interface signature is unchanged; only invalid input is rejected. It guards programmer
  errors only; lexer, parser and semantic must pass exactly `"Lexical"`, `"Syntax"` or `"Semantic"`.
- **Trade-offs**:
  - (+) A programming mistake fails loudly in tests instead of silently hiding or misplacing an error.
  - (-) A stage with a bug could raise instead of reporting. Compiler stages only pass the three constants, and
    the "never crash on any input" rule concerns user input, not internal misuse.
- **Status**: Accepted by user.

## D-010 [SUPERSEDED by D-011] Tests run with `python -m pytest`, not bare `pytest`

- **Context**: Tests import `from src.errors import ...`. Bare `pytest` does not put the repo root on `sys.path`
  (observed: `ModuleNotFoundError: No module named 'src'`).
- **Options considered**:
  1. Document `python -m pytest` (adds no files).
  2. Add a root `pytest.ini` with `pythonpath = .`.
- **Decision**: Originally Option 1 to stay strictly inside Phase 0 file list. Superseded by D-011 after user
  approved a one-time scope exception for `pytest.ini`.
- **Trade-offs**:
  - (+) No extra config file.
  - (-) Bare `pytest` and `pytest -q` fail for anyone who forgets.

## D-011 Root `pytest.ini` sets `pythonpath = .` and `testpaths = tests`

- **Context**: Phase prompts and verification instructions in `Prompts.md` run bare `pytest -v` and `pytest -q`.
  Without `pythonpath = .`, bare `pytest` fails with `ModuleNotFoundError: No module named 'src'`.
- **Options considered**:
  1. Keep D-010 (`python -m pytest` only).
  2. Add a root `pytest.ini` with `[pytest]`, `pythonpath = .`, `testpaths = tests` (approved as a one-time Phase 0
     scope exception).
- **Decision**: Option 2 (supersedes D-010).
- **Trade-offs**:
  - (+) Both `pytest` and `python -m pytest` work identically from the repo root.
  - (+) Matches the commands in `Prompts.md` without editing the prompts.
  - (-) Adds one small config file at the repo root.
