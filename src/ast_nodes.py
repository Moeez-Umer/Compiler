"""Parse tree node classes (interfaces.md: ast_nodes.py, SPEC section 7).

Every node is a dataclass with `line` and `col` (position of its first or
defining token) plus `label()` (text shown in the tree) and `children()`.
Single-child expression chains never become nodes (D-004): a node exists only
when an operator or construct is actually applied.
"""
from dataclasses import dataclass, field


def annotation():
    """A field filled in later by the semantic analyzer; None until analysis runs.

    Kept out of __init__, repr and equality so parser tests compare structure only.
    """
    return field(default=None, init=False, repr=False, compare=False)


@dataclass
class Node:
    """Base class: every node knows its source position and how to show itself."""

    line: int
    col: int

    def label(self) -> str:
        """Text shown for this node in the tree; defaults to the class name."""
        return type(self).__name__

    def children(self) -> list["Node"]:
        """Child nodes in source order; leaves return an empty list."""
        return []


# ---------------------------------------------------------------- program

@dataclass
class Program(Node):
    """Grammar rule `program`: all top-level declarations and functions."""

    items: list[Node]

    def children(self) -> list[Node]:
        """Top-level declarations and functions in source order."""
        return list(self.items)


@dataclass
class Param(Node):
    """Grammar rule `param`: one function parameter."""

    type_name: str
    name: str
    tac_name: str | None = annotation()

    def label(self) -> str:
        """Tree label for a parameter node (`Param <type> <name>`)."""
        return f"Param {self.type_name} {self.name}"


@dataclass
class Block(Node):
    """Grammar rule `block`: `{ statement* }`."""

    statements: list[Node]
    # Position of the closing `}` (D-034); 0 means unknown. Not compared, so tree tests stay structural.
    end_line: int = field(default=0, compare=False)
    end_col: int = field(default=0, compare=False)
    scope_id: int | None = annotation()

    def children(self) -> list[Node]:
        """Statements inside the block in source order."""
        return list(self.statements)


@dataclass
class FunctionDecl(Node):
    """Grammar rules `topLevel` and `funcRest`: a top-level function."""

    return_type: str
    name: str
    params: list[Param]
    body: Block
    scope_id: int | None = annotation()

    def label(self) -> str:
        """Tree label for a function declaration (`FunctionDecl <type> <name>`)."""
        return f"FunctionDecl {self.return_type} {self.name}"

    def children(self) -> list[Node]:
        """Parameters followed by the function body block."""
        return [*self.params, self.body]


@dataclass
class VarDecl(Node):
    """Grammar rules `varRest` and `varDecl`: a variable or constant declaration."""

    type_name: str
    name: str
    init: Node | None
    is_const: bool
    tac_name: str | None = annotation()

    def label(self) -> str:
        """Tree label for a variable or constant declaration (`VarDecl [const ]<type> <name>`)."""
        const = "const " if self.is_const else ""
        return f"VarDecl {const}{self.type_name} {self.name}"

    def children(self) -> list[Node]:
        """Single initializer expression child when present, else empty."""
        return [self.init] if self.init is not None else []


# ------------------------------------------------------------- statements

@dataclass
class Assign(Node):
    """Grammar rules `idStmt`, `forInit`, `forUpdate`: `name = expr`."""

    name: str
    value: Node
    tac_name: str | None = annotation()

    def label(self) -> str:
        """Tree label for an assignment (`Assign <name>`)."""
        return f"Assign {self.name}"

    def children(self) -> list[Node]:
        """Assigned value expression."""
        return [self.value]


@dataclass
class If(Node):
    """Grammar rule `ifStmt`. `else_branch` is a Block, another If (else-if), or None."""

    condition: Node
    then_block: Block
    else_branch: Node | None

    def children(self) -> list[Node]:
        """Condition, then-block, and optional else-branch in source order."""
        parts = [self.condition, self.then_block]
        if self.else_branch is not None:
            parts.append(self.else_branch)
        return parts


@dataclass
class While(Node):
    """Grammar rule `whileStmt`."""

    condition: Node
    body: Block

    def children(self) -> list[Node]:
        """Loop condition and body block."""
        return [self.condition, self.body]


@dataclass
class For(Node):
    """Grammar rule `forStmt`. `init` and `update` are optional."""

    init: Node | None
    condition: Node
    update: Node | None
    body: Block
    scope_id: int | None = annotation()

    def children(self) -> list[Node]:
        """Present parts of `(init?, condition, update?, body)` in source order."""
        parts = []
        if self.init is not None:
            parts.append(self.init)
        parts.append(self.condition)
        if self.update is not None:
            parts.append(self.update)
        parts.append(self.body)
        return parts


@dataclass
class Return(Node):
    """Grammar rule `returnStmt`."""

    value: Node

    def children(self) -> list[Node]:
        """Returned expression."""
        return [self.value]


@dataclass
class CallStmt(Node):
    """Grammar rule `idStmt` (call form): a call used as a statement."""

    call: "Call"

    def children(self) -> list[Node]:
        """Underlying `Call` node."""
        return [self.call]


# ------------------------------------------------------------ expressions

@dataclass
class BinaryOp(Node):
    """Grammar rules `orExpr` to `term`: a binary operator applied to two operands."""

    op: str
    left: Node
    right: Node
    expr_type: str | None = annotation()

    def label(self) -> str:
        """Tree label for a binary operator (`BinaryOp <op>`)."""
        return f"BinaryOp {self.op}"

    def children(self) -> list[Node]:
        """Left and right operand expressions."""
        return [self.left, self.right]


@dataclass
class UnaryOp(Node):
    """Grammar rule `unary`: prefix `-` or `!`."""

    op: str
    operand: Node
    expr_type: str | None = annotation()

    def label(self) -> str:
        """Tree label for a unary operator (`UnaryOp <op>`)."""
        return f"UnaryOp {self.op}"

    def children(self) -> list[Node]:
        """Single operand expression."""
        return [self.operand]


@dataclass
class Literal(Node):
    """Grammar rule `primary` (literal forms). `type_name` is int, float, char or bool."""

    value: str
    type_name: str
    expr_type: str | None = annotation()

    def label(self) -> str:
        """Tree label for a literal (`Literal <value> (<type>)`)."""
        return f"Literal {self.value} ({self.type_name})"


@dataclass
class Identifier(Node):
    """Grammar rule `primary` (a variable use)."""

    name: str
    expr_type: str | None = annotation()
    tac_name: str | None = annotation()

    def label(self) -> str:
        """Tree label for an identifier (`Identifier <name>`)."""
        return f"Identifier {self.name}"


@dataclass
class Call(Node):
    """Grammar rule `primary` (call form): `name(args)`."""

    name: str
    args: list[Node]
    expr_type: str | None = annotation()

    def label(self) -> str:
        """Tree label for a function call (`Call <name>`)."""
        return f"Call {self.name}"

    def children(self) -> list[Node]:
        """Argument expressions in source order."""
        return list(self.args)
