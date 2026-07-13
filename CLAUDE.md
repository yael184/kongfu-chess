# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -r requirements-dev.txt        # test deps (pytest, pytest-cov)
pytest                                      # run the suite in tests/ (see pytest.ini)
pytest --cov=. --cov-report=term-missing    # coverage in the terminal
pytest --cov=. --cov-report=html            # coverage as a browsable report in htmlcov/index.html
pytest tests/unit/test_rule_engine.py       # run one file
pytest tests/unit/test_rule_engine.py::test_valid_move_is_ok   # run one test
pytest -k pawn                              # run tests matching an expression
```

`pytest.ini` sets `testpaths = tests` and `pythonpath = .`. `pythonpath = .` puts the repo root on `sys.path` so tests can `from model.board import Board` etc. Tests are split into `tests/unit/` (per-layer unit tests) and `tests/integration/` (end-to-end), both packages (they have `__init__.py`); `tests/test_config.py` and `tests/test_layer_boundaries.py` sit at the top level.

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

Board rows must all be the same width (else `ERROR ROW_WIDTH_MISMATCH`). Each token is either the empty token (`.`) or a two-char `<color><symbol>` where color is `w`/`b` and the symbol is whatever the configured pieces declare (`K R B Q N P` as shipped; unknown token → `ERROR UNKNOWN_TOKEN`). Commands are `click x y` (pixels), `jump x y` (pixels — dodge in place), `wait <ms>`, and `print board`. Coordinates are pixels: `col = x // cell_size`, `row = y // cell_size`.

## Architecture

Layered stack, assembled by a **composition root** (`composition/app_factory.py`) and entered through `main.py`. Data flow for the text surface:

`stdin → ScriptParser (split Board:/Commands:) → BoardParser (text → model.Board) → app_factory builds GameEngine + RealTimeArbiter + ChessRuleSet + Controller → ScriptRunner dispatches commands → BoardPrinter renders`.

**Everything is injected; nothing is ambient.** No class constructs its own collaborators, no class has a default argument pointing at a concrete class, and no layer imports `config`. `composition/app_factory.py` is the only module allowed to name classes from more than one layer — every other module depends solely on what it is handed. `tests/test_layer_boundaries.py` enforces this by parsing imports, so a leak fails the build rather than rotting quietly.

The point of the layering is that each kind of change has exactly one home:

| To change… | You edit… |
| --- | --- |
| how a piece moves, what an arrival does, what wins | `rules/` (often just `config.toml`) |
| the time model (real-time → turn-based) | `realtime/` |
| how the board is stored (e.g. binary) | `model/board.py` + `text_io/` (the conversion) |
| adding a piece | `config.toml` — a `[[pieces]]` block, no code |
| adding a command | the command table in `composition/app_factory.py` |

- **`model/`** — the domain core: no rules, timing, rendering, or input knowledge. Depends on nothing.
  - `position.py` — `Position` (frozen value object: `row`/`col`; value equality, hashable; **no bounds** — bounds belong to `Board`).
  - `piece.py` — `Piece` (entity: stable `id`, `Color` enum, `PieceKind`, `cell`, `state`). **`PieceKind` is a frozen value object, not an enum** — an open set, so `PieceKind("dragon")` is as valid as `PieceKind.KING`; the six standard kinds are convenience constants, not the vocabulary. `Color` stays an enum (genuinely closed). `is_ally_of`/`is_enemy_of` are the single source of the friend/foe test. `state` is a lifecycle flag only — idle/moving/captured, **no** path/speed/arrival.
  - `board_view.py` — the **`BoardView` / `MutableBoard` ports**: `width`/`height`/`is_within_bounds`/`piece_at`/**`pieces()`**/**`rows()`**. `pieces()` and `rows()` exist so that nothing outside `model/` ever rebuilds the grid with `range(height) × range(width)` — that loop is what would pin the board to a dense array.
  - `board.py` — `_GridBoard` (the one class that knows a board is a rectangular grid), `Board` (mutable: `add_piece`/`remove_piece`/`move_piece`, plus `snapshot()`), `BoardSnapshot` (immutable copy). **Empty cells return `None`**; one-piece-per-cell via `DuplicateOccupancyError`; also `OutOfBoundsError`/`PieceNotFoundError`. `move_piece` assumes validation already happened and requires an empty destination — so captures remove the victim first.
  - `effects.py` — the **effects vocabulary**: `RemovePiece` / `MovePiece` / `TransformPiece` / `EndGame`, each knowing how to `apply(board)` itself, plus `EffectApplier`. This is the *answer* half of the rules contract.
  - `arrival.py` — `ArrivalContext(board, piece, destination, destination_is_protected)`: the *question* half. Both halves live in the model, on neutral ground, so `rules/` and `realtime/` never import each other.
  - `game_state.py` — `GameState`: data holder for `board` + `game_over`.
- **`rules/`** — the **only layer that knows what chess is**. Stateless, and it never mutates: it answers with data.
  - `piece_rules.py` — `PieceRule` is the strategy every piece plugs into: `legal_destinations(board, piece)` plus `kind_after_arrival(board, piece, cell)` (promotion, generalized — a rule decides what a piece *becomes*). Implementations are **parameterized, not per-piece**: `SlidingRule(directions)` covers rook/bishop/queen, `LeapingRule(offsets)` covers knight/king, `CombinedRule` unions patterns, `PawnRule(promotes_to)` is the one special case. `PieceRuleRegistry.rule_for(kind)` is the lookup; it is built from config, never a module global.
  - `rule_factory.py` — builds the rules from `[[pieces]]` specs. `MOVEMENT_BUILDERS` maps a spec's `movement` name to a builder: **a new piece with an existing pattern is config only; a genuinely new pattern is one `PieceRule` subclass + one entry here, and nothing outside `rules/`.**
  - `rule_set.py` — `ChessRuleSet`, the single facade: `legal_destinations`, `validate_move`, and **`resolve_arrival(ArrivalContext) -> [Effect]`** — capture semantics, the dodge outcome, promotion and the victory condition, all expressed as effects for someone else to apply.
  - `rule_engine.py` — `RuleEngine.validate_move(board, source, destination) -> MoveValidation(is_valid, reason)`, read-only, registry injected. Reasons: `ok`, `outside_board`, `empty_source`, `friendly_destination`, `illegal_piece_move`.
- **`realtime/`** — the model of **time**, and it holds **no chess whatsoever** (no `PieceKind`, no king, no promotion, no capture logic — the boundary test asserts this). `motion.py`: `Motion` + `cell_distance` (Chebyshev — **diagonal steps cost one cell**: 1 diagonal square = 1000 ms, 3 = 3000 ms). `real_time_arbiter.py`: `RealTimeArbiter(rules, effect_applier, ms_per_cell, jump_duration_ms)` owns the active motions **and the airborne (jumping) set**, both **outside `Board`**. **Logical board rule:** a moving piece stays on its source cell until arrival, so `print board` is deterministic. `advance_time(ms)` (never real sleep) advances the clock, resolves arrivals, then expires landed jumps; returns `AdvanceResult(game_over)` — deliberately *not* `king_captured`. On arrival it builds an `ArrivalContext`, supplying the one fact only it can know (`destination_is_protected`: an enemy is still mid-dodge there), asks the injected rule set, and applies whatever effects come back. `request_jump(board, cell)` marks the cell airborne until `clock + jump_duration_ms` — ignored for an empty cell, an in-flight piece, or one already airborne; a jump does **not** lock the board.
- **`engine/game_engine.py`** — `GameEngine(game_state, arbiter, rules)`, the application-service layer and **public command boundary**. Orchestration only, all collaborators injected and duck-typed. `request_move` rejects `game_over` (before consulting rules), then `motion_in_progress`, then delegates to `rules.validate_move` (copying its reason), else starts the motion → `ok`. `wait(ms)` delegates to `arbiter.advance_time` and sets `game_over` when the arbiter reports it — *which* event ends the game is a rules decision the engine never sees. `snapshot() -> GameSnapshot` wraps a `BoardSnapshot` and delegates every board question to it (no bounds arithmetic, no grid walking).
- **`input/`** — the click→command layer. `board_mapper.py`: `BoardMapper(cell_size).to_cell(x, y)` (`col = x // cell_size`, `row = y // cell_size`; any viewport/camera support lives here, never in the model). `controller.py`: `Controller(engine, mapper)` maps pixels and delegates — it decides no legality, never calls `Board.move_piece` or the rules, and reads bounds/occupancy via `GameEngine.snapshot()`. Click policy: first click ignores outside-board and empty-cell clicks, else selects; a second click on a **same-color piece switches the selection**; another **in-board** second click sends the move and clears the selection (legal or not); an **outside-board** second click cancels the selection.
- **`text_io/`** — the text I/O format layer (named `text_io`, not `io`, because `io/` would shadow the stdlib module). `token_codec.py`: **`TokenCodec` is the single source of truth for the `<color><symbol>` format**, and its symbol map is *injected* from the configured pieces — so a new piece brings its own token and nothing here changes. `piece_factory.py`: `PieceFactory` only assigns **unique stable ids** (it no longer knows about tokens). `board_parser.py`: `BoardParser(factory, codec).parse(text) -> Board` (raises `BoardParseError(ROW_WIDTH_MISMATCH|UNKNOWN_TOKEN)`). `board_printer.py`: `BoardPrinter(codec).to_text(view)` renders any `BoardView` via `rows()`. Parser + printer are "the conversion": with `model/board.py` they are the only things that would change if the board's representation did.
- **`texttests/`** — the text-driven surface. `script_parser.py`: `ScriptParser.parse(text) -> ParsedScript(board_text, commands)`. `commands.py`: the handlers (`pixel_command`, `duration_command`, `print_board_command`) and `UnknownCommandError`. `script_runner.py`: `ScriptRunner(commands)` dispatches each line through an **injected command table** — it knows no command by name, so adding one is a table entry, not an edit to its if/elif chain. Unknown command, or known command with arguments that do not fit → `ERROR: Unknown command '<line>'`.
- **`composition/app_factory.py`** — the composition root. Builds the codec, parser, printer, rule set, arbiter, engine, controller and command table from a `GameConfig`. **The swap point for everything**: a different rule set, time model, board or surface is a change here and nowhere else. Notably it contains *no list of pieces* — that comes from config.
- **`config.py` / `config.toml`** — `load(path=None) -> GameConfig` **returns an immutable value** (it does not populate module globals; a config is injected, not reached into). `GameConfig` holds `cell_size`, `ms_per_cell`, `jump_duration_ms`, `empty_token`, and `pieces: tuple[PieceSpec]`. A `PieceSpec` is `name`/`symbol`/`movement`/`directions`/`offsets`/`promotes_to`/`victory_on_capture`. **Add new tunables to `config.toml` and map them in `config.load`, never as literals in code.**
- **`main.py`** — `main(input_stream=None)` (stdin by default, injectable for tests). Reads the document, parses script + board (translating parse errors to `ERROR <code>` + `sys.exit(0)`), then hands off to the composition root.

### Adding a piece

Add a `[[pieces]]` block to `config.toml` — `name`, `symbol`, a `movement` pattern (`slide` / `leap` / `combined` / `pawn`) and its `directions`/`offsets`, optionally `promotes_to` and `victory_on_capture`. That is the whole change: no code in `model/`, `rules/`, `text_io/` or anywhere else. Only a movement *pattern* nobody has written yet needs code, and then only a `PieceRule` subclass plus a `MOVEMENT_BUILDERS` entry, both inside `rules/`. `tests/integration/test_custom_game.py` demonstrates this end to end with an invented piece.

### Conventions that bite

- **`Board` is indexed by `Position(row, col)`, but clicks are pixels `(x, y)`.** `BoardMapper` maps `col = x // cell_size`, `row = y // cell_size` — x→col, y→row. Getting this backwards is the classic bug.
- **Empty cells are `None`** (`board.piece_at(pos) is None`) — there is no Null-Object empty cell in the model.
- **Never walk the grid outside `model/`.** Use `board.pieces()` or `board.rows()`; `range(height) × range(width)` in any other layer is a board-representation leak and is what a binary board would break.
- **Values, not strings, in logic**: `Color.WHITE` / `PieceState.MOVING` are enums; `PieceKind` is a *value object* (`PieceKind("dragon")`) because the set of pieces must stay open. The single-char `w`/`b` + symbol exist only in text tokens, encoded/decoded by `text_io.token_codec`.
- **Nothing outside `composition/` imports `config`**, and no constructor has a default collaborator. If you find yourself reaching for one, inject it instead — `tests/test_layer_boundaries.py` will fail you otherwise.
- **Rules never mutate; `realtime/` never decides.** A rule returns `Effect`s and the arbiter applies them. If you are about to write `if piece.kind == ...` outside `rules/`, stop.
- **Still missing vs. full Kung-Fu-Chess**: no post-move **cooldown**, no scoring, no networking. (Jump/dodge, pawn two-step, and promotion **are** implemented.)
- **The one-active-motion lock** lives in `GameEngine` (via `arbiter.has_active_motion()`), not in `Board`. A second `request_move` while a motion is in flight returns `motion_in_progress` without consulting the rules. A **jump** is not a motion — it does not lock the board and can coexist with an incoming enemy move (that's what makes a dodge possible).

## Project context

`kong_fu_chess_requirements.md` is the full product spec (Hebrew): Kung-Fu-Chess is meant to be a **real-time, no-turns** game where moves take physical travel time, pieces have a post-move cooldown, and you win only by actually capturing the enemy king (no check/checkmate). **The current code is a layered rebuild** implementing real-time movement over time (the `realtime/` layer), a configurable victory condition, jump/dodge, pawn two-step and promotion, config-driven pieces, and a text surface. Still **simplified**: no post-move cooldown, no scoring, no networking. When extending, honor the spec's design principle: make the *known* future extensions (new piece types, new rule sets, new commands, a `view/` renderer, a binary board) easy, but do **not** add speculative abstractions for things not yet needed.

## Architecture Principles - Extensibility (must respect)

1. **Future binary representation of board/pieces**: currently a dict of `Position -> Piece`,
   but a move to a binary representation may be needed to save memory.
   - Do NOT implement this now.
   - Mandatory: all access to the board/pieces goes through the `BoardView` / `MutableBoard`
     ports in `model/board_view.py` — never touch the internal data structure, and never rebuild
     the grid yourself. `pieces()` and `rows()` exist so you don't have to.
   - When working on new code that touches the board/pieces, always ask:
     "If the internal representation switches to binary tomorrow, will this code still work?"
     Today the honest answer is yes: only `model/board.py` and the `text_io/` conversion would change.

2. **User-defined games (custom rules engine)**: users define custom movement rules per piece,
   including non-standard behavior (a pawn reversing direction instead of promoting, a piece that
   does not exist in chess, a different victory condition).
   - **This is now implemented** — the strategy pattern in `rules/piece_rules.py`, driven by
     `[[pieces]]` in `config.toml` via `rules/rule_factory.py`. See "Adding a piece" above.
   - Mandatory: no hard-coding of movement rules inside game/piece logic. Every movement rule
     stays swappable/externally definable — never embedded if/else logic, and never a check on a
     piece's kind outside `rules/`.
   - Before implementing movement logic for a piece, check: "Could this be replaced with a
     completely different rule without touching this code?"

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
