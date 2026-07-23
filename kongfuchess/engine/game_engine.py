# engine/game_engine.py
from dataclasses import dataclass

from kongfuchess.model.piece import PieceState

# Application-level MoveResult reasons. Rule-level reasons are copied from MoveValidation.
REASON_OK = "ok"
REASON_GAME_OVER = "game_over"
REASON_PIECE_BUSY = "piece_busy"


@dataclass(frozen=True)
class MoveResult:
    """Outcome of a request_move command. `reason` is always present ("ok" when accepted)."""
    is_accepted: bool
    reason: str

    @classmethod
    def accepted(cls):
        return cls(True, REASON_OK)

    @classmethod
    def rejected(cls, reason):
        return cls(False, reason)


class GameSnapshot:
    """Read-only view of the game exposed to the renderer and BoardPrinter: an immutable board
    view plus the game-over flag.

    It is a BoardView itself, delegating every board question to the snapshot it wraps. It knows
    nothing about how the board is laid out or stored — no bounds arithmetic, no grid walking —
    so a different board representation reaches the printer and the renderer unchanged.
    """

    def __init__(self, board_view, game_over):
        self._board = board_view
        self._game_over = game_over

    @property
    def width(self):
        return self._board.width

    @property
    def height(self):
        return self._board.height

    @property
    def game_over(self):
        return self._game_over

    def is_within_bounds(self, position):
        return self._board.is_within_bounds(position)

    def piece_at(self, position):
        return self._board.piece_at(position)

    def pieces(self):
        return self._board.pieces()

    def rows(self):
        return self._board.rows()


class GameEngine:
    """Application-service layer and public command boundary (for Controller and TextTestRunner).

    It orchestrates only: it enforces the application-level guards (game over, and that the moved
    piece is IDLE rather than busy), delegates legality to the rules, starts motions and advances
    time through the arbiter, sets game_over when the arbiter reports the game has ended, and exposes
    a read-only snapshot. It holds no piece-specific movement logic, rendering code, pixel mapping,
    text parsing, or test-runner logic — and no opinion on what ends a game.

    Every collaborator is injected — the engine names no concrete class, so it is unaware of which
    rules are in play and which time model is running. Only composition/app_factory decides that.

    The arbiter is expected to provide:
      - has_active_motion() -> bool
      - start_motion(board, source, destination)
      - request_jump(board, cell)
      - advance_time(ms) -> outcome, where outcome exposes a boolean `game_over`
      - active_motions() -> read-only motion views; airborne_cells() -> cells (for a renderer)
      - rest_windows() -> read-only cooldown views (for a renderer)
    The rules collaborator is expected to provide:
      - validate_move(board, source, destination) -> a result with `is_valid` and `reason`
      - legal_destinations(board, piece) -> the cells that piece may move to
    """

    def __init__(self, game_state, arbiter, rules):
        self._state = game_state
        self._arbiter = arbiter
        self._rules = rules

    def request_move(self, source, destination):
        """Validate and, if accepted, start a move. Application guards run before the rules.

        Moves are real-time and parallel: any number of pieces may be in flight at once. The only
        per-move gate is that the source piece must be IDLE — a piece already moving, jumping, or
        resting is busy and cannot be commanded again until it settles.
        """
        if self._state.game_over:
            return MoveResult.rejected(REASON_GAME_OVER)

        piece = self._state.board.piece_at(source)
        if piece is not None and piece.state is not PieceState.IDLE:
            return MoveResult.rejected(REASON_PIECE_BUSY)

        validation = self._rules.validate_move(self._state.board, source, destination)
        if not validation.is_valid:
            return MoveResult.rejected(validation.reason)

        self._arbiter.start_motion(self._state.board, source, destination)
        return MoveResult.accepted()

    def request_jump(self, cell):
        """Make the piece on `cell` jump in place (a dodge). Ignored once the game is over."""
        if self._state.game_over:
            return
        self._arbiter.request_jump(self._state.board, cell)

    def wait(self, ms):
        """Advance simulated time through the arbiter, flipping game_over when it reports the end.

        *Which* event ends the game is a rules decision the engine never sees; it only records the
        verdict the arbiter passes back.
        """
        outcome = self._arbiter.advance_time(ms)
        if outcome.game_over:
            self._state.game_over = True
        return outcome

    def active_motions(self):
        """Read-only views of the moves currently in flight, for a renderer to interpolate.

        The board snapshot shows a moving piece on its source cell (the logical-board rule); this
        is the extra fact a real-time view needs to draw it gliding. Empty for a turn-based arbiter.
        """
        return self._arbiter.active_motions()

    def rest_windows(self):
        """Read-only views of the cooldowns running right now, for a renderer to draw a countdown.

        The board snapshot says a piece is LONG_REST but not *how much longer*; this is that extra
        fact. Empty for an arbiter without cooldowns.
        """
        return self._arbiter.rest_windows()

    def legal_destinations(self, cell):
        """Every cell the piece on `cell` may move to, for a view to highlight. Empty for an empty
        cell, so a caller may pass whatever the user selected.

        A pure rules question, asked and passed straight through: the engine adds no opinion of its
        own, and its own guards (game over, piece busy) belong to request_move, not to this.
        """
        piece = self._state.board.piece_at(cell) if cell is not None else None
        if piece is None:
            return ()
        return tuple(self._rules.legal_destinations(self._state.board, piece))

    def airborne_cells(self):
        """The cells whose piece is mid-jump right now, for a renderer to animate the dodge."""
        return self._arbiter.airborne_cells()

    def game_time_ms(self):
        """The authoritative server clock in ms, passed straight through from the arbiter. A move is
        stamped with this so the panel can show when it happened; it is the same 'now' collisions are
        ordered by. The engine reads it, it does not keep its own clock."""
        return self._arbiter.now_ms

    def snapshot(self):
        """Return a read-only GameSnapshot of the current board and game-over flag."""
        return GameSnapshot(self._state.board.snapshot(), self._state.game_over)
