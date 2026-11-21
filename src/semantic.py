"""Semantic analyzer (SPEC section 8, interfaces.md: semantic.py).

Phase 5a: scopes, declarations and expression typing.
Phase 5b: function rules (callee, arity, argument types, return type, missing return).
"""
import re

from src.ast_nodes import (Assign, BinaryOp, Block, Call, CallStmt, For, FunctionDecl, Identifier,
                           If, Literal, Node, Program, Return, UnaryOp, VarDecl, While)
from src.errors import ErrorCollector
from src.symbol_table import Symbol, SymbolTable

ERROR = "error"   # internal type: an expression that already caused an error (no cascades)
NUMERIC = ("int", "float", "char")
INT_LIKE = ("int", "char")
ARITH_OPS = ("+", "-", "*", "/")
RELATIONAL_OPS = ("<", ">", "<=", ">=")
EQUALITY_OPS = ("==", "!=")
LOGICAL_OPS = ("&&", "||")
# Names the TAC generator uses for temporaries (t1) and labels (L1); a variable must never get one.
RESERVED_TAC_NAME = re.compile(r"^[tL][0-9]+$")
# SPEC section 8 assignability table as (value type, target type) pairs; everything else is an error.
ASSIGNABLE = {("int", "int"), ("int", "float"), ("float", "float"), ("char", "int"),
              ("char", "float"), ("char", "char"), ("bool", "bool")}


def is_assignable(value_type: str, target_type: str) -> bool:
    """SPEC section 8 assignability table; an `error` side is accepted so errors never cascade."""
    if ERROR in (value_type, target_type):
        return True
    return (value_type, target_type) in ASSIGNABLE


def numeric_result(left: str, right: str) -> str:
    """Result type of numeric arithmetic: float if either side is float, else int (char promoted)."""
    return "float" if "float" in (left, right) else "int"


class Analyzer:
    """Walks the tree once (pass 2) after the function signatures are collected (pass 1)."""

    def __init__(self, errors: ErrorCollector) -> None:
        """Start with an empty symbol table; `used_names` tracks every tac_name handed out."""
        self.errors = errors
        self.table = SymbolTable()
        self.used_names: set[str] = set()
        self.name_counts: dict[str, int] = {}
        # The function whose body is being checked (set by check_function, restored afterwards).
        self.current_function: FunctionDecl | None = None

    # ------------------------------------------------------------------ helpers

    def report(self, node: Node, message: str) -> None:
        """Report a Semantic error at the node's own line and column."""
        self.errors.report("Semantic", node.line, node.col, message)

    def make_tac_name(self, name: str) -> str:
        """Unique TAC name: `x`, then `x_1`, `x_2`; names like t1 or L2 count as taken (D-029)."""
        candidate = name
        count = self.name_counts.get(name, 0)
        while candidate in self.used_names or RESERVED_TAC_NAME.match(candidate):
            count += 1
            candidate = f"{name}_{count}"
        self.name_counts[name] = count
        self.used_names.add(candidate)
        return candidate

    # ----------------------------------------------------------- program, pass 1

    def analyze_program(self, tree: Program) -> SymbolTable:
        """Open the global scope, collect all signatures (pass 1), then check items in order (pass 2)."""
        self.table.enter_scope("global")
        self.collect_functions(tree)
        for item in tree.items:
            if isinstance(item, FunctionDecl):
                self.check_function(item)
            elif isinstance(item, VarDecl):
                self.check_var_decl(item)   # a global is visible only after this point
        self.table.exit_scope()
        return self.table

    def collect_functions(self, tree: Program) -> None:
        """Pass 1: put every function signature in the global scope (SPEC section 8, Functions)."""
        for item in tree.items:
            if not isinstance(item, FunctionDecl):
                continue
            params = [(p.type_name, p.name) for p in item.params]
            symbol = Symbol(item.name, item.return_type, "func", 0, item.line, params=params,
                            tac_name=item.name)
            if not self.table.declare(symbol):
                first = self.table.lookup_current(item.name)
                self.report(item, f"Function '{item.name}' is already declared (line {first.line})")

    # --------------------------------------------------------------- pass 2: bodies

    def check_function(self, fn: FunctionDecl) -> None:
        """One function scope shared by the parameters and the body's top level (SPEC section 8)."""
        outer_function = self.current_function
        self.current_function = fn
        fn.scope_id = self.table.enter_scope(f"function {fn.name}")
        fn.body.scope_id = fn.scope_id
        for param in fn.params:
            self.declare_variable(param, param.type_name, "param")
        self.check_statements(fn.body.statements)
        self.check_missing_return(fn)
        self.table.exit_scope()
        self.current_function = outer_function

    def check_missing_return(self, fn: FunctionDecl) -> None:
        """SPEC section 8: the LAST top-level statement of a body must be a `return`.

        Strict on purpose (D-035): an if/else whose branches both return still counts as missing.
        Reported at the closing brace; a Block without a known end (end_line 0) falls back to the header.
        """
        statements = fn.body.statements
        if statements and isinstance(statements[-1], Return):
            return
        known = fn.body.end_line > 0
        line, col = (fn.body.end_line, fn.body.end_col) if known else (fn.line, fn.col)
        self.errors.report("Semantic", line, col, f"Missing return at end of function '{fn.name}'")

    def check_statements(self, statements: list[Node]) -> None:
        """Check each statement of a block in order."""
        for statement in statements:
            self.check_statement(statement)

    def check_block(self, block: Block) -> None:
        """A nested block opens its own scope (SPEC section 8)."""
        block.scope_id = self.table.enter_scope("block")
        self.check_statements(block.statements)
        self.table.exit_scope()

    def check_statement(self, stmt: Node) -> None:
        """Dispatch on the statement class (grammar rule `statement`)."""
        if isinstance(stmt, VarDecl):
            self.check_var_decl(stmt)
        elif isinstance(stmt, Assign):
            self.check_assign(stmt)
        elif isinstance(stmt, If):
            self.check_if(stmt)
        elif isinstance(stmt, While):
            self.check_condition(stmt.condition, "while")
            self.check_block(stmt.body)
        elif isinstance(stmt, For):
            self.check_for(stmt)
        elif isinstance(stmt, Return):
            self.check_return(stmt)
        elif isinstance(stmt, CallStmt):
            self.type_expr(stmt.call)
        elif isinstance(stmt, Block):
            self.check_block(stmt)

    def check_return(self, stmt: Return) -> None:
        """returnStmt: the value must be assignable to the enclosing function's return type (SPEC section 8)."""
        value_type = self.type_expr(stmt.value)
        fn = self.current_function
        if fn is not None and not is_assignable(value_type, fn.return_type):
            self.report(stmt, f"Cannot return {value_type} from function '{fn.name}' returning {fn.return_type}")

    def check_if(self, stmt: If) -> None:
        """ifStmt: bool condition, then block, and an else block or a nested else-if."""
        self.check_condition(stmt.condition, "if")
        self.check_block(stmt.then_block)
        if isinstance(stmt.else_branch, If):
            self.check_if(stmt.else_branch)
        elif isinstance(stmt.else_branch, Block):
            self.check_block(stmt.else_branch)

    def check_for(self, stmt: For) -> None:
        """forStmt: its own scope holds the init variable; the body is a block inside it."""
        stmt.scope_id = self.table.enter_scope("for")
        if isinstance(stmt.init, VarDecl):
            self.check_var_decl(stmt.init)
        elif isinstance(stmt.init, Assign):
            self.check_assign(stmt.init)
        self.check_condition(stmt.condition, "for")
        if stmt.update is not None:
            self.check_assign(stmt.update)
        self.check_block(stmt.body)
        self.table.exit_scope()

    def check_condition(self, condition: Node, keyword: str) -> None:
        """The condition of if, while and for must be bool; reported at the condition expression."""
        found = self.type_expr(condition)
        if found not in ("bool", ERROR):
            self.report(condition, f"Condition of '{keyword}' must be bool, found {found}")

    # ------------------------------------------------------------------ declarations

    def declare_variable(self, node: Node, type_name: str, kind: str) -> None:
        """Declare a variable, constant or parameter and give it its unique tac_name."""
        symbol = Symbol(node.name, type_name, kind, self.table.current_level(), node.line,
                        tac_name=self.make_tac_name(node.name))
        node.tac_name = symbol.tac_name
        if not self.table.declare(symbol):
            first = self.table.lookup_current(node.name)
            self.report(node, f"'{node.name}' is already declared in this scope (line {first.line})")

    def check_var_decl(self, decl: VarDecl) -> None:
        """varDecl/varRest: const needs an initializer; the initializer is typed BEFORE the name is
        declared, so `int x = x;` reports an undeclared x (D-028)."""
        if decl.is_const and decl.init is None:
            self.report(decl, f"Constant '{decl.name}' must have an initializer")
        if decl.init is not None:
            value_type = self.type_expr(decl.init)
            self.check_assignable(value_type, decl.type_name, decl.name, decl)
        self.declare_variable(decl, decl.type_name, "const" if decl.is_const else "var")

    def check_assignable(self, value_type: str, target_type: str, name: str, node: Node) -> None:
        """Report `Cannot assign V to T variable 'name'` when the SPEC table says no."""
        if not is_assignable(value_type, target_type):
            self.report(node, f"Cannot assign {value_type} to {target_type} variable '{name}'")

    def check_assign(self, stmt: Assign) -> None:
        """Assignment statement: the target must be a declared, non-const variable and assignable."""
        value_type = self.type_expr(stmt.value)
        symbol = self.table.lookup(stmt.name)
        if symbol is None:
            self.report(stmt, f"Undeclared identifier '{stmt.name}'")
        elif symbol.kind == "func":
            self.report(stmt, f"Cannot assign to function '{stmt.name}'")
        else:
            stmt.tac_name = symbol.tac_name
            if symbol.kind == "const":
                self.report(stmt, f"Cannot assign to constant '{stmt.name}'")
            else:
                self.check_assignable(value_type, symbol.type_name, stmt.name, stmt)

    # ------------------------------------------------------------ expression typing

    def type_expr(self, node: Node) -> str:
        """Compute, store in `expr_type` and return the type of an expression (SPEC section 8)."""
        if isinstance(node, Literal):
            result = node.type_name
        elif isinstance(node, Identifier):
            result = self.type_identifier(node)
        elif isinstance(node, Call):
            result = self.type_call(node)
        elif isinstance(node, UnaryOp):
            result = self.type_unary(node)
        elif isinstance(node, BinaryOp):
            result = self.type_binary(node)
        else:
            return ERROR
        node.expr_type = result
        return result

    def type_identifier(self, node: Identifier) -> str:
        """A variable use: must be declared and must not be a function name."""
        symbol = self.table.lookup(node.name)
        if symbol is None:
            self.report(node, f"Undeclared identifier '{node.name}'")
            return ERROR
        if symbol.kind == "func":
            self.report(node, f"Function '{node.name}' cannot be used as a variable")
            return ERROR
        node.tac_name = symbol.tac_name
        return symbol.type_name

    def type_call(self, node: Call) -> str:
        """Call rule: the callee must be a function, arity and argument types must match (SPEC section 8).

        Every argument is typed first so errors inside arguments are always reported. A call to a
        non-function has type `error`; a call with bad arguments still has the function's return type.
        """
        argument_types = [self.type_expr(argument) for argument in node.args]
        symbol = self.table.lookup(node.name)
        if symbol is None:
            self.report(node, f"Call to undeclared function '{node.name}'")
            return ERROR
        if symbol.kind != "func":
            self.report(node, f"Cannot call '{node.name}': it is a variable, not a function")
            return ERROR
        self.check_arguments(node, symbol, argument_types)
        return symbol.type_name

    def check_arguments(self, node: Call, symbol: Symbol, argument_types: list[str]) -> None:
        """Arity first; only when the count is right is each argument compared with its parameter."""
        expected = len(symbol.params)
        if len(node.args) != expected:
            noun = "argument" if expected == 1 else "arguments"
            self.report(node, f"Function '{node.name}' expects {expected} {noun}, found {len(node.args)}")
            return
        for index, (argument, found) in enumerate(zip(node.args, argument_types), start=1):
            param_type, param_name = symbol.params[index - 1]
            if not is_assignable(found, param_type):
                self.report(argument, f"Argument {index} of '{node.name}': "
                                      f"cannot pass {found} to {param_type} parameter '{param_name}'")

    def type_unary(self, node: UnaryOp) -> str:
        """unary: `-` needs a numeric operand, `!` needs a bool."""
        operand = self.type_expr(node.operand)
        if operand == ERROR:
            return ERROR
        if node.op == "-" and operand in NUMERIC:
            return "float" if operand == "float" else "int"
        if node.op == "!" and operand == "bool":
            return "bool"
        article = "a numeric operand" if node.op == "-" else "a bool operand"
        self.report(node, f"Operator '{node.op}' requires {article}, found {operand}")
        return ERROR

    def type_binary(self, node: BinaryOp) -> str:
        """Binary operators per the SPEC section 8 table; any `error` operand gives `error` silently.

        The parser nests `a + b + c` to the LEFT, so a long chain is walked with a loop down the
        left spine (not recursion): 2000 terms must not hit Python's recursion limit.
        """
        spine: list[BinaryOp] = []
        current: Node = node
        while isinstance(current, BinaryOp):
            spine.append(current)
            current = current.left
        left = self.type_expr(current)
        for operation in reversed(spine):
            right = self.type_expr(operation.right)
            left = self.apply_binary(operation, left, right)
            operation.expr_type = left
        return left

    def apply_binary(self, node: BinaryOp, left: str, right: str) -> str:
        """Type one binary node from its operand types, reporting at the operator if not allowed."""
        if ERROR in (left, right):
            return ERROR
        result = self.binary_result(node.op, left, right)
        if result is not None:
            return result
        self.report(node, self.binary_message(node.op, left, right))
        return ERROR

    def binary_result(self, op: str, left: str, right: str) -> str | None:
        """Result type of `left op right`, or None when the operand types are not allowed."""
        both_numeric = left in NUMERIC and right in NUMERIC
        if op in ARITH_OPS and both_numeric:
            return numeric_result(left, right)
        if op == "%" and left in INT_LIKE and right in INT_LIKE:
            return "int"
        if op in RELATIONAL_OPS and both_numeric:
            return "bool"
        if op in EQUALITY_OPS and (both_numeric or left == right == "bool"):
            return "bool"
        if op in LOGICAL_OPS and left == right == "bool":
            return "bool"
        return None

    def binary_message(self, op: str, left: str, right: str) -> str:
        """The error text for a rejected binary operator (templates 10 to 14 of the plan)."""
        found = f"found {left} and {right}"
        if op == "%":
            return f"Operator '%' requires int or char operands, {found}"
        if op in EQUALITY_OPS:
            return f"Operator '{op}' requires two numeric or two bool operands, {found}"
        if op in LOGICAL_OPS:
            return f"Operator '{op}' requires bool operands, {found}"
        return f"Operator '{op}' requires numeric operands, {found}"


def analyze(tree: Program, errors: ErrorCollector) -> SymbolTable:
    """Run both semantic passes over `tree`, annotate it, and return the symbol table.

    Pass 1 collects function signatures; pass 2 checks bodies. Reports every error found.
    """
    analyzer = Analyzer(errors)
    try:
        return analyzer.analyze_program(tree)
    except RecursionError:
        # Safety net (SPEC section 9: never crash): absurdly deep nesting, e.g. 900 unary minus signs.
        errors.report("Semantic", tree.line, tree.col, "Program is nested too deeply to analyze")
        return analyzer.table
