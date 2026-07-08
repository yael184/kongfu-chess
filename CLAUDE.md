# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements-dev.txt        # test deps (pytest, pytest-cov)
pytest                                      # run the split suite in tests/ (see pytest.ini)
pytest --cov=. --cov-report=term-missing    # run with coverage report
pytest tests/test_engine.py                 # run one file
pytest tests/test_engine.py::test_capture_enemy_piece   # run one test
pytest -k pawn                              # run tests matching an expression
pytest test_game.py                         # run the legacy monolithic suite (NOT collected by default)
```

`pytest.ini` sets `testpaths = tests` and `pythonpath = .`. Because of `testpaths`, a plain `pytest` run collects **only** `tests/` — the root-level `test_game.py` (the original monolithic suite, kept for reference) is excluded from default runs and must be named explicitly. `pythonpath = .` puts the repo root on `sys.path` so tests can `from board import Board` etc.

Run the game itself by feeding a board+commands document to `main.py` on stdin:

```bash
python main.py < input.txt
```

## Input format (main.parse_input)

`main.py` parses a single text document with two labeled sections. Both `Board:` and `Commands:` markers are required or it prints `ERROR ...` and calls `sys.exit(0)`:

```
Board:
wK . bK
. . .
Commands:
click 50 50
click 150 50
print board
```

Board rows must all be the same width (else `ERROR ROW_WIDTH_MISMATCH`). Each token is either `.` (empty) or a two-char `<color><symbol>` where color is `w`/`b` and symbol is one of `K R B Q N P` (unknown token → `ERROR UNKNOWN_TOKEN`).

## Architecture

Small, layered engine. Data flows: raw text → `Board` + command list → `GameEngine` mutates `Board`.

- **`pieces.py`** — `Piece` base class plus one subclass per piece type. The only per-piece logic is `is_valid_move(from_row, from_col, to_row, to_col, board)`, which encodes *shape* rules only; sliding pieces (Rook/Bishop/Queen) call the shared `_is_path_clear` helper to reject blocked paths. `EmptyCell` is a `Piece` subclass (Null Object) so the grid is never `None` and callers never special-case empties.
- **`registry.py`** — `create_piece_from_token` is a factory mapping a token to a piece instance via the `PIECE_CLASSES` dict. **This is the extension point for new piece types** (per the spec's "easy to add a piece" design goal): add the class in `pieces.py` and one entry here — no changes to parsing or the engine.
- **`board.py`** — `Board` owns the `grid` (list-of-lists of `Piece`) and `selected_piece`. All access goes through `get_cell`/`is_empty`/`get_piece_color`, which are bounds-safe (out-of-bounds reads return an `EmptyCell`, not an error).
- **`engine.py`** — `GameEngine.execute_command` dispatches `click x y`, `wait <ms>`, and `print board`. A click with no selection selects a non-empty cell; a second click either switches selection (same color), moves/captures (valid move, enemy or empty target), or deselects (illegal move).
- **`config.py`** — shared constants: `CELL_SIZE` (100), color strings `"WHITE"`/`"BLACK"`, `EMPTY_TOKEN`.
- **`main.py`** — `parse_input` + `main(input_stream=None)`; `input_stream` defaults to `sys.stdin` and is injectable for tests.

### Conventions that bite

- **Grid is `[row][col]`, but clicks are `(x, y)`.** In `engine._handle_click`, `row = y // CELL_SIZE` and `col = x // CELL_SIZE` — x maps to column, y maps to row. Getting this backwards is the most common source of confusion.
- **Colors are the full strings `"WHITE"`/`"BLACK"`** everywhere in logic; the single-char `w`/`b` exists only in tokens and `__str__` output.
- **Pawn direction is hardcoded**: white moves up (`row - 1`), black moves down (`row + 1`); pawns capture diagonally and cannot capture straight ahead.

## Project context

`kong_fu_chess_requirements.md` is the full product spec (Hebrew): Kung-Fu-Chess is meant to be a **real-time, no-turns** game where moves take physical travel time, pieces have a post-move cooldown, and you win only by actually capturing the enemy king (no check/checkmate). **The current code is an early, simplified move engine** — click-to-select/move with instant moves, no timing, cooldown, scoring, or networking yet. When extending, honor the spec's stated design principle: make the *known* future extensions (new piece types, new commands, animations) easy, but do **not** add speculative abstractions for things not yet needed. The registry-factory piece model is the concrete expression of that principle.
