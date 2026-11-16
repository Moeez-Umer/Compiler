"""Lexical scope stack and symbol table with full scope history (SPEC sections 8 and 10, interfaces.md: symbol_table.py)."""
from dataclasses import dataclass, field


@dataclass
class Symbol:
    """One declared identifier in a scope (SPEC sections 8 and 10, interfaces.md: symbol_table.py).

    `type_name` is `int`, `float`, `char`, or `bool` (for `"func"`, the return type).
    `kind` is `"var"`, `"const"`, `"param"`, or `"func"`.
    `params` lists `(type_name, param_name)` pairs for functions, or `None` for non-functions.
    `tac_name` is assigned by the semantic analyzer to give shadowed variables unique TAC names.
    """

    name: str
    type_name: str
    kind: str
    scope_level: int
    line: int
    params: list[tuple[str, str]] | None = None
    tac_name: str = ""


@dataclass
class _Scope:
    """One lexical scope record kept both while active and in the permanent scope history."""

    scope_id: int
    label: str
    level: int
    symbols: dict[str, Symbol] = field(default_factory=dict)


def _format_params(symbol: Symbol) -> str:
    """Format a function's parameter list for `dump()`, or `-` for non-function symbols."""
    if symbol.params is None:
        return "-"
    inside = ", ".join(f"{param_type} {param_name}" for param_type, param_name in symbol.params)
    return f"({inside})"


def _format_scope(scope: _Scope) -> str:
    """Render one scope header (`Scope k (label)`) and its aligned symbol table for `dump()`."""
    header_line = f"Scope {scope.scope_id} ({scope.label})" if scope.label else f"Scope {scope.scope_id}"
    if not scope.symbols:
        return f"{header_line}\n  (empty)"

    col_headers = ("NAME", "TYPE", "KIND", "LEVEL", "LINE", "PARAMS")
    rows = [
        (
            sym.name,
            sym.type_name,
            sym.kind,
            str(sym.scope_level),
            str(sym.line),
            _format_params(sym),
        )
        for sym in scope.symbols.values()
    ]
    widths = [max(len(row[i]) for row in [col_headers, *rows]) for i in range(6)]

    lines = [header_line]
    for row in [col_headers, *rows]:
        lines.append(
            f"  {row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}  {row[2]:<{widths[2]}}  "
            f"{row[3]:>{widths[3]}}  {row[4]:>{widths[4]}}  {row[5]}"
        )
    return "\n".join(lines)


class SymbolTable:
    """Nested symbol table that retains exited scopes for `dump()` (SPEC sections 8 and 10).

    `_active` holds currently open scopes from outermost (`global`, level 0) to innermost.
    `_all_scopes` records every scope ever entered in creation order so `dump()` can print
    all scopes even after function and block scopes have been exited.
    """

    def __init__(self) -> None:
        """Start with no active scopes and an empty scope history."""
        self._active: list[_Scope] = []
        self._all_scopes: list[_Scope] = []

    def enter_scope(self, label: str) -> int:
        """Open a new inner scope labelled `label` and return its sequential `scope_id`."""
        scope_id = len(self._all_scopes)
        level = len(self._active)
        scope = _Scope(scope_id=scope_id, label=label, level=level)
        self._all_scopes.append(scope)
        self._active.append(scope)
        return scope_id

    def exit_scope(self) -> None:
        """Close the current innermost scope while keeping it in `_all_scopes` for `dump()`."""
        if not self._active:
            raise RuntimeError("Cannot exit_scope: no active scope")
        self._active.pop()

    def declare(self, symbol: Symbol) -> bool:
        """Declare `symbol` in the current scope (SPEC section 8: same-scope redeclaration rule).

        Returns `False` and leaves the existing entry untouched if `symbol.name` is already
        declared in the current scope; otherwise sets `symbol.scope_level` to the current
        scope's level (so the stored level never disagrees with its scope), stores `symbol`,
        and returns `True` (including when shadowing an outer scope).
        """
        if not self._active:
            raise RuntimeError("Cannot declare symbol: no active scope")
        current_scope = self._active[-1]
        if symbol.name in current_scope.symbols:
            return False
        symbol.scope_level = current_scope.level
        current_scope.symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Symbol | None:
        """Find `name` by walking active scopes from innermost outward (SPEC section 8)."""
        for scope in reversed(self._active):
            if name in scope.symbols:
                return scope.symbols[name]
        return None

    def lookup_current(self, name: str) -> Symbol | None:
        """Find `name` only in the current innermost active scope, ignoring outer scopes."""
        if not self._active:
            return None
        return self._active[-1].symbols.get(name)

    def current_level(self) -> int:
        """Return the nesting level of the current scope (`0` for global, `-1` if none active)."""
        return len(self._active) - 1

    def dump(self) -> str:
        """Format every scope ever created (active or exited) in creation order (SPEC section 10)."""
        return "\n\n".join(_format_scope(scope) for scope in self._all_scopes)
