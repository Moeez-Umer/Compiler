# SmartLang Compiler Front-End

Term project for CS426 Compiler Construction (Information Technology University).
It is the front-end of a compiler for **SmartLang**, a simplified imperative language: a lexical analyzer,
a recursive descent parser, a semantic analyzer and a three-address-code (TAC) generator.
Everything is hand-written Python 3.12. Only the standard library, `graphviz` and `pytest` are used.

Design documents live in `docs/`: `SPEC.md` (language and compiler rules), `interfaces.md` (module contracts),
`Decisions.md` (design choices), `Flow.md` (pipeline), `PROGRESS.md` (phase checklist).

## Setup (macOS)

```bash
brew install graphviz            # provides the `dot` binary (needed for parse-tree PNGs from Phase 2)
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python --version                 # should print Python 3.12.x
```

## Run the tests

From the repo root, with the virtual environment active:

```bash
pytest -v
```

(`python -m pytest -v` also works; `pytest.ini` sets `pythonpath = .` and `testpaths = tests`.)

## Usage

Command-line usage: coming in later phases.
