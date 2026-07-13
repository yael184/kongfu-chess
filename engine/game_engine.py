# engine/game_engine.py
from dataclasses import dataclass

# Application-level MoveResult reasons. Rule-level reasons are copied from MoveValidation.
REASON_OK = "ok"
REASON_GAME_OVER = "game_over"
REASON_MOTION_IN_PROGRESS = "motion_in_progress"


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

    It orchestrates only: it enforces the application-level guards (game over, an active motion in
    the common route), delegates legality to the rules, starts motions and advances time through the
    arbiter, sets game_over when the arbiter reports the game has ended, and exposes a read-only
    snapshot. It holds no piece-specific movement logic, rendering code, pixel mapping, text
    parsing, or test-runner logic — and no opinion on what ends a game.

    Every collaborator is injected — the engine names no concrete class, so it is unaware of which
    rules are in play and which time model is running. Only composition/app_factory decides that.

    The arbiter is expected to provide:
      - has_active_motion() -> bool
      - start_motion(board, source, destination)
      - request_jump(board, cell)
      - advance_time(ms) -> outcome, where outcome exposes a boolean `game_over`
    The rules collaborator is expected to provide:
      - validate_move(board, source, destination) -> a result with `is_valid` and `reason`
    """

    def __init__(self, game_state, arbiter, rules):
        self._state = game_state
        self._arbiter = arbiter
        self._rules = rules

    def request_move(self, source, destination):
        """Validate and, if accepted, start a move. Application guards run before the rules."""
        if self._state.game_over:
            return MoveResult.rejected(REASON_GAME_OVER)
        if self._arbiter.has_active_motion():
            return MoveResult.rejected(REASON_MOTION_IN_PROGRESS)

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

    def snapshot(self):
        """Return a read-only GameSnapshot of the current board and game-over flag."""
        return GameSnapshot(self._state.board.snapshot(), self._state.game_over)
