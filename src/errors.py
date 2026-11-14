"""Error reporting shared by every compiler stage (SPEC section 9, interfaces.md: errors.py)."""
from dataclasses import dataclass

# Order in which error kinds are listed (SPEC section 9, "Output order").
KIND_ORDER = ("Lexical", "Syntax", "Semantic")


@dataclass(frozen=True)
class CompilerError:
    """One reported error. kind is "Lexical", "Syntax" or "Semantic"."""

    kind: str
    line: int
    col: int
    message: str

    def format(self) -> str:
        """Return the exact SPEC section 9 text, e.g. "[Lexical Error] Line 5, Col 12: msg"."""
        return f"[{self.kind} Error] Line {self.line}, Col {self.col}: {self.message}"


class ErrorCollector:
    """Collects errors from all stages so the compiler can report many per run (SPEC section 9)."""

    def __init__(self) -> None:
        """Start with no errors."""
        self._errors: list[CompilerError] = []

    def report(self, kind: str, line: int, col: int, message: str) -> None:
        """Record one error. An unknown kind raises ValueError so typos cannot hide errors (D-009)."""
        if kind not in KIND_ORDER:
            raise ValueError(f"Unknown error kind: {kind!r}")
        self._errors.append(CompilerError(kind, line, col, message))

    def has_errors(self) -> bool:
        """True if any error of any kind was reported."""
        return len(self._errors) > 0

    def has_kind(self, kind: str) -> bool:
        """True if at least one error of this kind was reported (used by the pipeline policy, D-006)."""
        return any(e.kind == kind for e in self._errors)

    def all(self) -> list[CompilerError]:
        """Return a copy grouped Lexical, Syntax, Semantic, each sorted by line then col.

        sorted() is stable, so errors at the same position keep their report order.
        """
        return sorted(
            self._errors,
            key=lambda e: (KIND_ORDER.index(e.kind), e.line, e.col),
        )
