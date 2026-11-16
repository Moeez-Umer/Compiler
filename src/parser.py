"""Recursive descent LL(1) parser for SmartLang (SPEC section 6, D-002).

One method per grammar rule, named after the rule (`parse_if_stmt` for
`ifStmt`). Precedence comes from rule layering and left associativity from
loops. A level with a single operand returns that operand unchanged (D-004).

Phase 2 scope: valid programs. There is no panic-mode recovery yet (that is
Phase 3, D-003). On the first unexpected token the parser reports ONE Syntax
error and returns the declarations it finished before that point (D-018).
"""
from src.ast_nodes import (
    Assign, BinaryOp, Block, Call, CallStmt, For, FunctionDecl, Identifier,
    If, Literal, Node, Param, Program, Return, UnaryOp, VarDecl, While)
from src.errors import ErrorCollector
from src.tokens import Token, TokenType

TYPE_KEYWORDS = ("int", "float", "char", "bool")
LITERAL_TYPES = {
    TokenType.INT_LIT: "int",
    TokenType.FLOAT_LIT: "float",
    TokenType.CHAR_LIT: "char",
}
SYMBOL_TYPES = (TokenType.KEYWORD, TokenType.OPERATOR, TokenType.DELIMITER)

OR_OPS = ("||",)
AND_OPS = ("&&",)
EQ_OPS = ("==", "!=")
REL_OPS = ("<", ">", "<=", ">=")
ADD_OPS = ("+", "-")
TERM_OPS = ("*", "/", "%")


class ParseError(Exception):
    """Internal signal that the next token does not fit the grammar.

    Never escapes parse(): it is caught there and turned into a Syntax error.
    """

    def __init__(self, line: int, col: int, message: str, after_invalid: bool = False):
        super().__init__(message)
        self.line = line
        self.col = col
        self.message = message
        # True when the offending token comes right after a skipped INVALID token (D-020).
        self.after_invalid = after_invalid


class Parser:
    """Holds the token list and a cursor; one parse_* method per grammar rule."""

    def __init__(self, tokens: list[Token]):
        # INVALID tokens were already reported by the lexer, so skip them silently.
        # `after_invalid` remembers which kept tokens followed a skipped one, so a
        # syntax error caused only by the missing token is not reported twice (D-020).
        self.tokens: list[Token] = []
        self.after_invalid: set[int] = set()
        skipped = False
        for token in tokens:
            if token.type == TokenType.INVALID:
                skipped = True
                continue
            if skipped:
                self.after_invalid.add(len(self.tokens))
                skipped = False
            self.tokens.append(token)
        self.pos = 0

    # ------------------------------------------------------------ helpers

    def peek(self, offset: int = 0) -> Token:
        """Look ahead without consuming. Past the end, keep returning EOF."""
        index = min(self.pos + offset, len(self.tokens) - 1)
        if index < 0:
            return Token(TokenType.EOF, "", 1, 1)
        return self.tokens[index]

    def advance(self) -> Token:
        """Consume and return the current token (never moves past EOF)."""
        token = self.peek()
        if token.type != TokenType.EOF:
            self.pos += 1
        return token

    def at(self, *lexemes: str) -> bool:
        """True if the current token is a keyword, operator or delimiter in `lexemes`."""
        token = self.peek()
        return token.type in SYMBOL_TYPES and token.lexeme in lexemes

    def at_type(self) -> bool:
        """True if the current token starts a `type`."""
        return self.at(*TYPE_KEYWORDS)

    def found(self) -> str:
        """Describe the current token for an error message."""
        token = self.peek()
        return "end of file" if token.type == TokenType.EOF else f"'{token.lexeme}'"

    def follows_invalid(self) -> bool:
        """True if the current token directly follows a skipped INVALID token."""
        return min(self.pos, len(self.tokens) - 1) in self.after_invalid

    def fail(self, expected: str) -> ParseError:
        """Build the error for the current token: `Expected X but found Y`."""
        token = self.peek()
        return ParseError(token.line, token.col, f"Expected {expected} but found {self.found()}",
                          after_invalid=self.follows_invalid())

    def expect(self, lexeme: str) -> Token:
        """Consume the keyword, operator or delimiter `lexeme`, or fail."""
        if not self.at(lexeme):
            raise self.fail(f"'{lexeme}'")
        return self.advance()

    def expect_identifier(self) -> Token:
        """Consume an IDENTIFIER token, or fail."""
        if self.peek().type != TokenType.IDENTIFIER:
            raise self.fail("identifier")
        return self.advance()

    # ------------------------------------------------- program and top level

    def parse_program(self, errors: ErrorCollector) -> Program:
        """program -> topLevel* EOF.  Reports one Syntax error and stops at the first problem."""
        items: list[Node] = []
        try:
            while self.peek().type != TokenType.EOF:
                items.append(self.parse_top_level())
        except ParseError as error:
            # The lexer already reported the INVALID token that caused this error (D-020).
            if not error.after_invalid:
                errors.report("Syntax", error.line, error.col, error.message)
        except RecursionError:
            token = self.peek()
            errors.report("Syntax", token.line, token.col, "Program is nested too deeply")
        return Program(items=items, line=1, col=1)

    def parse_top_level(self) -> Node:
        """topLevel -> 'const' type ID varRest | type ID ( funcRest | varRest )."""
        start = self.peek()
        is_const = self.at("const")
        if is_const:
            self.advance()
        type_name = self.parse_type()
        name = self.expect_identifier().lexeme
        if not is_const and self.at("("):
            return self.parse_func_rest(type_name, name, start)
        return self.parse_var_rest(type_name, name, is_const, start)

    def parse_var_rest(self, type_name: str, name: str, is_const: bool, start: Token) -> VarDecl:
        """varRest -> ( '=' expr )? ';'.  `start` is the first token of the declaration."""
        init = None
        if self.at("="):
            self.advance()
            init = self.parse_expr()
        self.expect(";")
        return VarDecl(type_name=type_name, name=name, init=init, is_const=is_const,
                       line=start.line, col=start.col)

    def parse_func_rest(self, return_type: str, name: str, start: Token) -> FunctionDecl:
        """funcRest -> '(' params? ')' block."""
        self.expect("(")
        params = [] if self.at(")") else self.parse_params()
        self.expect(")")
        body = self.parse_block()
        return FunctionDecl(return_type=return_type, name=name, params=params, body=body,
                            line=start.line, col=start.col)

    def parse_params(self) -> list[Param]:
        """params -> param ( ',' param )*."""
        params = [self.parse_param()]
        while self.at(","):
            self.advance()
            params.append(self.parse_param())
        return params

    def parse_param(self) -> Param:
        """param -> type ID."""
        start = self.peek()
        type_name = self.parse_type()
        name = self.expect_identifier().lexeme
        return Param(type_name=type_name, name=name, line=start.line, col=start.col)

    def parse_type(self) -> str:
        """type -> 'int' | 'float' | 'char' | 'bool'."""
        if not self.at_type():
            raise self.fail("type")
        return self.advance().lexeme

    # ------------------------------------------------------------ statements

    def parse_block(self) -> Block:
        """block -> '{' statement* '}'."""
        start = self.expect("{")
        statements = []
        while not self.at("}"):
            statements.append(self.parse_statement())
        self.expect("}")
        return Block(statements=statements, line=start.line, col=start.col)

    def parse_statement(self) -> Node:
        """statement -> varDecl | idStmt | ifStmt | whileStmt | forStmt | returnStmt | block.

        One token of lookahead picks the alternative (LL(1)).
        """
        if self.at("const") or self.at_type():
            return self.parse_var_decl()
        if self.peek().type == TokenType.IDENTIFIER:
            return self.parse_id_stmt()
        if self.at("if"):
            return self.parse_if_stmt()
        if self.at("while"):
            return self.parse_while_stmt()
        if self.at("for"):
            return self.parse_for_stmt()
        if self.at("return"):
            return self.parse_return_stmt()
        if self.at("{"):
            return self.parse_block()
        raise self.fail("statement")

    def parse_var_decl(self) -> VarDecl:
        """varDecl -> 'const'? type ID ( '=' expr )? ';'."""
        start = self.peek()
        is_const = self.at("const")
        if is_const:
            self.advance()
        type_name = self.parse_type()
        name = self.expect_identifier().lexeme
        return self.parse_var_rest(type_name, name, is_const, start)

    def parse_id_stmt(self) -> Node:
        """idStmt -> ID ( '=' expr | '(' args? ')' ) ';'.  Assignment or call statement."""
        name_token = self.expect_identifier()
        if self.at("("):
            call = self.parse_call_rest(name_token)
            self.expect(";")
            return CallStmt(call=call, line=name_token.line, col=name_token.col)
        stmt = self.parse_assignment(name_token)
        self.expect(";")
        return stmt

    def parse_assignment(self, name_token: Token) -> Assign:
        """The `ID '=' expr` part shared by idStmt, forInit and forUpdate (ID already consumed)."""
        self.expect("=")
        value = self.parse_expr()
        return Assign(name=name_token.lexeme, value=value,
                      line=name_token.line, col=name_token.col)

    def parse_if_stmt(self) -> If:
        """ifStmt -> 'if' '(' expr ')' block ( 'else' ( ifStmt | block ) )?."""
        start = self.expect("if")
        self.expect("(")
        condition = self.parse_expr()
        self.expect(")")
        then_block = self.parse_block()
        else_branch = None
        if self.at("else"):
            self.advance()
            # `else if` nests as an If inside else_branch, so chains need no special node.
            else_branch = self.parse_if_stmt() if self.at("if") else self.parse_block()
        return If(condition=condition, then_block=then_block, else_branch=else_branch,
                  line=start.line, col=start.col)

    def parse_while_stmt(self) -> While:
        """whileStmt -> 'while' '(' expr ')' block."""
        start = self.expect("while")
        self.expect("(")
        condition = self.parse_expr()
        self.expect(")")
        body = self.parse_block()
        return While(condition=condition, body=body, line=start.line, col=start.col)

    def parse_for_stmt(self) -> For:
        """forStmt -> 'for' '(' forInit? ';' expr ';' forUpdate? ')' block."""
        start = self.expect("for")
        self.expect("(")
        init = None if self.at(";") else self.parse_for_init()
        self.expect(";")
        condition = self.parse_expr()
        self.expect(";")
        update = None if self.at(")") else self.parse_for_update()
        self.expect(")")
        body = self.parse_block()
        return For(init=init, condition=condition, update=update, body=body,
                   line=start.line, col=start.col)

    def parse_for_init(self) -> Node:
        """forInit -> type ID '=' expr | ID '=' expr."""
        start = self.peek()
        if self.at_type():
            type_name = self.parse_type()
            name = self.expect_identifier().lexeme
            self.expect("=")
            init = self.parse_expr()
            return VarDecl(type_name=type_name, name=name, init=init, is_const=False,
                           line=start.line, col=start.col)
        return self.parse_assignment(self.expect_identifier())

    def parse_for_update(self) -> Assign:
        """forUpdate -> ID '=' expr."""
        return self.parse_assignment(self.expect_identifier())

    def parse_return_stmt(self) -> Return:
        """returnStmt -> 'return' expr ';'."""
        start = self.expect("return")
        value = self.parse_expr()
        self.expect(";")
        return Return(value=value, line=start.line, col=start.col)

    def parse_args(self) -> list[Node]:
        """args -> expr ( ',' expr )*."""
        args = [self.parse_expr()]
        while self.at(","):
            self.advance()
            args.append(self.parse_expr())
        return args

    # ----------------------------------------------------------- expressions

    def parse_binary_level(self, parse_operand, operators: tuple[str, ...]) -> Node:
        """Shared loop for the left-associative levels: operand ( op operand )*.

        With no operator present the single operand is returned as is (D-004).
        Each new BinaryOp wraps the tree built so far as its LEFT child, which
        is what makes `a - b - c` group as `(a - b) - c`.
        """
        left = parse_operand()
        while self.at(*operators):
            op_token = self.advance()
            right = parse_operand()
            left = BinaryOp(op=op_token.lexeme, left=left, right=right,
                            line=op_token.line, col=op_token.col)
        return left

    def parse_expr(self) -> Node:
        """expr -> orExpr."""
        return self.parse_or_expr()

    def parse_or_expr(self) -> Node:
        """orExpr -> andExpr ( '||' andExpr )*.  Lowest precedence."""
        return self.parse_binary_level(self.parse_and_expr, OR_OPS)

    def parse_and_expr(self) -> Node:
        """andExpr -> eqExpr ( '&&' eqExpr )*."""
        return self.parse_binary_level(self.parse_eq_expr, AND_OPS)

    def parse_eq_expr(self) -> Node:
        """eqExpr -> relExpr ( ( '==' | '!=' ) relExpr )*."""
        return self.parse_binary_level(self.parse_rel_expr, EQ_OPS)

    def parse_rel_expr(self) -> Node:
        """relExpr -> addExpr ( ( '<' | '>' | '<=' | '>=' ) addExpr )*."""
        return self.parse_binary_level(self.parse_add_expr, REL_OPS)

    def parse_add_expr(self) -> Node:
        """addExpr -> term ( ( '+' | '-' ) term )*."""
        return self.parse_binary_level(self.parse_term, ADD_OPS)

    def parse_term(self) -> Node:
        """term -> unary ( ( '*' | '/' | '%' ) unary )*."""
        return self.parse_binary_level(self.parse_unary, TERM_OPS)

    def parse_unary(self) -> Node:
        """unary -> ( '-' | '!' ) unary | primary.  Right recursive, so `!!a` and `- -a` work."""
        if self.at("-", "!"):
            op_token = self.advance()
            operand = self.parse_unary()
            return UnaryOp(op=op_token.lexeme, operand=operand,
                           line=op_token.line, col=op_token.col)
        return self.parse_primary()

    def parse_primary(self) -> Node:
        """primary -> literal | 'true' | 'false' | ID ( '(' args? ')' )? | '(' expr ')'."""
        token = self.peek()
        if token.type in LITERAL_TYPES:
            self.advance()
            return Literal(value=token.lexeme, type_name=LITERAL_TYPES[token.type],
                           line=token.line, col=token.col)
        if self.at("true", "false"):
            self.advance()
            return Literal(value=token.lexeme, type_name="bool",
                           line=token.line, col=token.col)
        if token.type == TokenType.IDENTIFIER:
            self.advance()
            if self.at("("):
                return self.parse_call_rest(token)
            return Identifier(name=token.lexeme, line=token.line, col=token.col)
        if self.at("("):
            self.advance()
            inner = self.parse_expr()
            self.expect(")")
            return inner   # parentheses only group; they leave no node (D-004)
        raise self.fail("expression")

    def parse_call_rest(self, name_token: Token) -> Call:
        """The `'(' args? ')'` part of primary and idStmt (the ID is already consumed)."""
        self.expect("(")
        args = [] if self.at(")") else self.parse_args()
        self.expect(")")
        return Call(name=name_token.lexeme, args=args,
                    line=name_token.line, col=name_token.col)


def parse(tokens: list[Token], errors: ErrorCollector) -> Program:
    """Parse a token list into a Program tree (interfaces.md: parser.py).

    Never raises. Reports Syntax errors through `errors` and returns whatever
    was parsed before the first error.
    """
    return Parser(tokens).parse_program(errors)
