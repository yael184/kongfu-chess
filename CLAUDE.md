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
python -m kongfuchess.main < input.txt
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

Layered stack, assembled by a **composition root** (`composition/app_factory.py`) and entered through two peer surfaces: `main.py` (text) and `gui.py` (OpenCV). Data flow for the text surface:

`stdin → ScriptParser (split Board:/Commands:) → BoardParser (text → model.Board) → app_factory builds GameEngine + RealTimeArbiter + ChessRuleSet + Controller → ScriptRunner dispatches commands → BoardPrinter renders`.

And for the graphical surface (`python -m kongfuchess.gui [board-file]`):

`board file → BoardParser → app_factory builds the same GameEngine + Controller + a BoardRenderer → GameLoop (real-time clock in, mouse in, OpenCV pixels out)`. The two surfaces share the entire engine; they differ only in how time enters (a `wait` command vs. a real clock) and how state leaves (text vs. sprites).

**Everything is injected; nothing is ambient.** No class constructs its own collaborators, no class has a default argument pointing at a concrete class, and no layer imports `config`. `composition/app_factory.py` is the only module allowed to name classes from more than one layer — every other module depends solely on what it is handed. `tests/test_layer_boundaries.py` enforces this by parsing imports, so a leak fails the build rather than rotting quietly.

The point of the layering is that each kind of change has exactly one home:

| To change… | You edit… |
| --- | --- |
| how a piece moves, what an arrival does, what wins, what a collision means | `rules/` (often just `config.toml`) |
| the time model, cooldown durations, collision *detection* | `realtime/` (durations in `config.toml`) |
| how the board is stored (e.g. binary) | `model/board.py` + `text_io/` (the conversion) |
| adding a piece | `config.toml` — a `[[pieces]]` block (+ a sprite folder for the GUI), no code |
| adding a command | the command table in `composition/app_factory.py` |
| how the game looks (the GUI) | `view/` + the `[assets]` config |

- **`model/`** — the domain core: no rules, timing, rendering, or input knowledge. Depends on nothing.
  - `position.py` — `Position` (frozen value object: `row`/`col`; value equality, hashable; **no bounds** — bounds belong to `Board`).
  - `piece.py` — `Piece` (entity: stable `id`, `Color` enum, `PieceKind`, `cell`, `state`). **`PieceKind` is a frozen value object, not an enum** — an open set, so `PieceKind("dragon")` is as valid as `PieceKind.KING`; the six standard kinds are convenience constants, not the vocabulary. `Color` stays an enum (genuinely closed). `is_ally_of`/`is_enemy_of` are the single source of the friend/foe test. `state` is a lifecycle flag only — `idle`/`moving`/`jumping`/`short_rest`/`long_rest`/`captured`, saying *what phase* a piece is in, **no** path/speed/timer/arrival (the arbiter owns the timers). A piece is *busy* whenever it is not `idle`; `jumping`/`short_rest` are the states that protect a cell.
  - `arrival.py` / `collision.py` — the neutral *question* halves of the rules contract (with `effects.py` as the *answer*): `ArrivalContext` (a piece reached a cell) and `BlockContext`/`CrossContext` + `CollisionResolution` (pieces met in flight). They live in `model/` so `rules/` and `realtime/` never import each other.
  - `board_view.py` — the **`BoardView` / `MutableBoard` ports**: `width`/`height`/`is_within_bounds`/`piece_at`/**`pieces()`**/**`rows()`**. `pieces()` and `rows()` exist so that nothing outside `model/` ever rebuilds the grid with `range(height) × range(width)` — that loop is what would pin the board to a dense array.
  - `board.py` — `_GridBoard` (the one class that knows a board is a rectangular grid), `Board` (mutable: `add_piece`/`remove_piece`/`move_piece`, plus `snapshot()`), `BoardSnapshot` (immutable copy). **Empty cells return `None`**; one-piece-per-cell via `DuplicateOccupancyError`; also `OutOfBoundsError`/`PieceNotFoundError`. `move_piece` assumes validation already happened and requires an empty destination — so captures remove the victim first.
  - `effects.py` — the **effects vocabulary**: `RemovePiece` / `MovePiece` / `TransformPiece` / `EndGame`, each knowing how to `apply(board)` itself, plus `EffectApplier`. This is the *answer* half of the rules contract.
  - `arrival.py` — `ArrivalContext(board, piece, destination, destination_is_protected)`: the *question* half. Both halves live in the model, on neutral ground, so `rules/` and `realtime/` never import each other.
  - `game_state.py` — `GameState`: data holder for `board` + `game_over`.
- **`rules/`** — the **only layer that knows what chess is**. Stateless, and it never mutates: it answers with data.
  - `piece_rules.py` — `PieceRule` is the strategy every piece plugs into: `legal_destinations(board, piece)` plus `kind_after_arrival(board, piece, cell)` (promotion, generalized — a rule decides what a piece *becomes*). Implementations are **parameterized, not per-piece**: `SlidingRule(directions)` covers rook/bishop/queen, `LeapingRule(offsets)` covers knight/king, `CombinedRule` unions patterns, `PawnRule(promotes_to)` is the one special case. `PieceRuleRegistry.rule_for(kind)` is the lookup; it is built from config, never a module global.
  - `rule_factory.py` — builds the rules from `[[pieces]]` specs. `MOVEMENT_BUILDERS` maps a spec's `movement` name to a builder: **a new piece with an existing pattern is config only; a genuinely new pattern is one `PieceRule` subclass + one entry here, and nothing outside `rules/`.**
  - `rule_set.py` — `ChessRuleSet`, the single facade: `legal_destinations`, `validate_move`, `flies_over(piece)`, and the three "what does this meeting mean" answers, all returned as data: **`resolve_arrival(ArrivalContext)`** (the §1 arrival table — empty/enemy/friend, protection eats the arriver friend-or-foe, the knight is the only piece that may take a friend, promotion, victory), **`resolve_block(BlockContext)`** (§2 mid-path: capture-and-stop / stop-before / cancel / redirect-onto-a-protected-piece), and **`resolve_cross(CrossContext)`** (§3 two movers meet: the first-started survives, a later friend cancels). A `CollisionResolution` is `(effects, adjustment)`; the arbiter applies the effects and retargets the motion.
  - `rule_engine.py` — `RuleEngine.validate_move(board, source, destination) -> MoveValidation(is_valid, reason)`, read-only, registry injected. Reasons: `ok`, `outside_board`, `empty_source`, `friendly_destination`, `illegal_piece_move`.
- **`realtime/`** — the model of **time**, and it holds **no chess whatsoever** (no `PieceKind`, no king, no promotion, no capture logic — the boundary test asserts this). `motion.py`: `Motion` + `cell_distance` (Chebyshev — **diagonal steps cost one cell**: 1 diagonal square = 1000 ms, 3 = 3000 ms); `Motion.progress(now)` (0..1) and the read-only `MotionView` exist purely so a renderer can interpolate a gliding piece without touching the clock. `real_time_arbiter.py`: `RealTimeArbiter(rules, effect_applier, ms_per_cell, jump_duration_ms, long_rest_ms, short_rest_ms, collision_resolver)` owns **many** in-flight motions at once (real-time, no turns) plus every piece's **timed lifecycle** (jump→short_rest→idle, and a move's arrival→long_rest→idle), all **outside `Board`**. **Logical board rule:** a moving piece stays on its source cell until arrival, so `print board` is deterministic. `advance_time(ms)` (never real sleep) advances the clock, settles **collisions**, resolves arrivals, then ages every lifecycle; returns `AdvanceResult(game_over)`. Rest/protection windows are measured from the **arrival/jump timestamp**, not the tick-end clock, so one coarse tick still lands cooldowns at the right time. `_is_protected_on_arrival` compares `arrival_ms` to a piece's `protected_until` (end of jump+short_rest), keyed by the stable `piece.id` (a `Piece` is unhashable). `collision_resolver.py`: `CollisionResolver` owns the **geometry/timing** of a real-time board (each mover's current cell by progress, who started first) and asks the injected rules what a meeting means, then settles it by **retargeting the loser's `Motion` to arrive now** — so a collision opens no second mutation path. A knight (`flies_over`, asked of the rules) is skipped entirely.
- **`engine/game_engine.py`** — `GameEngine(game_state, arbiter, rules)`, the application-service layer and **public command boundary**. Orchestration only, all collaborators injected and duck-typed. `request_move` rejects `game_over` (before consulting rules), then **`piece_busy`** (the source piece is not `IDLE` — moving/jumping/resting), then delegates to `rules.validate_move` (copying its reason), else starts the motion → `ok`. **Moves are parallel**: the only per-move lock is that one per-piece busy check — many pieces move at once. `wait(ms)` delegates to `arbiter.advance_time` and sets `game_over` when the arbiter reports it — *which* event ends the game is a rules decision the engine never sees. `snapshot() -> GameSnapshot` wraps a `BoardSnapshot` and delegates every board question to it (no bounds arithmetic, no grid walking). `active_motions()`/`airborne_cells()` pass the arbiter's render windows through unchanged, so a view reads everything it needs through the engine boundary.
- **`input/`** — the click→command layer. `board_mapper.py`: `BoardMapper(cell_size).to_cell(x, y)` (`col = x // cell_size`, `row = y // cell_size`; any viewport/camera support lives here, never in the model). `controller.py`: `Controller(engine, mapper)` maps pixels and delegates — it decides no legality, never calls `Board.move_piece` or the rules, and reads bounds/occupancy via `GameEngine.snapshot()`. Click policy: first click ignores outside-board and empty-cell clicks, else selects; a second click on a **same-color piece switches the selection**; another **in-board** second click sends the move and clears the selection (legal or not); an **outside-board** second click cancels the selection.
- **`text_io/`** — the text I/O format layer (named `text_io`, not `io`, because `io/` would shadow the stdlib module). `token_codec.py`: **`TokenCodec` is the single source of truth for the `<color><symbol>` format**, and its symbol map is *injected* from the configured pieces — so a new piece brings its own token and nothing here changes. `piece_factory.py`: `PieceFactory` only assigns **unique stable ids** (it no longer knows about tokens). `board_parser.py`: `BoardParser(factory, codec).parse(text) -> Board` (raises `BoardParseError(ROW_WIDTH_MISMATCH|UNKNOWN_TOKEN)`). `board_printer.py`: `BoardPrinter(codec).to_text(view)` renders any `BoardView` via `rows()`. Parser + printer are "the conversion": with `model/board.py` they are the only things that would change if the board's representation did.
- **`texttests/`** — the text-driven surface. `script_parser.py`: `ScriptParser.parse(text) -> ParsedScript(board_text, commands)`. `commands.py`: the handlers (`pixel_command`, `duration_command`, `print_board_command`) and `UnknownCommandError`. `script_runner.py`: `ScriptRunner(commands)` dispatches each line through an **injected command table** — it knows no command by name, so adding one is a table entry, not an edit to its if/elif chain. Unknown command, or known command with arguments that do not fit → `ERROR: Unknown command '<line>'`.
- **`view/`** — the **OpenCV surface**, structured to the `final_plan.md` blueprint (State / Strategy / DI, a coordinator + focused renderers). Like every consumer it holds **no chess and no timing**: it reads the board via `GameEngine.snapshot()`/`pieces()`/`active_motions()`, sends input via the injected `Controller`, and draws. `view/` imports only `model` (the boundary test — now recursive over subpackages — enforces it); it never reads `config`.
  - `img.py` — the given cv2 primitive (load/resize/alpha-blend/put-text, plus `draw_rect`).
  - `sprites/` — **State + Strategy**. `sprite_state.py`: `SpriteState` (one clip: frames + its own clock; `current_frame`/`is_finished`/`next_state_when_finished`) and `AnimatedSprite` (holds one current state, swaps via the library — no `if/else` on state names; the engine's `PieceState` is authoritative each tick). `sprite_library.py`: `SpriteLibrary` owns the **on-disk asset layout** (`<symbol><suffix>/states/<state>/sprites/<n>.png` + `config.json`) exactly as `text_io` owns the token format; handed a resolved folder per `(kind, color)`, it caches frames and returns a **fresh** `SpriteState` per request (so per-piece clocks never collide).
  - `rendering/` — the **coordinator + renderer split** (final_plan §7.2a). `board_view.py`: `BoardView` draws nothing itself, just calls three collaborators in order. `board_renderer.py`: the background template (forced BGRA), a fresh copy per frame. `piece_renderer.py`: composites pieces, keeps a per-piece `AnimatedSprite` (keyed by piece id), **glides** in-flight pieces via `MotionView.progress` and maps `PieceState` → sprite-state folder (config-driven). `overlay_renderer.py`: selection highlight + game-over banner. `renderer.py`: the `Renderer` protocol + `InputEvent` (`CLICK`/`JUMP`/`QUIT`). `cv2_renderer.py`: the one concrete `Renderer` — a **resizable** window (`WINDOW_NORMAL`) whose clicks are scaled back to board pixels via `getWindowImageRect` (`scale_point`, unit-tested; fixed-size `WINDOW_AUTOSIZE` is the fallback).
  - `game_loop.py`: `GameLoop`, the real-time driver (visual sibling of `ScriptRunner`) — measures elapsed wall time, `engine.wait(dt)`, renders via `BoardView`, routes `Renderer` input events to `controller.handle_click`/`handle_jump`, quits on the QUIT event.
- **`composition/app_factory.py`** — the composition root. Builds the codec, parser, printer, rule set, arbiter (with the collision resolver), engine, controller and command table from a `GameConfig`, plus `build_gui_app` and its helpers `build_board_view`/`build_piece_folders`/`build_state_folders` — `build_piece_folders` is the **one place** the on-disk piece naming (`<symbol><suffix>`, e.g. `QW`/`KB`) is spelled out. **The swap point for everything**: a different rule set, time model, board or surface is a change here and nowhere else. Notably it contains *no list of pieces* — that comes from config.
- **`config.py` / `config.toml`** — `load(path=None) -> GameConfig` **returns an immutable value** (it does not populate module globals; a config is injected, not reached into). `GameConfig` holds `cell_size`, `ms_per_cell`, `jump_duration_ms`, `long_rest_ms`, `short_rest_ms`, `empty_token`, `pieces: tuple[PieceSpec]`, and `assets: AssetsConfig` (the GUI's `board_image`/`pieces_dir`/`default_board` paths — resolved absolute against the package — plus the `white_suffix`/`black_suffix` and `idle`/`move`/`jump` state-folder names, so re-skinning is config only). A `PieceSpec` is `name`/`symbol`/`movement`/`directions`/`offsets`/`promotes_to`/`victory_on_capture`/`flies_over` (the knight's collision exemption). **Add new tunables to `config.toml` and map them in `config.load`, never as literals in code.**
- **`main.py`** — `main(input_stream=None)` (stdin by default, injectable for tests). Reads the document, parses script + board (translating parse errors to `ERROR <code>` + `sys.exit(0)`), then hands off to the composition root.
- **`gui.py`** — `main(argv=None)`, the graphical entry point (`python -m kongfuchess.gui [board-file]`; with no argument it loads `assets.default_board`). Reads config, parses the board, and hands off to `app_factory.build_gui_app(...).run()`.

### Adding a piece

Add a `[[pieces]]` block to `config.toml` — `name`, `symbol`, a `movement` pattern (`slide` / `leap` / `combined` / `pawn`) and its `directions`/`offsets`, optionally `promotes_to`, `victory_on_capture`, and `flies_over` (exempt from collisions / may take a friend, like the knight). That is the whole change: no code in `model/`, `rules/`, `text_io/` or anywhere else. Only a movement *pattern* nobody has written yet needs code, and then only a `PieceRule` subclass plus a `MOVEMENT_BUILDERS` entry, both inside `rules/`. `tests/integration/test_custom_game.py` demonstrates this end to end with an invented piece.

For the piece to appear in the **GUI**, also add its sprite folders under `assets.pieces_dir`: `<symbol><white_suffix>/` and `<symbol><black_suffix>/` (e.g. `DW`/`DB` for a `symbol = "D"` dragon), each with `states/<idle|move|jump>/sprites/*.png` and a `config.json`. Still no code — `build_piece_folders` derives the folder name from the symbol.

### Conventions that bite

- **`Board` is indexed by `Position(row, col)`, but clicks are pixels `(x, y)`.** `BoardMapper` maps `col = x // cell_size`, `row = y // cell_size` — x→col, y→row. Getting this backwards is the classic bug.
- **Empty cells are `None`** (`board.piece_at(pos) is None`) — there is no Null-Object empty cell in the model.
- **Never walk the grid outside `model/`.** Use `board.pieces()` or `board.rows()`; `range(height) × range(width)` in any other layer is a board-representation leak and is what a binary board would break.
- **Values, not strings, in logic**: `Color.WHITE` / `PieceState.MOVING` are enums; `PieceKind` is a *value object* (`PieceKind("dragon")`) because the set of pieces must stay open. The single-char `w`/`b` + symbol exist only in text tokens, encoded/decoded by `text_io.token_codec`.
- **Nothing outside `composition/` imports `config`**, and no constructor has a default collaborator. If you find yourself reaching for one, inject it instead — `tests/test_layer_boundaries.py` will fail you otherwise.
- **Rules never mutate; `realtime/` never decides.** A rule returns `Effect`s and the arbiter applies them. If you are about to write `if piece.kind == ...` outside `rules/`, stop.
- **Still missing vs. full Kung-Fu-Chess**: no scoring, no networking, no moves-log/score panels. (Parallel real-time moves, post-move **cooldown** (long-rest) and post-jump short-rest, the **collision model** (§1 arrival table / §2 mid-path / §3 two-movers, knight exempt), jump/dodge, pawn two-step, promotion, and the **OpenCV GUI** with gliding pieces **are** implemented.)
- **Moves are parallel; the only lock is per-piece busy.** `GameEngine.request_move` rejects `piece_busy` when the source piece is not `IDLE` (moving/jumping/resting) — many *different* pieces move at once. There is no global one-motion lock any more. A **jump** does not lock the board and can coexist with an incoming enemy move (that's what makes a dodge possible).
- **Collisions: `realtime/` sees the geometry, `rules/` says what it means.** The `CollisionResolver` computes where each mover is and who started first, then asks `rules.resolve_block`/`resolve_cross` and settles by retargeting a `Motion`. If you are tempted to put "eat vs. stop" or a kind check in `realtime/`, stop — it goes in `rules/`, and the knight's exemption is the `flies_over` config flag asked via `rules.flies_over(piece)`.

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
