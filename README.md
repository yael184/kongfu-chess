# Kong-Fu-Chess ♟️

A command-driven chess engine in Python. You supply a starting board and a list of commands (clicks, waits, prints); the engine processes them and updates the board state.

> **Note:** This is a layered, simplified implementation. The full product vision (a **real-time**, no-turns game with move travel time, cooldowns, and scoring) is described in [kong_fu_chess_requirements.md](kong_fu_chess_requirements.md). Moves take **travel time** (a piece is shown at its origin until it has traveled far enough); jump/dodge, pawn two-step and promotion are implemented, and you win by capturing the enemy king — but post-move cooldowns, scoring, and networking are not implemented yet.

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
| `click x y` | Click on pixel `(x, y)` — selects a piece, switches selection, starts a move/capture, or clears the selection |
| `jump x y` | The piece on cell `(x, y)` jumps in place (a dodge) — see below |
| `wait <ms>` | Advances the game clock by milliseconds, completing any move that has finished traveling |
| `print board` | Prints the current board state |

> **Moves take time:** a move does not apply instantly. It takes `cells_traveled × MS_PER_CELL` (1000 ms per cell; a diagonal square counts as one cell) to arrive; the piece stays on its origin cell until a `wait` advances the clock past its arrival time. A move never completes without a sufficient `wait`. **While a move is in progress a second move is rejected** — only one piece moves at a time. There is **no cooldown**: as soon as a piece arrives it can move again. **Capturing the enemy king ends the game** — once a move lands on a king, the game is over and all later moves are ignored (`print board` still works).

> **Jump / dodge:** `jump x y` makes the piece on that cell jump in place for `JUMP_DURATION_MS` (1000 ms) without leaving its cell — it does not lock the board. While airborne it is protected: if an enemy finishes moving onto its cell *during* the jump, the jumper captures the attacker (attacker removed, jumper stays); if the jump ends first, the attacker captures normally. A piece already moving, or an empty cell, cannot jump.

> **Pawns:** move one step forward into an empty cell, or a **two-step first move** from the start rank; capture one diagonal step forward; a pawn reaching the last rank **promotes to a queen** on arrival. (No en passant.)

> **Heads up:** Click coordinates are `(x, y)` in pixels, while the board is indexed by `(row, col)`. The conversion is `row = y // CELL_SIZE`, `col = x // CELL_SIZE` (cell size = 100).

## Code structure

The engine is layered; dependencies point inward toward `model/`.

| Layer | Responsibility |
|------|----------------|
| [model/](model/) | Domain core: `Position` (value object), `Piece` (entity + `Color`/`PieceKind`/`PieceState` enums), `Board` (occupancy, bounds, `move_piece`), `GameState` |
| [rules/](rules/) | `piece_rules.py` (per-kind `legal_destinations` + `promotion_kind`, the **extension point** for new pieces) and `RuleEngine` (read-only move validation) |
| [realtime/](realtime/) | `Motion` and `RealTimeArbiter` — movement over time; the board changes only on arrival |
| [engine/game_engine.py](engine/game_engine.py) | `GameEngine` — the public command boundary (`request_move`, `wait`, `snapshot`) |
| [input/](input/) | `BoardMapper` (pixels → cells) and `Controller` (click selection → `request_move`) |
| [text_io/](text_io/) | `PieceFactory` (+ token codec), `BoardParser` (text → board), `BoardPrinter` (board/snapshot → text) |
| [texttests/](texttests/) | `ScriptParser` (document → board + commands) and `ScriptRunner` (dispatch commands) |
| [main.py](main.py) | Wires the stack and runs a document from stdin |
| [config.py](config.py) / [config.toml](config.toml) | Tunables (`cell_size`, `ms_per_cell`, empty token) loaded from an external file |

## Configuration

Game constants live in [config.toml](config.toml), not in code. Edit the file to change the
cell size, travel time per cell, or the empty-cell token, then run again — no code changes needed:

```toml
[timing]
ms_per_cell = 1000       # milliseconds to cross one cell
jump_duration_ms = 1000  # how long a jump protects a piece
```

[config.py](config.py) reads this file on import (via the standard-library `tomllib`) and exposes
the values as `config.CELL_SIZE`, `config.MS_PER_CELL`, `config.JUMP_DURATION_MS`,
`config.EMPTY_TOKEN`. Call `config.load()` to re-read the file at runtime after editing it.

## Tests

The suite lives in [tests/](tests/): `tests/unit/` (per-layer) and `tests/integration/` (end-to-end).

```bash
pytest                                      # run all tests
pytest --cov=. --cov-report=term-missing    # with a coverage report
pytest tests/unit/test_rule_engine.py       # a single file
pytest -k pawn                              # by expression
```
