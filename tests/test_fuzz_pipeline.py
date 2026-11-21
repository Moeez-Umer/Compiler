"""Full-pipeline fuzzing: random text and mutated valid programs (Phase 8, D-046).

Every case runs lexer, parser, semantic analyzer and TAC generator (TAC only when error-free).
Checked for each case: nothing escapes, nothing hangs (2 s per case), every error has a valid
kind and line >= 1, errors are sorted, and zero errors means TAC exists and is well-formed.
This is a robustness test, not an oracle: it cannot tell a wrong error message from a right one.
"""
import random
import signal
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

from src.errors import KIND_ORDER, ErrorCollector
from src.lexer import tokenize
from src.tokens import TokenType
from tests.pipeline_helper import check_tac, compile_source

SEED = 426
MUTANT_COUNT = 4000
RANDOM_TEXT_COUNT = 1500
CASE_SECONDS = 2.0
TOTAL_SECONDS = 120
TESTS = Path(__file__).parent

KINDS = ("delete", "duplicate", "swap", "operator", "type")
TYPES = ("int", "float", "char", "bool")
ALL_OPERATORS = ("+", "-", "*", "/", "%", "=", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!")
OPERATOR_GROUPS = (("+", "-", "*", "/", "%"), ("<", ">", "<=", ">="), ("==", "!="), ("&&", "||"))

# Minimums, chosen below the observed counts (see PROGRESS.md) so that the stages stay exercised.
MIN_BY_STAGE = {"lexical": 15, "syntax": 1500, "semantic": 600, "tac": 300}
MIN_PER_KIND = 700
MIN_SEMANTIC_FOR_OPERATOR_AND_TYPE = 250


class CaseTimeout(Exception):
    """One fuzz case ran longer than CASE_SECONDS."""


@contextmanager
def case_alarm(seconds: float):
    """Fail one case after `seconds` of CPU time (SIGVTALRM). A different timer than conftest's
    SIGALRM, so the per-test limit of D-026 stays in place around the whole loop."""
    def on_timer(signum, frame):
        raise CaseTimeout(f"no result within {seconds} s")

    old_handler = signal.signal(signal.SIGVTALRM, on_timer)
    signal.setitimer(signal.ITIMER_VIRTUAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_VIRTUAL, 0)
        signal.signal(signal.SIGVTALRM, old_handler)


# ------------------------------------------------------------------ the checks for one case

def invariant_problems(result) -> list[str]:
    """The properties every compilation must have, whatever the input."""
    problems = []
    for error in result.errors:
        if error.kind not in KIND_ORDER:
            problems.append(f"invalid kind {error.kind!r}")
        if error.line < 1:
            problems.append(f"line < 1: {error.format()}")
    keys = [(KIND_ORDER.index(e.kind), e.line, e.col) for e in result.errors if e.kind in KIND_ORDER]
    if keys != sorted(keys):
        problems.append("errors are not sorted by kind, line, col")
    if not result.errors:
        if result.tac is None:
            problems.append("zero errors but no TAC")
        else:
            problems += [f"bad TAC: {p}" for p in check_tac(result.tac)]
    return problems


def run_case(source: str):
    """Compile `source`; returns (result or None, problems). Prints the input if the alarm fires."""
    try:
        with case_alarm(CASE_SECONDS):
            result = compile_source(source)
    except CaseTimeout as exc:
        print(f"HANG ({exc}); input = {source!r}", file=sys.stderr)
        return None, [f"hang: {exc}"]
    except Exception as exc:                       # noqa: BLE001  (an escaping exception IS the bug)
        return None, [f"exception escaped: {type(exc).__name__}: {exc}"]
    return result, invariant_problems(result)


# ------------------------------------------------------------------ mutation at source offsets

def line_starts(source: str) -> list[int]:
    """Offset of the first character of every line (only `\\n` ends a line, as in the lexer)."""
    return [0] + [i + 1 for i, ch in enumerate(source) if ch == "\n"]


def token_spans(source: str, tokens) -> list[tuple]:
    """(start, end, token) of every non-EOF token, from the token's line and column.

    Mutations cut the ORIGINAL text at these offsets, so the layout (lines, indentation,
    comments) stays as written and error positions stay realistic.
    """
    starts = line_starts(source)
    spans = []
    for token in tokens:
        if token.type is TokenType.EOF or token.line > len(starts):
            continue
        start = starts[token.line - 1] + token.col - 1
        end = start + len(token.lexeme)
        if source[start:end] == token.lexeme:
            spans.append((start, end, token))
    return spans


def replacement_for(old: str, choices: tuple, groups, rng: random.Random) -> str:
    """A different operator or keyword; 70% of the time from the same group, so types still fit often."""
    group = next((g for g in groups if old in g), choices)
    pool = group if rng.random() < 0.7 else choices
    return rng.choice([c for c in pool if c != old] or [c for c in choices if c != old])


def replace_span(source: str, span: tuple, text: str) -> str:
    """Source with the token at `span` replaced by `text`."""
    return source[:span[0]] + text + source[span[1]:]


def mutate(source: str, spans: list, kind: str, rng: random.Random) -> str:
    """One mutation of `kind`: delete / duplicate / swap a token, change an operator or a type."""
    if kind == "operator":
        spans = [s for s in spans if s[2].type is TokenType.OPERATOR] or spans
    if kind == "type":
        spans = [s for s in spans if s[2].lexeme in TYPES] or spans
    if kind == "swap" and len(spans) > 1:
        i = rng.randrange(len(spans) - 1)
        (s1, e1, _), (s2, e2, _) = spans[i], spans[i + 1]
        return source[:s1] + source[s2:e2] + source[e1:s2] + source[s1:e1] + source[e2:]
    span = rng.choice(spans)
    lexeme = source[span[0]:span[1]]
    if kind == "operator" and span[2].type is TokenType.OPERATOR:
        return replace_span(source, span, replacement_for(lexeme, ALL_OPERATORS, OPERATOR_GROUPS, rng))
    if kind == "type" and lexeme in TYPES:
        return replace_span(source, span, replacement_for(lexeme, TYPES, (TYPES,), rng))
    if kind == "duplicate":
        return source[:span[1]] + " " + lexeme + source[span[1]:]
    return source[:span[0]] + source[span[1]:]


def valid_programs() -> dict[str, tuple]:
    """name -> (source, token spans) for every tests/valid and tests/golden program."""
    programs = {}
    for folder in ("valid", "golden"):
        for path in sorted((TESTS / folder).glob("*.sl")):
            source = path.read_bytes().decode("utf-8")
            programs[f"{folder}/{path.name}"] = (source, token_spans(source, tokenize(source, ErrorCollector())))
    return programs


def make_mutants(count: int, rng: random.Random) -> list[tuple]:
    """`count` (kind, program name, mutated source); the kinds rotate so each is equally common."""
    programs = valid_programs()
    names = sorted(name for name in programs if programs[name][1])   # skip comment-only files
    mutants = []
    for n in range(count):
        kind = KINDS[n % len(KINDS)]
        for _ in range(20):                        # a mutation that changes nothing is retried
            name = rng.choice(names)
            source, spans = programs[name]
            mutated = mutate(source, spans, kind, rng)
            if mutated != source:
                break
        mutants.append((kind, name, mutated))
    return mutants


# ------------------------------------------------------------------ random raw text

FRAGMENTS = ("int", "float", "char", "bool", "const", "if", "else", "for", "while", "return", "true",
             "false", "main", "x", "y_1", "f", "0", "42", "3.14", "3.4.5", "9abc", "'a'", "'\\n'", "'ab'",
             "'", "(", ")", "{", "}", ";", ",", "+", "-", "*", "/", "%", "=", "==", "!=", "<=", ">=",
             "&&", "||", "&", "|", "!", "//", "/*", "*/", "@", "#", "\\", ".", "é", "\ufeff", "\x00", "\r")
SEPARATORS = (" ", " ", "\n", "\t", "", "\r\n")


def random_text(rng: random.Random) -> str:
    """Either glued SmartLang fragments (mostly almost-valid) or arbitrary characters."""
    if rng.random() < 0.7:
        pieces = [rng.choice(FRAGMENTS) + rng.choice(SEPARATORS) for _ in range(rng.randrange(0, 60))]
        return "".join(pieces)
    return "".join(chr(rng.choice((rng.randrange(32, 127), rng.randrange(0, 0x3000), 10, 9, 13)))
                   for _ in range(rng.randrange(0, 200)))


# ------------------------------------------------------------------ tests

def test_check_tac_detects_each_kind_of_problem():
    """The TAC checker itself must fail on bad TAC, or the fuzzer's check would prove nothing."""
    good = ["func f:", "  t1 = a + 1", "  ifFalse t1 goto L1", "  return t1", "L1:", "  return 0", "endfunc"]
    assert check_tac(good) == []
    assert check_tac(good[:-1])                                              # no endfunc
    assert check_tac(["endfunc"])                                            # endfunc alone
    assert check_tac(["func f:", "func g:", "endfunc", "endfunc"])           # nested func
    assert check_tac(["func f:", "  goto L9", "endfunc"])                    # undefined target
    assert check_tac(["func f:", "L1:", "L1:", "  return 0", "endfunc"])     # label twice
    assert check_tac(["func f:", "  t2 = t1 + 1", "endfunc"])                # temp used before set
    assert check_tac(["func f:", "  t1 = call t9, 0", "endfunc"]) == []      # callee name is not a temp


def test_token_spans_cover_every_token_exactly():
    """Offsets from line/col must reproduce each lexeme for every valid program (CRLF files included)."""
    for name, (source, spans) in valid_programs().items():
        tokens = [t for t in tokenize(source, ErrorCollector()) if t.type is not TokenType.EOF]
        assert len(spans) == len(tokens), name


def test_mutation_keeps_the_layout_of_the_original():
    """A deleted token leaves every other line untouched (positions stay realistic)."""
    source = "int main() {\n    int a = 1;\n    return a;\n}\n"
    spans = token_spans(source, tokenize(source, ErrorCollector()))
    deleted = mutate(source, spans, "delete", random.Random(1))
    assert deleted.count("\n") == source.count("\n") and len(deleted) < len(source)


def test_case_alarm_fires_and_prints_the_input(monkeypatch, capsys):
    """A hang is reported as a problem and the offending input is printed (to stderr)."""
    def hang(source):
        while True:
            pass

    this = sys.modules[__name__]
    monkeypatch.setattr(this, "compile_source", hang)
    monkeypatch.setattr(this, "CASE_SECONDS", 0.2)
    result, problems = run_case("int spin;")
    assert result is None and problems and problems[0].startswith("hang")
    assert "int spin;" in capsys.readouterr().err


def test_an_escaping_exception_is_reported(monkeypatch):
    """An exception from a stage is a failing case, not a crash of the fuzzer."""
    monkeypatch.setattr(sys.modules[__name__], "compile_source", lambda source: 1 / 0)
    result, problems = run_case("x")
    assert result is None and "ZeroDivisionError" in problems[0]


def test_random_text_never_breaks_the_pipeline(capsys):
    """(a) Random raw text, fixed seed."""
    signal.alarm(TOTAL_SECONDS)
    rng = random.Random(SEED)
    stages: Counter = Counter()
    failures = []
    for _ in range(RANDOM_TEXT_COUNT):
        source = random_text(rng)
        result, problems = run_case(source)
        stages[result.stage if result else "failed"] += 1
        if problems:
            failures.append(f"{problems}\n  input = {source!r}")
    with capsys.disabled():
        print(f"\nrandom text: {RANDOM_TEXT_COUNT} cases, stopped at {dict(stages)}")
    assert not failures, f"{len(failures)} failing inputs:\n" + "\n".join(failures)


def test_mutants_never_break_the_pipeline_and_reach_every_stage(capsys):
    """(b) Mutated valid programs: robustness invariants plus minimum stage coverage."""
    signal.alarm(TOTAL_SECONDS)
    mutants = make_mutants(MUTANT_COUNT, random.Random(SEED))
    by_stage: Counter = Counter()
    by_kind_stage: Counter = Counter()
    failures = []
    for kind, name, source in mutants:
        result, problems = run_case(source)
        stage = result.stage if result else "failed"
        by_stage[stage] += 1
        by_kind_stage[(kind, stage)] += 1
        if problems:
            failures.append(f"[{kind} of {name}] {problems}\n  input = {source!r}")
    with capsys.disabled():
        print(f"\nmutants: {len(mutants)} cases, stopped at {dict(by_stage)}")
        for kind in KINDS:
            row = {s: by_kind_stage[(kind, s)] for s in ("lexical", "syntax", "semantic", "tac")}
            print(f"  {kind:<9} {sum(row.values()):>5}  {row}")
    assert not failures, f"{len(failures)} failing inputs:\n" + "\n".join(failures)
    assert len(mutants) >= 3000
    for stage, minimum in MIN_BY_STAGE.items():
        assert by_stage[stage] >= minimum, f"only {by_stage[stage]} mutants stopped at {stage}"
    for kind in KINDS:
        total = sum(by_kind_stage[(kind, s)] for s in ("lexical", "syntax", "semantic", "tac"))
        assert total >= MIN_PER_KIND, f"only {total} '{kind}' mutants"
    for kind in ("operator", "type"):
        reached = by_kind_stage[(kind, "semantic")] + by_kind_stage[(kind, "tac")]
        assert reached >= MIN_SEMANTIC_FOR_OPERATOR_AND_TYPE, f"'{kind}' mutants rarely reach semantic"
