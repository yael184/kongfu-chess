# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements-dev.txt        # test deps (pytest, pytest-cov)
pytest                                      # run the suite in tests/ (see pytest.ini)
pytest --cov=. --cov-report=term-missing    # run with coverage report
pytest tests/unit/test_rule_engine.py       # run one file
pytest tests/unit/test_rule_engine.py::test_valid_move_is_ok   # run one test
pytest -k pawn                              # run tests matching an expression
```

`pytest.ini` sets `testpaths = tests` and `pythonpath = .`. `pythonpath = .` puts the repo root on `sys.path` so tests can `from model.board import Board` etc. Tests are split into `tests/unit/` (per-layer unit tests) and `tests/integration/` (end-to-end), both packages (they have `__init__.py`); `tests/test_config.py` sits at the top level.

Run the game itself by feeding a board+commands document to `main.py` on stdin:

```bash
python main.py < input.txt
```

## Input format

`main.py` runs a single text document with two labeled sections. Both `Board:` and `Commands:` markers are required or it prints `ERROR UNKNOWN_TOKEN` and calls `sys.exit(0)`:

```
Board:
wK . bK
. . .
Commands:
click 50 50
click 150 50
print board
```

Board rows must all be the same width (else `ERROR ROW_WIDTH_MISMATCH`). Each token is either `.` (empty) or a two-char `<color><symbol>` where color is `w`/`b` and symbol is one of `K R B Q N P` (unknown token → `ERROR UNKNOWN_TOKEN`). Commands are `click x y` (pixels), `jump x y` (pixels — dodge in place), `wait <ms>`, and `print board`. Coordinates are pixels: `col = x // CELL_SIZE`, `row = y // CELL_SIZE`.

## Architecture

Layered stack, wired end-to-end through `main.py`. Data flow for the text surface:

`stdin → ScriptParser (split Board:/Commands:) → BoardParser (text → model.Board) → GameEngine(GameState, RealTimeArbiter) + Controller → ScriptRunner dispatches commands → BoardPrinter renders`.

Dependencies point inward: `model/` knows nothing about the layers around it; `rules/`, `realtime/`, `engine/`, `input/`, `text_io/`, `texttests/` build on `model/` (and `config`). Each layer is isolated so an alternate surface (GUI, network, binary board) can be added without touching the core.

- **`model/`** — the domain core: no rules, timing, rendering, or input knowledge.
  - `position.py` — `Position` (frozen value object: `row`/`col`; value equality, hashable, readable repr; **no bounds** — bounds belong to `Board`).
  - `piece.py` — `Piece` (entity: stable `id`, `Color`/`PieceKind`/`PieceState` enums, `cell: Position`; `state` is a lifecycle flag only — idle/moving/captured, **no** path/speed/arrival). A piece knows nothing about renderer/pixels/tokens.
  - `board.py` — `Board` (stores `width`/`height`; `add_piece`/`remove_piece`/`piece_at`/`move_piece`/`is_within_bounds`; **empty cells return `None`**; enforces one-piece-per-cell via `DuplicateOccupancyError`; also `OutOfBoundsError`/`PieceNotFoundError`; contains **no** movement rules; `move_piece` assumes validation already happened and requires an empty destination — so captures remove the victim first).
  - `game_state.py` — `GameState`: data holder for `board` + `game_over` (flipped by `GameEngine` on a reported king capture).
- **`rules/`** — stateless movement rules + read-only validation. `piece_rules.py`: one `PieceRule` per kind exposing `legal_destinations(board, piece) -> set[Position]` (enemy-occupied cells are legal; never captures/moves/mutates). `QueenRule` = `RookRule | BishopRule`; `KnightRule`/`KingRule` jump; `PawnRule` — white moves up `row-1`, black down `row+1`; one step into empty, diagonal capture, and a **two-step first move from the start row** (white `height-2`, black `1`) if both cells are empty; **no** en-passant. `promotion_kind(piece, board)` returns `PieceKind.QUEEN` for a pawn on its last row (white `0`, black `height-1`), else `None`. `rule_for(kind)` returns the shared stateless instance — **the extension point for new piece types**. `rule_engine.py`: `RuleEngine.validate_move(board, source, destination) -> MoveValidation(is_valid, reason)`, read-only. Reasons: `ok`, `outside_board`, `empty_source`, `friendly_destination`, `illegal_piece_move`. Game-over is **not** a RuleEngine concern.
- **`realtime/`** — real-time movement, isolated here. `motion.py`: `Motion` (`piece`/`source`/`destination`/`start_ms`/`arrival_ms`; `Motion.start` sets `arrival = now + cell_distance*ms_per_cell`) and `cell_distance` (Chebyshev — **diagonal steps cost one cell**: 1 diagonal square = 1000 ms, 3 = 3000 ms). `real_time_arbiter.py`: `RealTimeArbiter` owns the active `Motion` collection **and the airborne (jumping) set**, both **outside `Board`**, and receives only validated commands. `has_active_motion()` exposes the common-route fact (GameEngine enforces one-active-motion). **Logical board rule:** a moving piece stays on its source cell until arrival, so `print board` is deterministic. `advance_time(ms)` (never real sleep) advances the clock, **atomically** resolves each arrived motion, then expires landed jumps; returns `AdvanceResult(king_captured)`. Arrival resolution: **jump collision** — if an enemy is still airborne on the destination when the mover arrives (`arrival <= land_ms`), the jumper eats the arriving attacker (attacker removed from its origin, jumper stays); otherwise normal capture-and-move, then `promotion_kind` is applied (pawn → queen on the last row). `request_jump(board, cell)` records `airborne[cell] = clock + JUMP_DURATION_MS` — ignored for an empty cell, an in-flight piece, or one already airborne; a jump does **not** lock the board. Cell-step duration = `config.MS_PER_CELL` (= `CELL_SIZE`px / `PIECE_SPEED` 100 px·s⁻¹ → 1000 ms; `PIECE_SPEED` itself is a future-renderer concern, not in config yet).
- **`engine/game_engine.py`** — `GameEngine`, the application-service layer and **public command boundary**. Orchestration only — no movement logic, rendering, pixel mapping, text parsing. Collaborators injected: `GameState`, `RealTimeArbiter` (duck-typed: `has_active_motion`/`start_motion`/`request_jump`/`advance_time`), `RuleEngine` (defaults to real). `request_move(source, destination) -> MoveResult(is_accepted, reason)`: rejects `game_over` (before consulting rules), then `motion_in_progress`, then delegates to `RuleEngine.validate_move` (copying its reason on rejection), else starts the motion → `ok`. `request_jump(cell)` delegates to the arbiter (ignored once `game_over`). `wait(ms)` delegates to `arbiter.advance_time` and sets `game_over` on a king capture — it never touches the board or motions directly. `snapshot() -> GameSnapshot` (read-only `width`/`height`/`is_within_bounds`/`piece_at`/`game_over`, placements copied at snapshot time) for the printer/renderer.
- **`input/`** — the click→command layer. `board_mapper.py`: `BoardMapper.to_cell(x, y) -> Position` (`col = x // CELL_SIZE`, `row = y // CELL_SIZE`; no camera in the common route — any viewport support lives here, never in the model). `controller.py`: `Controller.handle_click(x, y)`/`handle_jump(x, y)` map pixels and delegate to `GameEngine` — the controller decides no legality, never calls `Board.move_piece`/`RuleEngine`, reads bounds/occupancy via `GameEngine.snapshot()`. Click policy: first click ignores outside-board and empty-cell clicks, else selects; a second click on a **same-color piece switches the selection**; another **in-board** second click sends the move and clears the selection (legal or not); an **outside-board** second click cancels the selection. `handle_jump` maps the cell and calls `GameEngine.request_jump`.
- **`text_io/`** — the text I/O format layer (named `text_io`, not `io`, because `io/` would shadow the stdlib `io` module). `piece_factory.py`: `PieceFactory` builds `model.Piece`s assigning **unique stable ids** in creation order; owns the token↔piece codec (`decode_token`/`token_for_piece`) — the single source of truth for the `<color><symbol>` token format. `board_parser.py`: `BoardParser.parse(board_text) -> model.Board` (infers dimensions, uses the factory; raises `BoardParseError(ROW_WIDTH_MISMATCH|UNKNOWN_TOKEN)`). `board_printer.py`: `BoardPrinter.to_text(view)` renders any view exposing `width`/`height`/`piece_at` (a `Board` **or** a `GameSnapshot`) to text.
- **`texttests/`** — the text-driven surface. `script_parser.py`: `ScriptParser.parse(text) -> ParsedScript(board_text, commands)` (splits the `Board:`/`Commands:` document; raises `ScriptParseError(UNKNOWN_TOKEN)` on missing markers). `script_runner.py`: `ScriptRunner.run(commands)` dispatches `click x y`/`jump x y` → `Controller`, `wait ms` → `GameEngine.wait`, `print board` → `BoardPrinter.to_text(engine.snapshot())`; unknown → `ERROR: Unknown command`.
- **`config.py` / `config.toml`** — access layer for tunables (`CELL_SIZE`, `MS_PER_CELL`, `JUMP_DURATION_MS`, `EMPTY_TOKEN`). Values live in the external **`config.toml`** (read on import via `tomllib`); `config.load(path=None)` re-reads it. **Add new tunables to `config.toml` and map them in `config.load`, not as literals in code.**
- **`main.py`** — `main(input_stream=None)` (stdin by default, injectable for tests). Reads the document, runs `ScriptParser` + `BoardParser` (translating parse errors to `ERROR <code>` + `sys.exit(0)`), wires `GameEngine`/`Controller`/`ScriptRunner`, and runs the commands.

### Conventions that bite

- **`Board` is indexed by `Position(row, col)`, but clicks are pixels `(x, y)`.** `BoardMapper` maps `col = x // CELL_SIZE`, `row = y // CELL_SIZE` — x→col, y→row. Getting this backwards is the classic bug.
- **Empty cells are `None`** (`board.piece_at(pos) is None`) — there is no Null-Object empty cell in the model.
- **Enums, not strings, in logic**: `Color.WHITE`/`PieceKind.ROOK`/`PieceState.MOVING`. The single-char `w`/`b` + symbol exist only in text tokens, encoded/decoded by `text_io.piece_factory`.
- **Still missing vs. full Kung-Fu-Chess**: no post-move **cooldown**, no scoring, no networking. (Jump/dodge, pawn two-step, and promotion **are** implemented.)
- **The one-active-motion lock** lives in `GameEngine` (via `arbiter.has_active_motion()`), not in `Board`. A second `request_move` while a motion is in flight returns `motion_in_progress` without consulting the rules. A **jump** is not a motion — it does not lock the board and can coexist with an incoming enemy move (that's what makes a dodge possible).

## Project context

`kong_fu_chess_requirements.md` is the full product spec (Hebrew): Kung-Fu-Chess is meant to be a **real-time, no-turns** game where moves take physical travel time, pieces have a post-move cooldown, and you win only by actually capturing the enemy king (no check/checkmate). **The current code is a layered rebuild** implementing real-time movement over time (the `realtime/` layer), king-capture win, jump/dodge, pawn two-step and promotion, and a text surface. Still **simplified**: no post-move cooldown, no scoring, no networking. When extending, honor the spec's design principle: make the *known* future extensions (new piece types via `rules/`, new commands, a `view/` renderer, a binary board) easy, but do **not** add speculative abstractions for things not yet needed.

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
