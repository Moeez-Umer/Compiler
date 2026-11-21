"""Shared helper for the Phase 8 tests (D-044): run the stages directly, check EXPECT headers and TAC.

The stages are called one by one (tokenize, parse, analyze, generate), with the same policy as
`src/main.py` (SPEC section 9): semantic only without Lexical or Syntax errors, TAC only without errors.
"""
import re
from collections import Counter
from dataclasses import dataclass

from src.ast_nodes import Program
from src.errors import KIND_ORDER, CompilerError, ErrorCollector
from src.lexer import tokenize
from src.parser import parse
from src.semantic import analyze
from src.symbol_table import SymbolTable
from src.tacgen import generate
from src.tokens import Token

EXPECT_OK = "// EXPECT: OK"
EXPECT_PREFIX = "// EXPECT:"
EXPECT_RE = re.compile(r"^// EXPECT: (Lexical|Syntax|Semantic) (\d+) (.+)$")


@dataclass
class Result:
    """What the stages produced for one source text; a skipped stage leaves its field None."""

    tokens: list[Token]
    tree: Program
    errors: list[CompilerError]
    table: SymbolTable | None
    tac: list[str] | None

    @property
    def stage(self) -> str:
        """Where the compilation stopped: lexical, syntax, semantic, or tac (everything ran)."""
        kinds = {error.kind for error in self.errors}
        for kind in KIND_ORDER:
            if kind in kinds:
                return kind.lower()
        return "tac"


def compile_source(source: str) -> Result:
    """Run lexer, parser, semantic analyzer and TAC generator on `source` (same policy as main.py)."""
    collector = ErrorCollector()
    tokens = tokenize(source, collector)
    tree = parse(tokens, collector)
    table = None
    if not (collector.has_kind("Lexical") or collector.has_kind("Syntax")):
        table = analyze(tree, collector)
    tac = None
    if not collector.has_errors():
        tac = generate(tree)
    return Result(tokens, tree, collector.all(), table, tac)


# ------------------------------------------------------------------ EXPECT headers (SPEC section 13)

@dataclass(frozen=True)
class Expect:
    """One `// EXPECT: <Kind> <line> <substring>` line."""

    kind: str
    line: int
    text: str


def read_header(source: str) -> list[str]:
    """The leading run of `// EXPECT:` lines (trailing `\\r` removed)."""
    header = []
    for line in source.split("\n"):
        line = line.rstrip("\r")
        if not line.startswith(EXPECT_PREFIX):
            break
        header.append(line)
    return header


def header_problems(source: str, folder: str) -> list[str]:
    """Why the header is wrong for `folder` ('valid', 'golden' or 'invalid'); empty list when fine."""
    header = read_header(source)
    if folder in ("valid", "golden"):
        if header != [EXPECT_OK]:
            return [f"first line must be '{EXPECT_OK}', header is {header!r}"]
        return []
    if not header:
        return ["no '// EXPECT: <Kind> <line> <message>' line at the top"]
    return [f"malformed EXPECT line: {line!r}" for line in header if not EXPECT_RE.match(line)]


def parse_expects(source: str) -> list[Expect]:
    """The well-formed EXPECT lines of an invalid file, in file order."""
    expects = []
    for line in read_header(source):
        match = EXPECT_RE.match(line)
        if match:
            expects.append(Expect(match.group(1), int(match.group(2)), match.group(3)))
    return expects


def fits(expect: Expect, error: CompilerError) -> bool:
    """True if `error` is the one `expect` describes (kind, line, message substring)."""
    return (expect.kind == error.kind and expect.line == error.line
            and expect.text in error.message)


def match_errors(expects: list[Expect], errors: list[CompilerError]
                 ) -> tuple[list[Expect], list[CompilerError]]:
    """One-to-one matching of EXPECT lines to errors (augmenting paths, so the order of the
    lines cannot cause a false mismatch). Returns (unmatched expects, unexpected errors)."""
    owner: dict[int, int] = {}                     # error index -> expect index

    def assign(e_index: int, seen: set[int]) -> bool:
        for i, error in enumerate(errors):
            if i in seen or not fits(expects[e_index], error):
                continue
            seen.add(i)
            if i not in owner or assign(owner[i], seen):
                owner[i] = e_index
                return True
        return False

    matched = {e for e in range(len(expects)) if assign(e, set())}
    missing = [expects[e] for e in range(len(expects)) if e not in matched]
    extra = [errors[i] for i in range(len(errors)) if i not in owner]
    return missing, extra


def expectation_problems(source: str, result: Result) -> list[str]:
    """Each EXPECT line matched by one error, and no unexpected extra errors."""
    missing, extra = match_errors(parse_expects(source), result.errors)
    problems = [f"expected but not reported: {e.kind} {e.line} '{e.text}'" for e in missing]
    problems += [f"unexpected error: {error.format()}" for error in extra]
    return problems


# ------------------------------------------------------------------ TAC well-formedness

LABEL_DEF = re.compile(r"^(L\d+):$")
GOTO_TARGET = re.compile(r"\bgoto (L\d+)$")
FUNC_HEADER = re.compile(r"^func \w+:$")
TEMP_NAME = re.compile(r"\bt\d+\b")
CALLEE = re.compile(r"\bcall \w+")


def temp_problems(text: str, assigned: set[str], number: int) -> list[str]:
    """Check one instruction: every temporary it reads must already be assigned; record its target."""
    lhs, sep, rhs = text.partition(" = ")
    if not sep:
        lhs, rhs = "", text
    rhs = CALLEE.sub("call", rhs)                  # a function may be named like a temporary
    problems = [f"line {number}: temporary {t} used before assignment"
                for t in TEMP_NAME.findall(rhs) if t not in assigned]
    if TEMP_NAME.fullmatch(lhs):
        assigned.add(lhs)
    return problems


def check_tac(lines: list[str]) -> list[str]:
    """Well-formedness: labels defined once and every goto target defined, func/endfunc balanced,
    every temporary assigned before it is used. Returns the problems (empty when well-formed)."""
    problems: list[str] = []
    defined: Counter[str] = Counter()
    targets: list[str] = []
    assigned: set[str] = set()
    depth = 0
    for number, line in enumerate(lines, start=1):
        label = LABEL_DEF.match(line)
        if label:
            defined[label.group(1)] += 1
        elif FUNC_HEADER.match(line):
            if depth:
                problems.append(f"line {number}: func inside func")
            depth += 1
        elif line == "endfunc":
            if not depth:
                problems.append(f"line {number}: endfunc without func")
            depth = max(0, depth - 1)
        elif line != "globals:":
            text = line.strip()
            goto = GOTO_TARGET.search(text)
            if goto:
                targets.append(goto.group(1))
                text = text[:goto.start()]
            problems += temp_problems(text, assigned, number)
    if depth:
        problems.append("func without endfunc at the end")
    problems += [f"label {name} defined {count} times" for name, count in defined.items() if count > 1]
    problems += [f"goto {name}: label never defined" for name in sorted(set(targets)) if name not in defined]
    return problems
