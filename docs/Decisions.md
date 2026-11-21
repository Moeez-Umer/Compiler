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


## D-012 Malformed numbers are scanned as one run of digits, letters and dots

- **Context**: SPEC section 5 lists `3.4.5`, `3.`, `.5` and `9abc` as invalid. A naive scanner would split them
  into several small tokens and report several confusing errors.
- **Options considered**:
  1. Scan the longest valid number, then treat the rest as new tokens.
  2. Scan the whole run of `[A-Za-z0-9_.]` that starts with a digit (or with `.` followed by a digit), then
     validate it against `[0-9]+` or `[0-9]+.[0-9]+`.
- **Decision**: Option 2. One bad run is one INVALID token and one error, reported at its first column.
  Messages: `Malformed number 'N'`, and `Number 'N' is glued to letters` when the run contains letters.
- **Trade-offs**:
  - (+) One error per mistake; simple to explain.
  - (-) `3.foo` is one INVALID token (reported as glued to letters).
  - (-) A lone `.` not followed by a digit is an invalid character, not a malformed number.

## D-013 Extent of an invalid char literal or comment

- **Context**: SPEC says to emit an INVALID token for bad char literals and for an unterminated block comment,
  but not how much text the token covers.
- **Decision**:
  - A char literal runs to its closing quote or to the end of the line. An unterminated `'a;` therefore
    swallows the rest of the line (observed in `samples/invalid_lexical.sl`: the `;` is part of the INVALID lexeme).
    A backslash always consumes the next character, so a backslash followed by a quote is an escaped quote.
  - An unterminated `/*` yields one INVALID token with lexeme `/*`, reported at the line and column where
    the comment started; the rest of the file is consumed as comment text.
- **Trade-offs**:
  - (+) One error per bad literal, no cascades, forward progress guaranteed.
  - (-) Code after an unterminated char literal on the same line, or after an unterminated `/*`, is not checked.
    The parser (Phase 3) may report a follow-on syntax error; it skips INVALID tokens silently.

## D-014 Lexical error messages and column rules

- **Context**: SPEC section 9 fixes the error prefix but only gives one message text.
- **Decision**: Messages are `Invalid character 'X'` (also used for a single `&` or `|`),
  `Malformed number 'N'`, `Number 'N' is glued to letters`, `Unterminated char literal L`,
  `Empty char literal ''`, `Char literal L is too long`, `Bad escape sequence in char literal L`,
  `Unterminated block comment`. Columns count characters (a tab is 1 column); only `\n` ends a line, so `\r\n`
  is one line break. Identifiers and digits are ASCII only: a non-ASCII letter such as `é` is an invalid character.
- **Trade-offs**:
  - (+) Easy to match in `// EXPECT:` lines by substring.
  - (-) Tab-expanding editors may show different columns than the compiler.

## D-015 Phase 1 `main.py` always prints the tokens and an errors section

- **Context**: D-007 grows `main.py` one stage per phase; SPEC section 12 says no flag means `--all`.
- **Decision**: In Phase 1 the only stage is tokens, so any accepted invocation prints `== TOKENS ==` then
  `== ERRORS ==` (so lexical errors are visible next to the table). Unknown flags or a wrong number of paths
  give exit code 2 and a usage line on stderr; unreadable files also give 2. Exit 1 if any lexical error.
  `run(path, flags) -> int` matches interfaces.md. `main.py` inserts the repo root into `sys.path` so
  `python src/main.py` works.
- **Trade-offs**:
  - (+) Runnable end-to-end check now.
  - (-) Other flags are rejected until their phases; Phase 7 will rewrite the flag handling.

## D-016 Valid token samples are full SmartLang programs; EXPECT-file checks live in test_lexer.py

- **Context**: SPEC section 13 says every file in `tests/valid/` is `// EXPECT: OK`, and `test_programs.py` (a later
  phase) will run the whole pipeline on it.
- **Decision**: `tests/valid/tokens_*.sl` are meant to be grammatical and type-correct programs, not loose token
  lists. In Phase 1 `test_lexer.py` itself reads the `// EXPECT:` lines of `tests/invalid/lexical_*.sl` and checks
  kind, line and message substring; it also checks that the valid files lex without errors.
- **Trade-offs**:
  - (+) The same files can keep working in later phases.
  - (-) They have not been run through a parser or semantic analyzer (not built yet), so their validity beyond
    tokens is unverified until Phases 2 and 5.

## D-017 Node labels and child order in the parse tree

- **Context**: interfaces.md requires `label()` and `children()` on every node but does not say what the label text is.
- **Decision**: Label = class name plus the identifying data: `Program`, `FunctionDecl int main`, `Param int x`,
  `VarDecl const int LIMIT`, `Assign total`, `BinaryOp +`, `UnaryOp !`, `Literal 10 (int)`, `Identifier x`, `Call f`;
  other nodes use the class name. Children are in source order and absent optional parts (no `else`, no `for` init or
  update, no initializer) are left out, so the position of a child is not fixed. A `Block` as `else_branch` and an
  `If` as `else_branch` (else-if) both appear directly under the `If`. Node `line`/`col` are those of the first token of
  the construct; for `BinaryOp` and `UnaryOp` they are those of the operator token. Dataclass field order is the
  interfaces.md fields first, then `line`, `col` (always passed by keyword in the parser).
  Semantic annotations (`expr_type`, `tac_name`, `scope_id`) are dataclass fields with `init=False, compare=False`.
- **Trade-offs**:
  - (+) The tree text is short and readable; the semantic analyzer will find error positions at the operator.
  - (-) A reader cannot tell "then" from "else" in the text except by order and depth (a Block after a condition).
  - (-) Equality of nodes ignores annotations, which is what parser tests want but must be remembered later.

## D-018 Phase 2 reports one syntax error and stops (no recovery yet) [SUPERSEDED by D-021 and D-022 in Phase 3]

- **Context**: Phase 2 covers valid programs only; panic-mode recovery belongs to Phase 3 (D-003), but
  interfaces.md says `parse` never raises and the compiler must never crash.
- **Options considered**:
  1. Let `ParseError` escape (crashes the CLI on a bad file).
  2. Catch it once in `parse_program`, report ONE Syntax error, and return the top-level items finished before it.
- **Decision**: Option 2. Message form: `Expected 'X' but found 'Y'` (`end of file` at EOF, `Expected statement/expression/
  type/identifier but found ...`). A `RecursionError` from extremely deep nesting is reported as `Program is nested too deeply`.
  The `ParseError` class and `expect` helper are the ones Phase 3 will extend with synchronization.
- **Trade-offs**:
  - (+) No crash on any input; Phase 3 only has to add recovery points.
  - (-) After the first syntax error nothing else is checked; the partial tree omits the declaration that failed.

## D-019 `--tree`, `--tree-png` and `run()` signature

- **Context**: SPEC section 12 lists `--tree` and `--tree-png PATH`; interfaces.md freezes `run(path, flags) -> int`, but
  `flags: set[str]` has nowhere to hold the PATH value.
- **Options considered**:
  1. Encode the path in the flag string (`--tree-png=out.png`).
  2. Add an optional keyword parameter `png_path: str | None = None` to `run`.
- **Decision**: Option 2. Calls `run(path, flags)` keep working; this is a backward-compatible extension, flagged for
  approval (frozen interface). `parse_args` returns `(path, flags, png_path)`; `--tree-png` consumes the next argument,
  and a missing PATH is a usage error (exit 2). The parser runs only when `--tree` or `--tree-png` is requested, so
  Phase 1 `--tokens` runs behave exactly as before. Output order: tokens, `== PARSE TREE ==` (only with `--tree`),
  `== ERRORS ==`, then `PNG written: PATH`. A missing `dot` binary prints one `error: Graphviz 'dot' program not found...`
  line to stderr and exits 2. The PNG is also written for a partial tree after a syntax error.
- **Trade-offs**:
  - (+) Interface stays source compatible; Phase 7 can fold it into the final CLI.
  - (-) `run` now differs textually from interfaces.md until the interface doc is updated with approval.
  - (-) Syntax errors are only visible when a tree flag is given until Phase 7 makes the full pipeline the default.
- **Status**: Approved by the user (Phase 2 follow-up). `docs/interfaces.md` now shows the new `run()` signature.

## D-020 INVALID tokens are skipped and syntax errors right after them are suppressed

- **Context**: interfaces.md says the parser skips INVALID tokens silently, because the lexer already reported them.
  Skipping alone caused follow-on noise: in `int a = 5 @ 1;` the parser dropped `@` and then reported
  `Expected ';' but found '1'` (observed with `samples/invalid_lexical.sl` before this change). The same happens for
  `int g = 9abc;` (the INVALID run disappears, so the parser sees `= ;`) and for `char h = 'a;` (D-013: the literal
  swallows the `;`).
- **Options considered**:
  1. Keep skipping only; accept the extra Syntax errors.
  2. Skip INVALID tokens, remember which kept tokens directly follow a skipped one, and do not report a syntax
     error whose offending token is one of them.
  3. Make the parser fail at the INVALID token and report nothing else.
- **Decision**: Option 2. `Parser.__init__` builds the filtered token list and the set `after_invalid`; `fail()` sets
  `ParseError.after_invalid`; `parse_program` still stops at that error (no recovery before Phase 3) but does not
  report it. A comment-only note was added to `parser.py` in interfaces.md; no signature changed.
- **Trade-offs**:
  - (+) One mistake gives one error; a lexical error is never followed by a misleading syntax error.
  - (-) The parse still stops there, so later genuine syntax errors in the same file stay hidden until Phase 3 recovery.
  - (-) If the offending token follows an INVALID token but is itself wrong, that error is hidden too. Fixing the lexical
    error exposes it on the next run.
  - (-) Relies on the lexer having reported the INVALID token. Tokens built by hand without a lexical error would
    fail silently (cannot happen via `main.py`).

## D-021 Partial tree keeps everything that parsed (supersedes D-018)

- **Context**: D-018 caught the first `ParseError` in `parse_program` and returned only the items finished before it.
  After one error in `main` the tree showed just `Program`, and nothing after the error was checked.
- **Options considered**:
  1. Keep D-018 (stop at the first error).
  2. Recover but drop every function that contains an error.
  3. Recover at statement and top-level boundaries; keep every top-level item and statement that parsed, plus the
     recovered function.
- **Decision**: Option 3. A failed statement is dropped, the statements around it stay. A function whose header or body
  failed stays as a `FunctionDecl` (params parsed before the error, or none; body = the statements that parsed, or an
  empty `Block` when the `{` is missing). A failed top-level variable declaration is dropped. D-018's message format and
  the `RecursionError` message (`Program is nested too deeply`) are unchanged; the recursion error is now caught per
  top-level item, so later items are still parsed.
- **Trade-offs**:
  - (+) `--tree` shows a useful tree after errors; later errors in the same file are found.
  - (-) The tree can be incomplete or slightly wrong (dropped statement, empty body). It is for display only: the
    pipeline stops after parsing when any Syntax error exists (SPEC section 9), so semantic analysis never sees it.
  - (-) Params parsed before a header error are lost (the list is built inside `parse_params`).

## D-022 Panic-mode recovery design (implements D-003)

- **Context**: SPEC section 9 asks for panic mode: record the error, skip to `;`, `}` or a statement-starting keyword,
  guarantee forward progress.
- **Options considered**:
  1. Pure skip-to-sync with the sync set exactly as in the SPEC.
  2. Same, plus `{` as a sync token and special handling of a stray `else`.
  3. Phrase-level repair (insert the missing `;` or `)`).
- **Decision**: Option 2.
  - Recovery points: `parse_statement_or_recover` (each statement in a block), `parse_program` (each top-level item),
    `parse_func_rest` (function header). `ParseError` stays private and never leaves `parse()`.
  - `synchronize_statement`: consume a `;` and stop after it; stop BEFORE `}`, `{`, `if while for return const` and the
    type keywords; skip anything else. `synchronize_top_level`: consume `;` or `}`, stop before `const` or a type.
  - `{` is in the statement sync set so that after `if (a > 0 {` the body is parsed as a block instead of being eaten
    token by token (which would let its `}` close the enclosing function early). Cost: the `If` node is lost, its body
    stays as a plain nested `Block`.
  - Stray `else`: report `Expected statement but found 'else'`, then parse the following `if`/block and keep it, for the
    same reason (no follow-on errors, no early `}`).
  - Missing function body (`int f();`): one error, empty `Block` at the error token. A header error suppresses the
    second `Expected '{'` message.
  - Forward progress: `ensure_progress` consumes one token if nothing was consumed since the item started; every loop
    ends at EOF or consumes a token. Unclosed blocks all fail at EOF at the same position; `report_error` ignores a
    second error at the same line and column, so EOF gives one message.
  - D-020 stays inside `report_error`, the single place errors are reported, so it holds on every recovery path.
- **Trade-offs**:
  - (+) Small, explainable; each recovery method is under 20 lines; one mistake normally gives one message.
  - (-) A missing `;` also lost the next statement (`x = 1` newline `y = 2;` dropped both): the sync skipped to the `;`.
    **Updated by D-024**: a clearly forgotten `;` is now inserted instead; the skip stays for other cases.
  - (-) Follow-on errors are possible after unusual mistakes. Two genuine errors inside one skipped region are reported
    as one.
  - (-) Phrase-level repair would keep more of the tree but is not what SPEC section 9 specifies.

## D-023 Known limitation: D-020 hides a real syntax error right after an INVALID token

- **Context**: D-020 suppresses a syntax error whose offending token comes right after a skipped INVALID token, because
  the parser cannot tell whether that error was caused by the vanished token or is a genuine mistake.
- **Options considered**: (1) accept and document; (2) suppress only when the expected token could have been the INVALID
  one (needs per-error knowledge); (3) never suppress.
- **Decision**: Option 1. Example: `@ else { a = 2; }` reports only the Lexical error; the stray `else` is not reported
  until the `@` is fixed. Covered by `test_known_limitation_genuine_error_right_after_invalid_is_hidden`.
- **Trade-offs**:
  - (+) No misleading syntax error after a lexical error, which is by far the common case.
  - (-) One genuine error can stay hidden for one run. Recovery itself still runs, so later errors are found.

## D-024 Insert a clearly forgotten `;` instead of skipping (refines D-022)

- **Context**: Observed with `int x = 1` newline `x = x + 2;` newline `return x;`: panic mode reported the error at `x`, then
  skipped to the next `;`, so the tree lost BOTH `int x = 1` and `x = x + 2`, and a real error inside the second
  statement would have gone unreported.
- **Options considered**:
  1. Keep pure panic mode (D-022 as first written).
  2. Insert the `;` (report, consume nothing) when the offending token clearly starts something new: it is on a later
     line than the previous token, or is `}`, EOF, or a statement-start keyword (`if while for return const` or a type).
     Otherwise skip as before.
  3. Always insert.
- **Decision**: Option 2, in one helper `expect_semicolon` (used by declarations, assignments, call statements and
  `return`; the two `;` inside a `for (...)` header still use `expect`). The error text is unchanged
  (`Expected ';' but found X`); the statement stays in the tree; the next statement is parsed normally.
  Forward progress holds: the statement consumed at least one token before the check.
- **Trade-offs**:
  - (+) One missing `;` gives one error and loses nothing; errors in the next statement are still found.
  - (-) A heuristic, not a proof. `int a = 1` newline `)` gives two errors (`;` and the stray `)`); both are genuine.
  - (-) Same-line junk (`int a = 1 2;`) still takes the skip path and drops the statement.
  - (-) A phrase-level repair on top of panic mode (D-003 option 3, used in one place only).
- **Side change (same session)**: `synchronize_top_level` now consumes a whole run of stray `}` as one mistake. Found with
  5000 nested `{`: after the recursion error the leftover `}` produced thousands of `Expected type but found '}'` lines.

## D-025 Known limitations of the tree after a syntax error

- **Context**: After an error the parser returns a partial tree for display (D-021). It is not complete.
- **Decision**: Accepted and documented. The tree DROPS or CHANGES the following after an error:
  1. A failed `if`/`while`/`for` header (e.g. `if (a > 0 {`) loses the `If`/`While`/`For` node; its body block stays as a
     plain nested `Block`, and an `else` branch of that `if` is reported as a stray `else` (kept as a block, D-022).
  2. A statement that raised a `ParseError` is dropped (including the part of it that parsed), except for the missing-`;`
     case (D-024).
  3. A broken function header loses its parameters (`params` is empty); a missing body gives an empty `Block`.
  4. A failed top-level variable declaration is dropped.
  5. A stray `else` and its block are kept as a nested block although they are not valid code.
  6. A run of tokens skipped by panic mode can hide a second genuine error inside it; follow-on errors are possible.
  7. Nesting deeper than about 330 levels hits Python's recursion limit: one `Program is nested too deeply` error,
     the whole top-level item is dropped, and a follow-on error can appear after it (observed with 400 nested `{`).
  8. A genuine error right after an INVALID token is hidden (D-023).
- **Trade-offs**: (+) simple parser, explainable in a viva. (-) the tree after an error is for display only; the pipeline
  never runs semantic analysis on it (SPEC section 9).

## D-026 Root `conftest.py` with a 10-second `SIGALRM` timeout per test

- **Context**: A broken synchronization loop during panic-mode recovery can hang on a test that has no explicit
  `time_limit`, freezing the entire `pytest` run. Rule 9 forbids adding third-party packages like `pytest-timeout`.
- **Options considered**:
  1. Put `with time_limit(...)` manually inside every test across every test file.
  2. Add a root `conftest.py` with an `autouse=True` fixture that sets `signal.alarm(10)` around each test and raises
     `TimeoutExceeded`, falling back to a no-op when `signal.SIGALRM` is unavailable (Windows).
- **Decision**: Option 2 (approved by the user as a one-time scope exception).
- **Trade-offs**:
  - (+) Every test automatically fails after 10 seconds instead of hanging `pytest`; uses standard library `signal` only.
  - (+) Safe on Windows (`if not hasattr(signal, "SIGALRM"): yield; return`).
  - (-) Adds `conftest.py` at the repository root.
  - (-) Any test that calls `signal.alarm(...)` itself (such as `time_limit(60)` in the fuzz tests) overrides the
    10-second alarm for the duration of its `with` block, then restores the handler on exit.

## D-027 `SymbolTable` scope history, `current_level` convention, `scope_level` assignment, and `dump()` table format

- **Context**: `interfaces.md` freezes `Symbol` and `SymbolTable` (`enter_scope(label) -> int`, `exit_scope()`,
  `declare(symbol) -> bool`, `lookup(name)`, `lookup_current(name)`, `current_level() -> int`, `dump() -> str`), and
  SPEC section 10 requires `dump()` to print every scope that existed (including exited ones), labelled e.g.
  `Scope 0 (global)`, `Scope 1 (function sumSquares)`, `Scope 2 (block)`, with each symbol's name, type, kind, scope
  level, line, and function return type plus parameter list.
- **Options considered**:
  1. Parent-pointer tree of scopes vs. two lists of shared `_Scope` records (`_active` stack + `_all_scopes` history).
  2. Auto-create `Scope 0 (global)` in `SymbolTable.__init__()` vs. require an explicit `enter_scope("global")` call.
  3. Overwrite vs. keep the original `Symbol` when `declare()` sees a redeclaration in the same scope.
  4. Trust the `scope_level` passed into `Symbol(...)` vs. have `declare()` set `symbol.scope_level` to the current scope's level.
- **Decision**:
  - Two lists of shared `_Scope` records: `_active` holds the currently open scopes from outermost to innermost (used by
    `declare`, `lookup`, `lookup_current`, `current_level`), and `_all_scopes` holds every scope ever created in creation
    order `0, 1, 2, ...` (used by `dump`). `exit_scope()` pops from `_active` only.
  - `SymbolTable()` starts with no active scopes (`current_level() == -1`); `enter_scope("global")` opens `Scope 0 (global)`
    at nesting level `0` and returns `0`, so every scope uses `enter_scope(label) -> int` uniformly. Calling `declare()`
    or `exit_scope()` when `_active` is empty raises `RuntimeError`.
  - On same-scope redeclaration, `declare()` returns `False` and leaves the first `Symbol` untouched so subsequent
    lookups in semantic analysis resolve to the original declaration.
  - On a valid declaration, `declare()` sets `symbol.scope_level = self._active[-1].level` before storing `symbol`, so a
    stored symbol's `scope_level` can never disagree with the scope it was declared in.
  - `dump()` formats each scope in `_all_scopes` (separated by a blank line) with header `Scope <id> (<label>)` followed
    by a two-space-indented aligned table (`NAME`, `TYPE`, `KIND`, `LEVEL`, `LINE`, `PARAMS`, where `PARAMS` is
    `(type name, ...)` or `()` when `params is not None` and `-` otherwise), or `  (empty)` when a scope has no symbols.
- **Trade-offs**:
  - (+) `lookup()` walks `reversed(self._active)` and can never accidentally match an exited sibling scope, while `dump()`
    prints every scope ever entered in creation order.
  - (+) Uniform `enter_scope(label) -> int` contract for `global`, `function <name>`, `for`, and `block` scopes.
  - (+) Setting `symbol.scope_level` inside `declare()` eliminates any mismatch between a symbol's stored level and its scope.
  - (-) The caller (Phase 5 `semantic.py` or tests) must call `enter_scope("global")` before declaring top-level symbols.
  - (-) `declare()` mutates `symbol.scope_level` in place (`Symbol` is a non-frozen dataclass in `interfaces.md`).

## D-028 Phase 5a scope visibility, declaration order and silent non-function calls

- **Context**: SPEC section 8 fixes the scope kinds but not when a name becomes visible, nor what a call of a non-function does before Phase 5b.
- **Options considered**: (1) declare a name before or after typing its initializer; (2) make all globals visible everywhere vs. only after their declaration; (3) report `x(1)` where `x` is a variable now or leave it to 5b.
- **Decision** (approved): functions are visible everywhere (pass 1 collects every signature, so forward calls and recursion work); a global variable is visible only after its declaration, so a function placed before it cannot use it; the initializer is typed BEFORE the name is declared, so `int x = x;` reports `Undeclared identifier 'x'`; a call whose name resolves to a non-function is **silent in 5a** and gets type `error` (Phase 5b adds the message). A global variable whose name equals an earlier-collected function is a redeclaration error. The `for` statement has its own scope (label `for`) and its body is a block scope inside it; the function body Block shares the function's scope id.
- **Trade-offs**: (+) simple, matches C-like intuition. (-) Calling a variable is accepted silently until 5b (pinned by `test_5b_not_checked_yet`). (-) Order of global declarations matters for variables but not for functions.

## D-029 Unique `tac_name`, never colliding with TAC temporaries or labels

- **Context**: SPEC section 11 numbers temporaries `t1..` and labels `L1..`; a user variable named `t1` would clash in the flat TAC namespace. Shadowed variables also need distinct names.
- **Decision**: one program-wide `used_names` set. A declaration takes its own name if unused, else `name_1`, `name_2`, ... (skipping names already taken, so a user variable `x_1` is never reused). Any name matching `^[tL][0-9]+$` counts as already taken, so a user `t1` becomes `t1_1` and `L2` becomes `L2_1`. Parameters, variables, constants and globals all get a `tac_name`; `Identifier` and `Assign` copy the tac_name of the symbol they resolve to. Functions keep their own name.
- **Trade-offs**: (+) TAC generation can use `tac_name` directly. (-) Function names are not renamed, so a function called `L1` or `t1` could still look like a label or temporary in TAC; to be decided in Phase 6 (labels end in `:` and calls use `call f`, so no real clash is expected). Test: `test_tac_name_never_collides_with_temporaries_and_labels`.

## D-030 Error positions in Phase 5a (and a limitation for declarations)

- **Context**: the plan asked for assignment and initializer mismatches to be reported at the target name. `VarDecl` and `Param` only store the position of the declaration's FIRST token (the type, or `const`), and the parser is out of scope for Phase 5a.
- **Decision**: `Assign` errors use the target name (the parser stores the name token). Declaration errors (initializer mismatch, const without initializer, redeclaration) use the declaration's first token, so `    int x = 2.5;` reports Col 5, as in the SPEC example, but `const int C = 1.5;` reports Col 1 (the `const` keyword) and not the name. Binary and unary operators use the operator token; conditions use the condition expression node (for `x + 1` that is the `+`, for an identifier the identifier); identifiers and calls use their own token; a duplicate function uses the function's first token.
- **Trade-offs**: (-) A declaration error points at the type keyword, not the name; fixing it needs `name_line`/`name_col` on `VarDecl`/`Param` in the parser (a later, approved change). Listed in PROGRESS.md under Later.

## D-031 Internal `error` type and the CLI semantic-stage policy

- **Decision**: any operand of type `error` gives a result of type `error` and no message; a failed declaration still declares the name with its DECLARED type, so later uses are not errors; a failed const assignment or function assignment reports once. The semantic stage runs in `main.py` whenever the parser ran (`--tree`, `--tree-png`, `--symbols`) and there are no Lexical or Syntax errors; semantic errors then appear under `== ERRORS ==` and the exit code is 1. `--symbols` prints the tables even with semantic errors; with lexical or syntax errors it prints `== SYMBOL TABLES ==` and `(skipped: lexical or syntax errors)`. With only `--tokens` the parser does not run, so no semantic check happens (Phase 7 changes this, D-019).
- **Trade-offs**: (+) one mistake gives one message. (-) after a rejected operator the expression is `error`, so a second real mistake in the same expression is not reported.

## D-032 Left-spine loop and recursion safety net in the analyzer

- **Context**: the parser nests `a + b + c + ...` to the left. A recursive `type_binary` crashed with `RecursionError` on an 800-term sum (found while testing; it was my own new code, not an earlier-phase bug). 
- **Decision**: `type_binary` walks the left spine with a loop (2000-term chains work). Right-nested depth (900 unary minus signs, accepted by the parser) still recurses, so `analyze` catches `RecursionError` and reports one `Program is nested too deeply to analyze` Semantic error instead of crashing (SPEC section 9).
- **Trade-offs**: (-) after that error the symbol table can be incomplete. Tests: `test_long_operator_chain_does_not_crash`, `test_extreme_nesting_is_an_error_not_a_crash`.

## D-033 Convention: "start of declaration" for declaration errors

- **Context**: D-030 explained why Phase 5a reports declaration errors at the declaration's first token. It is now the general rule.
- **Decision**: errors about a declaration (initializer mismatch, const without initializer, redeclaration, duplicate function) are reported at the START of the declaration (`int`, `const`, or the function's return type), not at the name. Errors about an expression are reported at the expression node (operator token for `a + b`, own token for identifiers, literals and calls); assignment statements at the target name; `return` errors at the `return` keyword; call errors on the callee at the call name; argument errors at the argument expression; missing return at the closing `}`.
- **Trade-offs**: (-) declaration errors do not point at the name; the later parser change (name position on `VarDecl`/`Param`) would improve it.

## D-034 `Block.end_line` / `Block.end_col` (approved parser change)

- **Context**: SPEC section 8 wants "missing return" at the function's closing brace line, and `Block` stored only the `{` position.
- **Options considered**: (1) report at the function header and log a deviation; (2) store the `}` position in `Block`.
- **Decision** (approved): `Block` gets `end_line: int = 0` and `end_col: int = 0` with `compare=False`; `parse_block` fills them from the `}` token (the EOF token for an unclosed block). A Block built elsewhere keeps 0, and the analyzer then falls back to the function header. `docs/interfaces.md` lists the fields. `parse_function_body`'s empty Block (header error) keeps 0; syntax errors skip semantic analysis anyway.
- **Trade-offs**: (+) 3 added lines in `ast_nodes.py`, a few in `parser.py`; the full suite stayed at 479 passed right after the change, so `test_parser.py` and `test_syntax_errors.py` needed no edits. (-) `tree_export` does not show the fields (not needed).

## D-035 Missing return is strict

- **Context**: SPEC section 8: "the last statement of a function body (top level of the body) must be a `return`".
- **Decision**: only a final top-level `Return` satisfies it. Pinned (tests and `semantic_missing_return_*.sl`): an if/else where both branches return, a trailing bare block `{ return 1; }`, a trailing `while`/`for` containing `return`, and a trailing call all report `Missing return at end of function 'f'`. A `return` in the middle of the body does not count. An empty body reports it too.
- **Trade-offs**: (-) rejects some programs that are fine in C-like languages (if/else with returns in both branches); users add a final `return`. (+) simple and exactly the SPEC wording. Flow analysis is out of scope (SPEC section 15).

## D-036 Function rule messages and positions (Phase 5b)

- **Decision**: `Call to undeclared function 'f'` (5a), `Cannot call 'x': it is a variable, not a function` (call name; type `error`), `Function 'f' expects N argument(s), found M` (call name), `Argument K of 'f': cannot pass V to T parameter 'p'` (the argument expression), `Cannot return V from function 'f' returning T` (the `return` keyword), `Missing return at end of function 'f'` (closing brace). Arguments are always typed first. After an arity error the per-argument type check is skipped (pairing is meaningless). A call with bad arguments keeps the function's return type (no cascade); an `error`-typed argument or return value is silent. A local that shadows a function name makes `f(...)` a call of a variable.
- **Trade-offs**: (-) after an arity error, a wrong argument type is not reported until the arity is fixed. Tests: `tests/test_semantic_functions.py` and `tests/invalid/semantic_call_*.sl`, `semantic_return_*.sl`, `semantic_missing_return_*.sl`, `semantic_function_errors.sl`.

## D-037 RecursionError handler in `main.py` and the 3000-term PNG exit 2

- **Context**: with a 3000-term `1+1+...` chain, `--tree` crashed with a traceback (recursive `tree_to_text`). `--tree-png` exited 2: `RecursionError` is a subclass of `RuntimeError`, so `write_png` caught it as a Graphviz failure, printed the terse `error: maximum recursion depth exceeded` and returned the usage exit code 2 (the message was on stderr, so not silent, but unclear and with the wrong code). 800 terms work for both.
- **Decision** (approved: `main.py` only, `tree_export.py` untouched): `run` wraps `run_stages` in `try/except RecursionError`: one stderr line `error: program is nested too deeply to process (recursion limit exceeded)` and exit 1. `write_png` re-raises `RecursionError` before its `RuntimeError` branch. Exit 2 stays for usage and file errors.
- **Trade-offs**: (-) output already printed (tokens, errors section) stays; with `--tree-png` the `== ERRORS == (none)` section appears before the failure. A real fix would make `tree_export` iterative (needs approval). Tests: `test_cli_deep_chain_tree_gives_one_line_error`, `test_cli_deep_chain_tree_png_gives_one_line_error`, `test_cli_missing_file_is_still_exit_2`, plus 5a carry-forward tests `test_cli_lexical_errors_only_skip_semantic_stage` and `test_cli_symbols_after_nested_too_deeply`.

## D-038 TAC instruction format, literal rendering, assignment copy, and adjacent labels

- **Context**: SPEC section 11 defines the TAC instruction shapes (`x = y`, `x = y op z`, `x = op y`, `goto L`, `ifFalse x goto L`, `L:`, `param x`, `x = call f, n`, `call f, n`, `return x`, `func name: ... endfunc`, `globals:`), and `interfaces.md` freezes `generate(tree: Program) -> list[str]`. Several formatting details needed pinning before golden tests were written.
- **Options considered**:
  1. Write the result of a compound RHS directly into the target variable (`x = a + t1`) vs. always allocate a temporary for every `BinaryOp`/`UnaryOp`/`Call` and emit a separate copy (`t2 = a + t1` then `x = t2`).
  2. Emit a dummy instruction for uninitialized declarations (`int x;`) vs. emit nothing.
  3. Collapse adjacent labels at the end of an `else-if` chain (`L6:` followed by `L4:` and `L2:`) vs. preserve the exact nested `if/else` SPEC shape.
- **Decision** (approved):
  - Every `generate(tree)` element is a single line with no trailing newline and no blank lines between sections. `globals:`, `func <name>:`, `endfunc`, and `<L>:` sit at column 0; all instructions are indented two spaces.
  - Unary instructions keep the space shown in SPEC section 11 (`x = op y`, e.g. `  t1 = - a`, `  t2 = ! flag`).
  - Leaves (`Literal`, `Identifier`) return their operand string directly without allocating a temporary (`Literal.value` is emitted verbatim for `int`, `float`, single-quoted `char` with escapes, and `true`/`false`). Every `BinaryOp`, `UnaryOp`, and expression `Call` allocates a fresh temporary `tK`, and `Assign` / initialized `VarDecl` emits a copy `  <target> = <rhs>`.
  - Uninitialized variable declarations (local or global) emit nothing. The `globals:` header is emitted at the start of the output only when at least one top-level `VarDecl` has an initializer, and all initialized globals are emitted there in source order before the first function.
  - `else if` chains nest the standard `if/else` shape without peephole label merging, so adjacent closing labels (`L6:`, `L4:`, `L2:`) are preserved as-is.
- **Trade-offs**:
  - (+) Completely uniform generator: every expression node returns an operand string, every statement emits its SPEC template directly, and no peephole pass has to be explained in the viva.
  - (-) An assignment of a compound expression uses one extra copy instruction (`t2 = a + t1`, `x = t2`), and `else-if` chains end with stacked labels. Optimization is explicitly out of scope (SPEC section 15).

## D-039 Pre-body label allocation, pre-param argument evaluation, and strict `tac_name` enforcement

- **Context**: Nested loops/branches and nested function calls (`f(a, g(b))`) need deterministic label numbering and non-interleaved `param` emission. Also, D-029 left open whether function names like `t1`/`L1` need renaming in TAC and what `tacgen` should do if `tac_name` is missing.
- **Options considered**:
  1. Allocate labels lazily as they are emitted vs. allocate a control-flow statement's labels (`L_else, L_end` or `L_start, L_end`) in SPEC-shape order BEFORE generating its nested blocks/branches.
  2. Emit `param` immediately after each argument vs. evaluate all argument expressions left-to-right first and then emit all `param` lines right before `call f, n`.
  3. Fall back to `node.name` when `node.tac_name is None` vs. raise `ValueError`.
- **Decision** (approved):
  - `gen_if`, `gen_while`, and `gen_for` allocate their own labels in SPEC-shape order before generating their nested body/branch statements, so outer constructs always receive lower label numbers than inner constructs.
  - `gen_call_expr` and `gen_call_stmt` evaluate `[self.gen_expr(arg) for arg in args]` first, then emit `  param <arg>` for each evaluated operand immediately before `call <name>, <n>`.
  - `require_tac_name` raises `ValueError` whenever `tac_name` is `None` or empty on a `VarDecl` (including uninitialized globals), `Assign`, or `Identifier` — no silent fallback to `node.name`.
  - Function names keep their source name in TAC: because labels end with `:`, function headers start with `func `, and calls use `call <name>, <n>`, a function named `t1` or `L1` cannot collide syntactically with temporaries or labels.
- **Trade-offs**:
  - (+) Outer-before-inner label numbering makes nested control flow easy to trace by hand; evaluating call arguments before `param` prevents `param` interleaving on `f(a, g(b))`; strict `tac_name` checking catches any unanalyzed AST immediately.
  - (-) Callers of `generate(tree)` in tests must run `analyze(tree, errors)` first (which is already the documented precondition in `interfaces.md`).

## D-040 Iterative left-spine loop in `gen_binary` and `--tac` CLI behavior

- **Context**: Requirement 4 requires an 800-term `1 + 1 + ...` chain to produce correct TAC without deep recursion, and a 3000-term chain through the CLI to never crash with a traceback.
- **Decision** (approved):
  - `gen_binary` collects the left spine of consecutive `BinaryOp` nodes in a `while isinstance(current, BinaryOp)` loop and emits instructions in `reversed(spine)` order, matching `type_binary` in `semantic.py` (D-032).
  - Because `tokenize`, `parse_binary_level`, `type_binary`, and `gen_binary` all use iterative loops down the left spine, a 3000-term `1 + 1 + ... + 1` chain run with `--tac` alone succeeds cleanly (3000 TAC addition lines, exit 0). Running the same 3000-term chain with `--tree --tac` hits the recursion limit inside `tree_to_text` (`tree_export.py`, out of scope) and is caught by `main.py`'s existing `RecursionError` handler (D-037), printing the single line `error: program is nested too deeply to process (recursion limit exceeded)` to stderr and exiting 1.
  - In `main.py`, `--tac` is added to `KNOWN_FLAGS`, `USAGE`, and `wants_tree`. After `== ERRORS ==`, `run_tac_stage` prints `== THREE-ADDRESS CODE ==` followed by `(skipped: compilation errors)` when `errors.has_errors()` is true, `(none)` when `generate(tree)` returns an empty list, or the joined TAC lines otherwise.
- **Trade-offs**:
  - (+) Left-associative expression chains of thousands of terms use `O(1)` Python call-stack depth in `tacgen.py`.
  - (-) Deeply right-nested expressions (e.g. 900 stacked unary `-` operators) remain recursive; `semantic.py` catches `RecursionError` and reports `Program is nested too deeply to analyze`, causing `--tac` to print `(skipped: compilation errors)` and exit 1.
