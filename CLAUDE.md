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
- **`engine.py`** — `GameEngine.execute_command` dispatches `click x y`, `wait <ms>`, and `print board`. A click with no selection selects a non-empty cell; a second click either switches selection (same color), moves/captures (valid move, enemy or empty target), or deselects (illegal move). **Moves take travel time** (movement over time): a valid move is not applied instantly — it becomes a `PendingMove` with `arrival_ms = game_clock_ms + cells_traveled * config.MS_PER_CELL` (cells = Chebyshev distance). The piece stays in its **origin** cell (so `print board` shows it there) until `wait` advances `game_clock_ms` to/past `arrival_ms`, at which point `_resolve_arrived_moves` performs the actual `board.move_piece` (including capture). Only `wait` resolves pending moves, so a move never completes without a sufficient `wait`. **The board is locked while any move is pending**: the first line of `_handle_click` returns immediately if `pending_moves` is non-empty, so clicks are ignored until the in-flight move arrives. This means only one move runs at a time (no concurrent moves, including opposite colors), and a moving piece cannot be redirected — the original route always completes. There is **no cooldown** — the instant a piece arrives its move leaves `pending_moves`, the lock lifts, and it can move again immediately (the spec's 5000 ms cooldown is not implemented yet). **Capturing a king ends the game**: when `_resolve_arrived_moves` lands a move on a cell holding a `King`, it sets `self.game_over`. Detection happens at capture-resolution (reading the destination before `move_piece`), not by scanning the board. Once `game_over` is set, `_handle_click` returns immediately, so all later moves are ignored; `wait`/`print board` still run.
- **`config.py`** — shared constants: `CELL_SIZE` (100), `MS_PER_CELL` (1000, travel time per cell), color strings `"WHITE"`/`"BLACK"`, `EMPTY_TOKEN`.
- **`main.py`** — `parse_input` + `main(input_stream=None)`; `input_stream` defaults to `sys.stdin` and is injectable for tests.

### Conventions that bite

- **Grid is `[row][col]`, but clicks are `(x, y)`.** In `engine._handle_click`, `row = y // CELL_SIZE` and `col = x // CELL_SIZE` — x maps to column, y maps to row. Getting this backwards is the most common source of confusion.
- **Colors are the full strings `"WHITE"`/`"BLACK"`** everywhere in logic; the single-char `w`/`b` exists only in tokens and `__str__` output.
- **Pawn direction is hardcoded**: white moves up (`row - 1`), black moves down (`row + 1`); pawns capture diagonally and cannot capture straight ahead.

## Project context

`kong_fu_chess_requirements.md` is the full product spec (Hebrew): Kung-Fu-Chess is meant to be a **real-time, no-turns** game where moves take physical travel time, pieces have a post-move cooldown, and you win only by actually capturing the enemy king (no check/checkmate). **The current code is an early, simplified move engine** — click-to-select/move with instant moves, no timing, cooldown, scoring, or networking yet. When extending, honor the spec's stated design principle: make the *known* future extensions (new piece types, new commands, animations) easy, but do **not** add speculative abstractions for things not yet needed. The registry-factory piece model is the concrete expression of that principle.

## Architecture Principles - Extensibility (must respect, do NOT implement yet)

1. **Future binary representation of board/pieces**: Currently represented as text, 
   but in the future a move to binary representation will be required to save memory.
   - Do NOT implement this now.
   - Mandatory: all access to the board/pieces must go through an abstraction layer 
     (interface/abstract class) — never touch the internal data structure directly.
   - When working on new code that touches the board/pieces, always ask: 
     "If the internal representation switches to binary tomorrow, will this code still work?"

2. **User-defined games (custom rules engine)**: In the future, users will define 
   custom movement rules for each piece (including non-standard behavior — 
   e.g. a pawn reversing direction instead of promoting).
   - Do NOT implement this now.
   - Mandatory: no hard-coding of movement rules inside game/piece logic. 
     Every movement rule must be swappable/externally definable 
     (strategy pattern / config-driven rules), not embedded if/else logic.
   - Before implementing movement logic for a piece, check: "Could this be 
     replaced with a completely different rule without touching this code?"

## Clean Code - mandatory for every PR

- **DRY**: each piece of logic is implemented in only one place. Before writing 
  new code, check if the logic already exists elsewhere.
- **SRP**: every function does exactly one thing. A function doing several 
  things should be split.
- **No magic numbers/strings**: no hard-coded constants/strings in business logic. 
  Everything belongs in a configuration file.
- **Encapsulation**: a class's internal data structure is never exposed to other 
  classes. One class must never "know" which key to pull from another class's 
  internal dict.
- Before finishing a feature, review the changes and ask: "Is there a code smell here?"
