"""Three-address code (TAC) generator (SPEC section 11, interfaces.md: tacgen.py).

Translates an error-free, semantically annotated `Program` parse tree into linear
three-address instructions. Temporaries (`t1, t2, ...`) and labels (`L1, L2, ...`)
are numbered per program in creation order. Every variable reference uses its
semantic `tac_name` annotation (D-029); missing annotations raise `ValueError`.
"""
from src.ast_nodes import (
    Assign, BinaryOp, Block, Call, CallStmt, For, FunctionDecl, Identifier,
    If, Literal, Node, Program, Return, UnaryOp, VarDecl, While)


def require_tac_name(node: Node) -> str:
    """Return `node.tac_name`, or raise `ValueError` if semantic analysis did not set it."""
    tac_name = getattr(node, "tac_name", None)
    if not tac_name:
        name = getattr(node, "name", "<unknown>")
        raise ValueError(
            f"Missing tac_name annotation on {type(node).__name__} '{name}' "
            "(precondition violated: tree must be analyzed before TAC generation)"
        )
    return tac_name


class TACGenerator:
    """Walks an analyzed `Program` tree and emits SPEC section 11 TAC lines."""

    def __init__(self) -> None:
        """Start with empty output lines and 0-based counters for `t1..` and `L1..`."""
        self.lines: list[str] = []
        self.temp_count: int = 0
        self.label_count: int = 0

    # ------------------------------------------------------------------ helpers

    def new_temp(self) -> str:
        """Allocate and return the next program-wide temporary name (`t1`, `t2`, ...)."""
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self) -> str:
        """Allocate and return the next program-wide label name (`L1`, `L2`, ...)."""
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, instruction: str) -> None:
        """Append one two-space-indented TAC instruction line."""
        self.lines.append(f"  {instruction}")

    def emit_header(self, header: str) -> None:
        """Append one column-0 label, `globals:`, `func name:`, or `endfunc` line."""
        self.lines.append(header)

    # --------------------------------------------------------- program & topLevel

    def gen_program(self, tree: Program) -> list[str]:
        """Grammar rule `program -> topLevel* EOF`: emit `globals:` first, then functions."""
        self.gen_globals(tree.items)
        for item in tree.items:
            if isinstance(item, FunctionDecl):
                self.gen_function(item)
        return self.lines

    def gen_globals(self, items: list[Node]) -> None:
        """SPEC section 11: initialized global `VarDecl`s are emitted first under `globals:`."""
        global_decls = [item for item in items if isinstance(item, VarDecl)]
        for decl in global_decls:
            # Verify precondition even on uninitialized globals so unanalyzed trees fail loudly.
            require_tac_name(decl)
        initialized = [decl for decl in global_decls if decl.init is not None]
        if not initialized:
            return
        self.emit_header("globals:")
        for decl in initialized:
            self.gen_var_decl(decl)

    def gen_function(self, fn: FunctionDecl) -> None:
        """Grammar rule `funcRest -> '(' params? ')' block`: `func name: ... endfunc`."""
        self.emit_header(f"func {fn.name}:")
        self.gen_block(fn.body)
        self.emit_header("endfunc")

    # --------------------------------------------------------------- statements

    def gen_block(self, block: Block) -> None:
        """Grammar rule `block -> '{' statement* '}'`: emit each statement in order."""
        for stmt in block.statements:
            self.gen_statement(stmt)

    def gen_statement(self, stmt: Node) -> None:
        """Grammar rule `statement`: dispatch to the matching statement generator."""
        if isinstance(stmt, VarDecl):
            self.gen_var_decl(stmt)
        elif isinstance(stmt, Assign):
            self.gen_assign(stmt)
        elif isinstance(stmt, If):
            self.gen_if(stmt)
        elif isinstance(stmt, While):
            self.gen_while(stmt)
        elif isinstance(stmt, For):
            self.gen_for(stmt)
        elif isinstance(stmt, Return):
            self.gen_return(stmt)
        elif isinstance(stmt, CallStmt):
            self.gen_call_stmt(stmt)
        elif isinstance(stmt, Block):
            self.gen_block(stmt)

    def gen_var_decl(self, decl: VarDecl) -> None:
        """Grammar rules `varDecl` / `varRest`: emit `<tac_name> = <init>` when initialized."""
        target = require_tac_name(decl)
        if decl.init is None:
            return
        value = self.gen_expr(decl.init)
        self.emit(f"{target} = {value}")

    def gen_assign(self, stmt: Assign) -> None:
        """Grammar rules `idStmt`, `forInit`, `forUpdate`: emit `<tac_name> = <value>`."""
        target = require_tac_name(stmt)
        value = self.gen_expr(stmt.value)
        self.emit(f"{target} = {value}")

    def gen_if(self, stmt: If) -> None:
        """Grammar rule `ifStmt` (SPEC section 11 `if` / `if-else` shapes).

        Labels for this `if` are allocated BEFORE generating `then_block` or `else_branch`
        so outer labels get lower numbers than nested control-flow labels.
        """
        cond = self.gen_expr(stmt.condition)
        if stmt.else_branch is None:
            end_label = self.new_label()
            self.emit(f"ifFalse {cond} goto {end_label}")
            self.gen_block(stmt.then_block)
            self.emit_header(f"{end_label}:")
            return
        else_label = self.new_label()
        end_label = self.new_label()
        self.emit(f"ifFalse {cond} goto {else_label}")
        self.gen_block(stmt.then_block)
        self.emit(f"goto {end_label}")
        self.emit_header(f"{else_label}:")
        if isinstance(stmt.else_branch, If):
            self.gen_if(stmt.else_branch)
        elif isinstance(stmt.else_branch, Block):
            self.gen_block(stmt.else_branch)
        self.emit_header(f"{end_label}:")

    def gen_while(self, stmt: While) -> None:
        """Grammar rule `whileStmt` (SPEC section 11 `while` shape)."""
        start_label = self.new_label()
        end_label = self.new_label()
        self.emit_header(f"{start_label}:")
        cond = self.gen_expr(stmt.condition)
        self.emit(f"ifFalse {cond} goto {end_label}")
        self.gen_block(stmt.body)
        self.emit(f"goto {start_label}")
        self.emit_header(f"{end_label}:")

    def gen_for(self, stmt: For) -> None:
        """Grammar rule `forStmt` (SPEC section 11 `for` shape)."""
        if isinstance(stmt.init, VarDecl):
            self.gen_var_decl(stmt.init)
        elif isinstance(stmt.init, Assign):
            self.gen_assign(stmt.init)
        start_label = self.new_label()
        end_label = self.new_label()
        self.emit_header(f"{start_label}:")
        cond = self.gen_expr(stmt.condition)
        self.emit(f"ifFalse {cond} goto {end_label}")
        self.gen_block(stmt.body)
        if stmt.update is not None:
            self.gen_assign(stmt.update)
        self.emit(f"goto {start_label}")
        self.emit_header(f"{end_label}:")

    def gen_return(self, stmt: Return) -> None:
        """Grammar rule `returnStmt -> 'return' expr ';'`: emit `return <val>`."""
        value = self.gen_expr(stmt.value)
        self.emit(f"return {value}")

    def gen_call_stmt(self, stmt: CallStmt) -> None:
        """Grammar rule `idStmt` (call form): emit `param` lines and `call f, n` (result unused)."""
        args = [self.gen_expr(arg) for arg in stmt.call.args]
        for arg in args:
            self.emit(f"param {arg}")
        self.emit(f"call {stmt.call.name}, {len(args)}")

    # -------------------------------------------------------------- expressions

    def gen_expr(self, node: Node) -> str:
        """Grammar rule `expr`: emit instructions for `node` and return its operand name/literal."""
        if isinstance(node, Literal):
            return node.value
        if isinstance(node, Identifier):
            return require_tac_name(node)
        if isinstance(node, UnaryOp):
            return self.gen_unary(node)
        if isinstance(node, BinaryOp):
            return self.gen_binary(node)
        if isinstance(node, Call):
            return self.gen_call_expr(node)
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    def gen_unary(self, node: UnaryOp) -> str:
        """Grammar rule `unary -> ( '-' | '!' ) unary`: emit `tK = op y` and return `tK`."""
        operand = self.gen_expr(node.operand)
        temp = self.new_temp()
        self.emit(f"{temp} = {node.op} {operand}")
        return temp

    def gen_binary(self, node: BinaryOp) -> str:
        """Grammar rules `orExpr` to `term`: emit `tK = left op right` (including `&&`, `||`, D-005).

        Walks down the left spine iteratively so long left-associative chains (800 or 3000 terms)
        never hit Python's recursion limit.
        """
        spine: list[BinaryOp] = []
        current: Node = node
        while isinstance(current, BinaryOp):
            spine.append(current)
            current = current.left
        left = self.gen_expr(current)
        for operation in reversed(spine):
            right = self.gen_expr(operation.right)
            temp = self.new_temp()
            self.emit(f"{temp} = {left} {operation.op} {right}")
            left = temp
        return left

    def gen_call_expr(self, node: Call) -> str:
        """Grammar rule `primary -> ID '(' args? ')'`: evaluate args first, then `param` and `call`."""
        args = [self.gen_expr(arg) for arg in node.args]
        for arg in args:
            self.emit(f"param {arg}")
        temp = self.new_temp()
        self.emit(f"{temp} = call {node.name}, {len(args)}")
        return temp


def generate(tree: Program) -> list[str]:
    """Generate three-address code lines for an error-free, analyzed `Program` (interfaces.md)."""
    return TACGenerator().gen_program(tree)
