# Kong-Fu-Chess ♟️

A command-driven chess engine in Python. You supply a starting board and a list of commands (clicks, waits, prints); the engine processes them and updates the board state.

> **Note:** This is an early, simplified implementation. The full product vision (a **real-time**, no-turns game with move travel time, cooldowns, and scoring) is described in [kong_fu_chess_requirements.md](kong_fu_chess_requirements.md). The current code is an instant-move engine only.

## Installation

```bash
pip install -r requirements-dev.txt   # dev + test dependencies (pytest, pytest-cov)
```

## Running

The game reads a single text document from stdin containing a starting board and a list of commands:

```bash
python main.py < input.txt
```

### Input format

```
Board:
wK . bK
. . .
Commands:
click 50 50
click 150 50
print board
```

- Both the `Board:` and `Commands:` sections are **required**.
- All board rows must have the same width.
- Each cell is either `.` (empty) or `<color><piece>`, where color is `w`/`b` and piece is one of `K R B Q N P`.

### Supported commands

| Command | Meaning |
|---------|---------|
| `click x y` | Click on pixel `(x, y)` — selects a piece, moves, captures, or clears the selection |
| `wait <ms>` | Advances the game clock by milliseconds |
| `print board` | Prints the current board state |

> **Heads up:** Click coordinates are `(x, y)` in pixels, while the board is indexed `[row][col]`. The conversion is `row = y // CELL_SIZE`, `col = x // CELL_SIZE` (cell size = 100).

## Code structure

| File | Responsibility |
|------|----------------|
| [pieces.py](pieces.py) | `Piece` base class plus one subclass per piece type; each defines `is_valid_move`. `EmptyCell` is a Null Object |
| [registry.py](registry.py) | Factory that turns an input token into a piece object — the **extension point** for adding new pieces |
| [board.py](board.py) | `Board` — holds the grid and provides bounds-safe cell access |
| [engine.py](engine.py) | `GameEngine` — parses and runs commands against the board |
| [main.py](main.py) | Input parsing (`parse_input`) and entry point (`main`) |
| [config.py](config.py) | Shared constants (`CELL_SIZE`, color names, empty token) |

## Tests

The test suite lives in [tests/](tests/), split by module:

```bash
pytest                                      # run all tests
pytest --cov=. --cov-report=term-missing    # with a coverage report
pytest tests/test_engine.py                 # a single file
pytest -k pawn                              # by expression
```

`pytest.ini` sets `testpaths = tests`, so running `pytest` collects only `tests/`. The legacy `test_game.py` is kept for reference and is not collected by default (run it explicitly with `pytest test_game.py`).
