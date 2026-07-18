# Kong-Fu-Chess ♟️

A command-driven chess engine in Python. You supply a starting board and a list of commands (clicks, waits, prints); the engine processes them and updates the board state.

> **Note:** This is a layered, simplified implementation. The full product vision (a **real-time**, no-turns game with move travel time, cooldowns, and scoring) is described in [kong_fu_chess_requirements.md](kong_fu_chess_requirements.md). Moves take **travel time** (a piece is shown at its origin until it has traveled far enough); jump/dodge, pawn two-step and promotion are implemented, there is a **real-time OpenCV GUI** with gliding pieces, and you win by capturing the enemy king — but post-move cooldowns, scoring, and networking are not implemented yet.

## Installation

```bash
pip install -r requirements-dev.txt   # dev + test dependencies (pytest, pytest-cov)
```

## Running

The game reads a single text document from stdin containing a starting board and a list of commands:

```bash
python -m kongfuchess.main < input.txt
```

### Graphical (OpenCV) surface

There is also a real-time graphical surface. It shares the whole engine with the text one — only the way time enters (a real clock instead of `wait`) and the way state leaves (sprites instead of text) differ:

```bash
pip install opencv-python
python -m kongfuchess.gui                 # loads the standard starting position
python -m kongfuchess.gui my_board.txt    # or a board grid of your own
```

**Left-click** selects a piece and then a destination (a second click on your own piece switches the selection); **right-click** makes a piece jump in place (a dodge). Moves are **parallel** — many pieces travel at once — and each piece **rests** after acting (a long rest after a move, a short rest after a jump). Pieces **glide** between cells over their travel time. The **window is resizable** (clicks are scaled back to the right square), and it closes on <kbd>Esc</kbd>. The art lives under `kongfuchess/assets/` and is entirely config-driven (`[assets]` in [config.toml](kongfuchess/config.toml)) — re-skinning changes files, not code.

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
- Each cell is either `.` (empty) or `<color><piece>`, where color is `w`/`b` and the piece letter is one the configured pieces declare — `K R B Q N P` as shipped (see [Adding a piece](#adding-a-piece)).

### Supported commands

| Command | Meaning |
|---------|---------|
| `click x y` | Click on pixel `(x, y)` — selects a piece, switches selection, starts a move/capture, or clears the selection |
| `jump x y` | The piece on cell `(x, y)` jumps in place (a dodge) — see below |
| `wait <ms>` | Advances the game clock by milliseconds, completing any move that has finished traveling |
| `print board` | Prints the current board state |

> **Moves take time:** a move does not apply instantly. It takes `cells_traveled × MS_PER_CELL` (1000 ms per cell; a diagonal square counts as one cell) to arrive; the piece stays on its origin cell until a `wait` advances the clock past its arrival time. A move never completes without a sufficient `wait`. **While a move is in progress a second move is rejected** — only one piece moves at a time. There is **no cooldown**: as soon as a piece arrives it can move again. **Capturing the enemy king ends the game** — once a move lands on a king, the game is over and all later moves are ignored (`print board` still works).

> **Jump / dodge:** `jump x y` makes the piece on that cell jump in place for `JUMP_DURATION_MS` (1000 ms) without leaving its cell — it does not lock the board. While airborne it is protected: if an enemy finishes moving onto its cell *during* the jump, the jumper captures the attacker (attacker removed, jumper stays); if the jump ends first, the attacker captures normally. A piece already moving, or an empty cell, cannot jump.

> **Pawns:** move one step forward into an empty cell, or a **two-step first move** from the start rank; capture one diagonal step forward; a pawn reaching the last rank **promotes to a queen** on arrival — or to whatever `promotes_to` names in [config.toml](config.toml). (No en passant.)

> **Heads up:** Click coordinates are `(x, y)` in pixels, while the board is indexed by `(row, col)`. The conversion is `row = y // CELL_SIZE`, `col = x // CELL_SIZE` (cell size = 100).

## Code structure

The engine is layered, and every collaborator is **injected** — no class builds its own
dependencies, and only [composition/app_factory.py](composition/app_factory.py) knows more than one
layer. Each kind of change therefore has exactly one home.

All source lives in the [kongfuchess/](kongfuchess/) package (separated from `.venv`, tests, and other project files at the root).

| Layer | Responsibility |
|------|----------------|
| [model/](kongfuchess/model/) | Domain core: `Position`, `Piece` (`PieceKind` is an open value object, not an enum), the `BoardView`/`MutableBoard` ports, `Board`, `GameState`, and the `Effect`/`ArrivalContext` vocabulary the layers above talk in |
| [rules/](kongfuchess/rules/) | **The only layer that knows what chess is.** `PieceRule` strategies (`SlidingRule`, `LeapingRule`, `PawnRule`, …) built from config by `rule_factory.py`; `ChessRuleSet` answers "is this legal?" and "what does this arrival do?" — always as data, never by mutating |
| [realtime/](kongfuchess/realtime/) | `Motion` and `RealTimeArbiter` — movement over time, and **no chess at all**: it asks the injected rule set what an arrival means and applies the effects it gets back |
| [engine/game_engine.py](kongfuchess/engine/game_engine.py) | `GameEngine` — the public command boundary (`request_move`, `request_jump`, `wait`, `snapshot`, `active_motions`) |
| [input/](kongfuchess/input/) | `BoardMapper` (pixels → cells) and `Controller` (click selection → `request_move`) |
| [text_io/](kongfuchess/text_io/) | `TokenCodec` (the token format, symbols injected from config), `PieceFactory` (stable ids), `BoardParser`, `BoardPrinter` |
| [texttests/](kongfuchess/texttests/) | `ScriptParser` (document → board + commands) and `ScriptRunner` (dispatches through an injected command table) |
| [view/](kongfuchess/view/) | The **OpenCV surface** (State/Strategy/DI per `final_plan.md`): `sprites/` (`SpriteState`/`AnimatedSprite`/`SpriteLibrary`), `rendering/` (a `BoardView` coordinator over `BoardRenderer`/`PieceRenderer`/`OverlayRenderer`, plus a resizable `Cv2Renderer`), and the real-time `GameLoop`. Holds no chess and no timing; reads the engine snapshot and drives the injected `Controller` |
| [composition/](kongfuchess/composition/) | The composition root — builds and wires everything (text **and** GUI) from a `GameConfig`. The swap point for a different rule set, time model, board or surface |
| [main.py](kongfuchess/main.py) / [gui.py](kongfuchess/gui.py) | The two entry points: a document from stdin (text), or a board file + OpenCV window (GUI) |
| [config.py](kongfuchess/config.py) / [config.toml](kongfuchess/config.toml) | Tunables, **the pieces themselves**, and the GUI `[assets]`, loaded from an external file |

## Configuration

Game constants live in [config.toml](config.toml), not in code — including **the pieces**. Edit the
file and run again; no code changes needed.

```toml
[timing]
ms_per_cell = 1000       # milliseconds to cross one cell
jump_duration_ms = 1000  # how long a jump protects a piece
```

### Adding a piece

A piece is a `[[pieces]]` block: what it is called, the letter it is spelled with, how it moves, and
whether taking it wins the game. Adding one is **configuration only — no code anywhere**:

```toml
[[pieces]]
name = "archbishop"
symbol = "A"
movement = "combined"                                    # bishop + knight
directions = [[1, 1], [1, -1], [-1, 1], [-1, -1]]
offsets = [[2, 1], [2, -1], [-2, 1], [-2, -1], [1, 2], [1, -2], [-1, 2], [-1, -2]]
```

Available movement patterns: `slide` (travels along `directions` until blocked), `leap` (jumps to
fixed `offsets`), `combined` (both), and `pawn`. Optional keys: `promotes_to = "<name>"` and
`victory_on_capture = true`. Only a movement pattern that does not exist yet needs code — one
`PieceRule` subclass plus one entry in [rules/rule_factory.py](rules/rule_factory.py), and nothing
outside `rules/`. See [tests/integration/test_custom_game.py](tests/integration/test_custom_game.py)
for whole games (an invented piece, a different promotion, a different victory condition) defined
purely in config.

[config.py](config.py) reads the file via the standard-library `tomllib` and returns an immutable
`GameConfig`, which the composition root injects wherever it is needed — the values are never
module-level globals for a layer to reach into.

## Tests

The suite lives in [tests/](tests/): `tests/unit/` (per-layer) and `tests/integration/` (end-to-end).
[tests/test_layer_boundaries.py](tests/test_layer_boundaries.py) parses every module's imports and
fails the build if a layer reaches across a boundary it is not allowed to — so the decoupling is an
enforced invariant, not a good intention.

```bash
pytest                                      # run all tests
pytest --cov=. --cov-report=term-missing    # coverage in the terminal
pytest --cov=. --cov-report=html            # coverage as a report in htmlcov/index.html
pytest tests/unit/test_rule_engine.py       # a single file
pytest -k pawn                              # by expression
```
