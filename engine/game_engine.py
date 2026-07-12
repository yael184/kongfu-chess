# engine/game_engine.py
from dataclasses import dataclass

from model.position import Position
from rules.rule_engine import RuleEngine

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
    """Read-only view of the game exposed to the renderer and BoardPrinter.

    It captures the piece placements at snapshot time, so later board mutations do not change
    which cells it reports as occupied. It offers no mutation of the board or pieces.
    """

    def __init__(self, width, height, placements, game_over):
        self._width = width
        self._height = height
        self._placements = dict(placements)  # Position -> Piece, copied at snapshot time
        self._game_over = game_over

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def game_over(self):
        return self._game_over

    def is_within_bounds(self, position):
        return 0 <= position.row < self._height and 0 <= position.col < self._width

    def piece_at(self, position):
        return self._placements.get(position)


class GameEngine:
    """Application-service layer and public command boundary (for Controller and TextTestRunner).

    It orchestrates only: it enforces the application-level guards (game over, an active motion
    in the common route), delegates legality to RuleEngine, starts motions and advances time
    through the RealTimeArbiter, sets game_over when a king capture is reported, and exposes a
    read-only snapshot. It holds no piece-specific movement logic, rendering code, pixel mapping,
    text parsing, or test-runner logic.

    Collaborators are injected. The arbiter is expected to provide:
      - has_active_motion() -> bool
      - start_motion(board, source, destination)
      - advance_time(ms) -> outcome, where outcome exposes a boolean `king_captured`
    """

    def __init__(self, game_state, arbiter, rule_engine=None):
        self._state = game_state
        self._arbiter = arbiter
        self._rules = rule_engine if rule_engine is not None else RuleEngine()

    def request_move(self, source, destination):
        """Validate and, if accepted, start a move. Application guards run before RuleEngine."""
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
        """Advance simulated time through the arbiter, flipping game_over on a king capture."""
        outcome = self._arbiter.advance_time(ms)
        if getattr(outcome, "king_captured", False):
            self._state.game_over = True
        return outcome

    def snapshot(self):
        """Return a read-only GameSnapshot of the current board and game-over flag."""
        board = self._state.board
        placements = {}
        for row in range(board.height):
            for col in range(board.width):
                position = Position(row, col)
                piece = board.piece_at(position)
                if piece is not None:
                    placements[position] = piece
        return GameSnapshot(board.width, board.height, placements, self._state.game_over)
