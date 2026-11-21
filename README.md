# SmartLang Compiler Front-End

Term project for CS426 Compiler Construction (Information Technology University).
It is the front-end of a compiler for **SmartLang**, a simplified imperative language: a lexical analyzer,
a recursive descent parser, a semantic analyzer and a three-address-code (TAC) generator.
Everything is hand-written Python 3.12. Only the standard library, `graphviz` and `pytest` are used.

Design documents live in `docs/`: `SPEC.md` (language and compiler rules), `interfaces.md` (module contracts),
`Decisions.md` (design choices), `Flow.md` (pipeline), `PROGRESS.md` (phase checklist).

## Setup (macOS)

```bash
brew install graphviz            # provides the `dot` binary (needed for --tree-png)
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python --version                 # should print Python 3.12.x
```

## Run the tests

From the repo root, with the virtual environment active:

```bash
pytest -q -rs
```

(`python -m pytest` also works; `pytest.ini` sets `pythonpath = .` and `testpaths = tests`.)

## Usage

```bash
python src/main.py prog.sl [--tokens] [--tree] [--tree-png PATH] [--symbols] [--tac] [--all]
```

Flags can be given in any order. Sections are always printed in this order, one blank line apart:
`== TOKENS ==`, `== PARSE TREE ==`, `== SYMBOL TABLES ==`, `== ERRORS ==`, `== THREE-ADDRESS CODE ==`.

| Flag | Prints |
|---|---|
| *(none)* or `--all` | all five sections (everything except the PNG) |
| `--tokens` / `--tree` / `--symbols` / `--tac` | only that section (plus `== ERRORS ==`, which is always printed; `(none)` when empty) |
| `--tree-png PATH` | also writes the parse tree as a PNG (needs Graphviz `dot`); prints `wrote PATH` on stderr, stdout does not change |

Pipeline policy: the lexer and the parser always run; the tree is printed even after syntax errors (a partial tree);
semantic analysis runs only without lexical or syntax errors; TAC only without any error. A section whose stage
was skipped prints one line, for example `(skipped: lexical or syntax errors)`. A tree too deep to print shows
`(skipped: nested too deeply to print)` and the other sections still print.

| Exit code | Meaning |
|---|---|
| 0 | no errors |
| 1 | any lexical, syntax or semantic error (also a tree too deep to print or draw) |
| 2 | usage or file error (no file, unreadable or non-UTF-8 file, directory, unknown flag, `--tree-png` without a PATH, Graphviz problem); one line on stderr |

## Samples

| File | What it shows |
|---|---|
| `samples/valid_program.sl` | end-to-end demo: a clean program (exit 0) |
| `samples/errors_lexical_syntax.sl` | end-to-end demo: lexical and syntax errors, partial tree, later stages skipped (exit 1) |
| `samples/errors_semantic.sl` | end-to-end demo: six semantic errors, tables printed, TAC skipped (exit 1) |
| `samples/valid_all_tokens.sl` | lexer demo: every token class in a valid program |
| `samples/invalid_lexical.sl` | lexer demo: every kind of lexical error |

(`samples/valid_program_tree.png` is a parse-tree image of `valid_program.sl` made in Phase 2.)

### Example: `valid_program.sl` (clean, exit 0)

`python src/main.py samples/valid_program.sl --tac` prints `== ERRORS ==` and the TAC (the full no-flag output also has the token table, tree and symbol tables):

```text
== ERRORS ==
(none)

== THREE-ADDRESS CODE ==
globals:
  LIMIT = 10
func square:
  t1 = x * x
  return t1
endfunc
func sumSquares:
  total = 0
  i = 1
L1:
  t2 = i <= n
  ifFalse t2 goto L2
  param i
  t3 = call square, 1
  t4 = total + t3
  total = t4
  t5 = i + 1
  i = t5
  goto L1
L2:
  return total
endfunc
func average:
  t6 = a + b
  s = t6
  t7 = s / 2
  return t7
endfunc
func main:
  param LIMIT
  t8 = call sumSquares, 1
  r = t8
  t9 = r > 100
  t10 = LIMIT != 0
  t11 = t9 && t10
  big = t11
  ifFalse big goto L3
  t12 = r - 1
  r = t12
  goto L4
L3:
  t13 = r == 0
  ifFalse t13 goto L5
  r = 1
  goto L6
L5:
  r = 0
L6:
L4:
  k = 0
L7:
  t14 = k < 3
  ifFalse t14 goto L8
  t15 = r + k
  r = t15
  t16 = k + 1
  k = t16
  goto L7
L8:
  return r
endfunc
```

### Example: `errors_lexical_syntax.sl` (exit 1)

`python src/main.py samples/errors_lexical_syntax.sl --tree --symbols`:

```text
== PARSE TREE ==
Program
  FunctionDecl int main
    Block
      VarDecl int c
        Literal 1 (int)
      Block
        Assign a
          Literal 2 (int)
      Return
        Identifier a

== SYMBOL TABLES ==
(skipped: lexical or syntax errors)

== ERRORS ==
[Lexical Error] Line 3, Col 15: Invalid character '@'
[Syntax Error] Line 4, Col 13: Expected expression but found ';'
[Syntax Error] Line 6, Col 5: Expected ';' but found 'if'
[Syntax Error] Line 6, Col 15: Expected ')' but found '{'
```

The tree is partial: failed statements are dropped (D-021, D-025).

### Example: `errors_semantic.sl` (exit 1)

`python src/main.py samples/errors_semantic.sl --symbols --tac`:

```text
== SYMBOL TABLES ==
Scope 0 (global)
  NAME    TYPE  KIND   LEVEL  LINE  PARAMS
  square  int   func       0     4  (int x)
  main    int   func       0     8  ()
  LIMIT   int   const      0     2  -

Scope 1 (function square)
  NAME  TYPE  KIND   LEVEL  LINE  PARAMS
  x     int   param      1     4  -

Scope 2 (function main)
  NAME  TYPE  KIND  LEVEL  LINE  PARAMS
  a     int   var       1     9  -
  b     int   var       1    10  -
  flag  bool  var       1    11  -
  c     int   var       1    15  -

Scope 3 (block)
  (empty)

== ERRORS ==
[Semantic Error] Line 9, Col 5: Cannot assign float to int variable 'a'
[Semantic Error] Line 10, Col 13: Undeclared identifier 'ghost'
[Semantic Error] Line 11, Col 5: Cannot assign int to bool variable 'flag'
[Semantic Error] Line 12, Col 11: Condition of 'if' must be bool, found int
[Semantic Error] Line 14, Col 5: Cannot assign to constant 'LIMIT'
[Semantic Error] Line 15, Col 13: Function 'square' expects 1 argument, found 2

== THREE-ADDRESS CODE ==
(skipped: compilation errors)
```

### Example: `invalid_lexical.sl` (lexer demo, exit 1)

`python src/main.py samples/invalid_lexical.sl --symbols`:

```text
== SYMBOL TABLES ==
(skipped: lexical or syntax errors)

== ERRORS ==
[Lexical Error] Line 3, Col 15: Invalid character '@'
[Lexical Error] Line 4, Col 19: Invalid character '&'
[Lexical Error] Line 5, Col 19: Invalid character '|'
[Lexical Error] Line 6, Col 15: Malformed number '3.4.5'
[Lexical Error] Line 7, Col 15: Malformed number '3.'
[Lexical Error] Line 8, Col 15: Malformed number '.5'
[Lexical Error] Line 9, Col 13: Number '9abc' is glued to letters
[Lexical Error] Line 10, Col 14: Unterminated char literal 'a;
[Lexical Error] Line 11, Col 14: Empty char literal ''
[Lexical Error] Line 12, Col 14: Char literal 'ab' is too long
[Lexical Error] Line 13, Col 14: Bad escape sequence in char literal '\q'
[Lexical Error] Line 15, Col 5: Unterminated block comment
```

### Example: `valid_all_tokens.sl` (lexer demo, exit 0)

`python src/main.py samples/valid_all_tokens.sl --symbols`:

```text
== SYMBOL TABLES ==
Scope 0 (global)
  NAME    TYPE   KIND   LEVEL  LINE  PARAMS
  square  int    func       0     7  (int x)
  check   bool   func       0    11  (char c, int n)
  main    int    func       0    15  ()
  LIMIT   int    const      0     4  -
  RATE    float  const      0     5  -

Scope 1 (function square)
  NAME  TYPE  KIND   LEVEL  LINE  PARAMS
  x     int   param      1     7  -

Scope 2 (function check)
  NAME  TYPE  KIND   LEVEL  LINE  PARAMS
  c     char  param      1    11  -
  n     int   param      1    11  -

Scope 3 (function main)
  NAME   TYPE  KIND  LEVEL  LINE  PARAMS
  total  int   var       1    16  -
  c      char  var       1    17  -
  q      char  var       1    18  -
  flag   bool  var       1    19  -

Scope 4 (for)
  NAME  TYPE  KIND  LEVEL  LINE  PARAMS
  i     int   var       2    20  -

Scope 5 (block)
  (empty)

Scope 6 (block)
  (empty)

Scope 7 (block)
  (empty)

Scope 8 (block)
  (empty)

== ERRORS ==
(none)
```
