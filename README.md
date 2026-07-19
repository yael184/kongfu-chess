# Kong-Fu-Chess ♟️

A **real-time, no-turns** chess engine in Python, with both a text surface and an OpenCV GUI.
There are no turns: any idle piece can be commanded at any moment, moves take physical **travel
time**, pieces **rest** after acting, and pieces that meet in flight resolve through a real
**collision model**. You win by actually capturing the enemy king — there is no check or checkmate.

> **Status:** the product vision is described in [kong_fu_chess_requirements.md](kong_fu_chess_requirements.md),
> and the GUI architecture follows [final_plan.md](final_plan.md). Implemented: parallel real-time
> moves, post-move/post-jump cooldown, the collision model, jump/dodge, pawn two-step, promotion,
> a configurable victory condition, the OpenCV GUI (gliding pieces, animations, resizable window)
> and a side panel with player names, live score and a moves log. **Not** implemented: networking.

## Installation

```bash
pip install -r requirements-dev.txt   # dev + test dependencies (pytest, pytest-cov)
pip install opencv-python             # only needed for the GUI
```

## Running

### Graphical (OpenCV) surface

```bash
python -m kongfuchess.gui                 # loads the standard starting position
python -m kongfuchess.gui my_board.txt    # or a board grid of your own
```

- **Left-click** selects a piece, then a destination. A second click on your own piece switches the
  selection; a click outside the board cancels it.
- **Right-click** makes a piece jump in place (a dodge).
- Moves are **parallel** — many pieces travel at once — and each piece **rests** after acting, so it
  cannot be commanded again until it settles.
- Pieces **glide** between cells over their travel time and animate per state
  (idle / move / jump / short rest / long rest).
- A **side panel** shows player names, a live score and the moves log.
- The **window is resizable** — clicks are scaled back to the right square. <kbd>Esc</kbd> closes it.

The art lives under `kongfuchess/assets/` and is entirely config-driven
(`[assets]` in [config.toml](kongfuchess/config.toml)) — re-skinning changes files, not code.

### Text surface

The text surface reads a single document from stdin containing a starting board and a command list.
It shares the whole engine with the GUI; only the way time enters (a `wait` command instead of a real
clock) and the way state leaves (text instead of sprites) differ:

```bash
python -m kongfuchess.main < input.txt
```

#### Input format

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
- Each cell is either `.` (empty) or `<color><piece>`, where color is `w`/`b` and the piece letter is
  one the configured pieces declare — `K R B Q N P` as shipped (see [Adding a piece](#adding-a-piece)).

#### Supported commands

| Command | Meaning |
|---------|---------|
| `click x y` | Click on pixel `(x, y)` — selects a piece, switches selection, starts a move/capture, or clears the selection |
| `jump x y` | The piece on cell `(x, y)` jumps in place (a dodge) |
| `wait <ms>` | Advances the game clock by milliseconds, settling anything that finished in that span |
| `print board` | Prints the current board state |

## How the game plays

> **Moves take time, and they run in parallel.** A move takes `cells × ms_per_cell` (1000 ms per
> cell; a diagonal square counts as **one** cell). The piece stays on its origin cell until it
> arrives, so `print board` is deterministic. **Any number of pieces may be moving at once** — the
> only restriction is per piece: a piece that is moving, jumping or resting is **busy**, and a
> command for it is rejected with `piece_busy`.

> **Cooldown.** After a move a piece enters a **long rest** (`long_rest_ms`, 2000 ms). After a jump
> it enters a **short rest** (`short_rest_ms`, 500 ms) and then returns to idle. A resting piece is
> busy and cannot be commanded.

> **Jump / dodge.** `jump x y` makes the piece jump in place for `jump_duration_ms` (1000 ms)
> without leaving its cell; it does not lock the board. Throughout the jump **and** the short rest
> that follows, the piece **protects its cell**: anyone who finishes a move onto that cell is
> captured instead — friend or foe. A jump is only refused if the piece itself is busy.

> **Collisions.** Because moves overlap in time, the board can change while a piece is travelling:
> - **On arrival** — an empty cell: it lands. An enemy: captured, and it takes the cell. A friend:
>   the move **fails silently** (nobody moves, nothing is captured). A **protected** cell (its
>   occupant is jumping or short-resting): the *arriver* is captured.
> - **Mid-path** — a stationary friend stops the slide one cell short (or cancels it); a stationary
>   enemy is captured and the slide stops there; a jumping/short-resting piece redirects the slide
>   onto it, so the protection above applies.
> - **Two movers meeting** — between enemies the one that **started first** survives and the later
>   one is captured; between friends the later one stops and both survive.
> - The **knight is exempt from all of it** (`flies_over`) — it flies over collisions, and it is the
>   only piece that may capture a friendly piece by arriving on it.
>
> Requesting a move is still validated normally against the board at that moment: a destination
> occupied by a friend, or a path already blocked, is rejected up front.

> **Pawns.** One step forward into an empty cell, or a **two-step first move** from the start rank;
> capture one diagonal step forward; reaching the last rank **promotes** to a queen — or to whatever
> `promotes_to` names in [config.toml](kongfuchess/config.toml). (No en passant.)

> **Victory.** Capturing a piece marked `victory_on_capture` (the king) ends the game; later moves
> are ignored, though `print board` still works.

> **Heads up:** click coordinates are `(x, y)` in pixels, while the board is indexed by `(row, col)`.
> The conversion is `row = y // cell_size`, `col = x // cell_size` (cell size = 100).

## Code structure

The engine is layered, and every collaborator is **injected** — no class builds its own
dependencies, and only [composition/app_factory.py](kongfuchess/composition/app_factory.py) knows
more than one layer. Each kind of change therefore has exactly one home.

All source lives in the [kongfuchess/](kongfuchess/) package, separated from `.venv`, tests and other
project files at the root.

| Layer | Responsibility |
|------|----------------|
| [model/](kongfuchess/model/) | Domain core: `Position`, `Piece` (`PieceKind` is an open value object, not an enum), the `BoardView`/`MutableBoard` ports, `Board`, `GameState`, and the neutral vocabulary the layers above talk in — `Effect`s plus the `ArrivalContext`/`BlockContext`/`CrossContext` questions |
| [rules/](kongfuchess/rules/) | **The only layer that knows what chess is.** `PieceRule` strategies (`SlidingRule`, `LeapingRule`, `PawnRule`, …) built from config by `rule_factory.py`; `ChessRuleSet` answers "is this legal?", "what does this arrival do?" and "what does this collision mean?" — always as data, never by mutating |
| [realtime/](kongfuchess/realtime/) | `Motion`, `RealTimeArbiter` (many parallel motions + each piece's timed jump/rest lifecycle) and `CollisionResolver` (who is where, who started first). **No chess at all**: it states the situation to the injected rule set and applies the effects it gets back |
| [engine/game_engine.py](kongfuchess/engine/game_engine.py) | `GameEngine` — the public command boundary (`request_move`, `request_jump`, `wait`, `snapshot`, `active_motions`, `airborne_cells`) |
| [input/](kongfuchess/input/) | `BoardMapper` (pixels → cells) and `Controller` (click selection → `request_move`) |
| [text_io/](kongfuchess/text_io/) | `TokenCodec` (the token format, symbols injected from config), `PieceFactory` (stable ids), `BoardParser`, `BoardPrinter` |
| [texttests/](kongfuchess/texttests/) | `ScriptParser` (document → board + commands) and `ScriptRunner` (dispatches through an injected command table) |
| [view/](kongfuchess/view/) | The **OpenCV surface**, built to `final_plan.md`'s State/Strategy/Observer/DI design: `sprites/` (`SpriteState`/`AnimatedSprite` + the `SpriteLibrary` asset Strategy), `rendering/` (a `BoardView` coordinator over `BoardRenderer`/`PieceRenderer`/`OverlayRenderer`/`PanelRenderer`, the `Renderer` port and the resizable `Cv2Renderer`), `events/` (an `EventBus` fed by a snapshot-diff `SettlementDetector`, driving the score and moves-log observers), and the real-time `GameLoop`. Holds no chess and no timing |
| [composition/](kongfuchess/composition/) | The composition root — builds and wires everything (text **and** GUI) from a `GameConfig`. The swap point for a different rule set, time model, board or surface |
| [main.py](kongfuchess/main.py) / [gui.py](kongfuchess/gui.py) | The two entry points: a document from stdin (text), or a board file + OpenCV window (GUI) |
| [config.py](kongfuchess/config.py) / [config.toml](kongfuchess/config.toml) | Tunables, **the pieces themselves**, and the GUI assets/panel settings, loaded from an external file |

## Configuration

Game constants live in [config.toml](kongfuchess/config.toml), not in code — including **the
pieces**. Edit the file and run again; no code changes needed.

```toml
[board]
cell_size = 100          # pixels per square

[timing]
ms_per_cell = 1000       # time to cross one cell
jump_duration_ms = 1000  # how long a jump lasts
long_rest_ms = 2000      # cooldown after a move
short_rest_ms = 500      # cooldown after a jump

[players]
white = "White"          # names shown on the side panel
black = "Black"

[panel]
width = 300              # side-panel width in pixels (0 hides it)
```

`[assets]` holds the GUI's board image, sprite folder, default starting board, the white/black folder
suffixes and the sprite-state folder names — so re-skinning the game is configuration only.

### Adding a piece

A piece is a `[[pieces]]` block: what it is called, the letter it is spelled with, how it moves, what
it is worth, and whether taking it wins the game. Adding one is **configuration only — no code**:

```toml
[[pieces]]
name = "archbishop"
symbol = "A"
value = 7                                                # score-panel points
movement = "combined"                                    # bishop + knight
directions = [[1, 1], [1, -1], [-1, 1], [-1, -1]]
offsets = [[2, 1], [2, -1], [-2, 1], [-2, -1], [1, 2], [1, -2], [-1, 2], [-1, -2]]
```

Movement patterns: `slide` (travels along `directions` until blocked), `leap` (jumps to fixed
`offsets`), `combined` (both), and `pawn`. Optional keys: `promotes_to = "<name>"`,
`victory_on_capture = true`, and `flies_over = true` (exempt from collisions and allowed to capture a
friendly piece, like the knight). Only a movement pattern that does not exist yet needs code — one
`PieceRule` subclass plus one entry in
[rules/rule_factory.py](kongfuchess/rules/rule_factory.py), and nothing outside `rules/`. See
[tests/integration/test_custom_game.py](tests/integration/test_custom_game.py) for whole games (an
invented piece, a different promotion, a different victory condition) defined purely in config.

To make a new piece appear in the **GUI**, add its sprite folders under `assets.pieces_dir`:
`<symbol><white_suffix>/` and `<symbol><black_suffix>/` (e.g. `AW`/`AB`), each with
`states/<idle|move|jump|short_rest|long_rest>/sprites/*.png` and a `config.json`. Still no code.

[config.py](kongfuchess/config.py) reads the file via the standard-library `tomllib` and returns an
immutable `GameConfig`, which the composition root injects wherever it is needed — the values are
never module-level globals for a layer to reach into.

## Tests

The suite lives in [tests/](tests/): `tests/unit/` (per-layer) and `tests/integration/` (end-to-end).
Every GUI test runs **headless** — no window is ever opened.
[tests/test_layer_boundaries.py](tests/test_layer_boundaries.py) parses every module's imports and
fails the build if a layer reaches across a boundary it is not allowed to — so the decoupling is an
enforced invariant, not a good intention.

```bash
pytest                                      # run all tests
pytest --cov=. --cov-report=term-missing    # coverage in the terminal
pytest --cov=. --cov-report=html            # coverage as a report in htmlcov/index.html
pytest tests/unit/test_collision_resolver.py  # a single file
pytest -k pawn                              # by expression
```
