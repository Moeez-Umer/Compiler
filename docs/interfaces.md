# INTERFACES: module contracts (written before the code)

Frozen. Change only with the user's approval and a Decisions.md entry.
All modules live in `src/` and are imported as `from src.lexer import tokenize`.

## tokens.py

```python
class TokenType(Enum):
    KEYWORD; IDENTIFIER; INT_LIT; FLOAT_LIT; CHAR_LIT
    OPERATOR; DELIMITER; EOF; INVALID

@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    line: int
    col: int
```

## errors.py

```python
@dataclass(frozen=True)
class CompilerError:
    kind: str        # "Lexical" | "Syntax" | "Semantic"
    line: int
    col: int
    message: str
    def format(self) -> str   # "[Lexical Error] Line 5, Col 12: message"

class ErrorCollector:
    def report(self, kind: str, line: int, col: int, message: str) -> None
    def has_errors(self) -> bool
    def has_kind(self, kind: str) -> bool
    def all(self) -> list[CompilerError]        # grouped Lexical, Syntax, Semantic; sorted by line, col
```

## lexer.py

```python
def tokenize(source: str, errors: ErrorCollector) -> list[Token]
# Always ends with an EOF token. Invalid input yields INVALID tokens and a reported Lexical error.
```

## ast_nodes.py

Every node is a dataclass with `line: int` and `col: int`, plus two methods used by tree export:
`label() -> str` (text shown in the tree) and `children() -> list[Node]`.

```python
Program(items: list[FunctionDecl | VarDecl])
FunctionDecl(return_type: str, name: str, params: list[Param], body: Block)
Param(type_name: str, name: str)
VarDecl(type_name: str, name: str, init: Expr | None, is_const: bool)
Block(statements: list[Stmt])
Assign(name: str, value: Expr)
If(condition: Expr, then_block: Block, else_branch: Block | If | None)
While(condition: Expr, body: Block)
For(init: VarDecl | Assign | None, condition: Expr, update: Assign | None, body: Block)
Return(value: Expr)
CallStmt(call: Call)
BinaryOp(op: str, left: Expr, right: Expr)
UnaryOp(op: str, operand: Expr)
Literal(value: str, type_name: str)       # type_name in int, float, char, bool
Identifier(name: str)
Call(name: str, args: list[Expr])
```

Annotations added by the semantic analyzer (default `None` until analysis runs):
- every expression node: `expr_type: str`
- `VarDecl`, `Param`, `Identifier`, `Assign`: `tac_name: str`
- `Block`, `FunctionDecl`, `For`: `scope_id: int`

## parser.py

```python
def parse(tokens: list[Token], errors: ErrorCollector) -> Program
# Never raises, never loops forever. INVALID tokens are skipped silently (already reported).
# A syntax error whose offending token comes right after a skipped INVALID token is also not
# reported (the lexer error already covers it; D-020).
# On syntax errors reports Syntax errors and returns the best partial tree.
```

## tree_export.py

```python
def tree_to_text(root: Node) -> str
def tree_to_dot(root: Node) -> str
def export_png(root: Node, path: str) -> None     # uses graphviz; fails gracefully if `dot` is missing
```

## symbol_table.py

```python
@dataclass
class Symbol:
    name: str
    type_name: str                    # int | float | char | bool (return type for functions)
    kind: str                         # "var" | "const" | "param" | "func"
    scope_level: int
    line: int
    params: list[tuple[str, str]] | None = None    # (type, name) for functions
    tac_name: str = ""

class SymbolTable:
    def enter_scope(self, label: str) -> int          # returns scope id
    def exit_scope(self) -> None
    def declare(self, symbol: Symbol) -> bool          # False if name exists in CURRENT scope
    def lookup(self, name: str) -> Symbol | None       # walks outward
    def lookup_current(self, name: str) -> Symbol | None
    def current_level(self) -> int
    def dump(self) -> str                              # every scope ever created, exited or not
```

## semantic.py

```python
def analyze(tree: Program, errors: ErrorCollector) -> SymbolTable
# Pass 1 collects function signatures. Pass 2 checks bodies. Annotates the tree.
# Reports all semantic errors, never stops at the first.
```

## tacgen.py

```python
def generate(tree: Program) -> list[str]
# Precondition: tree has no errors and has been analyzed (annotations present).
```

## main.py

```python
def run(path: str, flags: set[str], png_path: str | None = None) -> int
# returns exit code; prints sections per SPEC section 12.
# png_path is the PATH of --tree-png (D-019, approved by the user); callers may omit it.
```

## Dependency direction (no cycles)

`tokens, errors` ← `lexer` ← `parser` (also uses `ast_nodes`) ← `semantic` (uses `symbol_table`) ← `tacgen` ← `main`.
`tree_export` depends only on `ast_nodes`.