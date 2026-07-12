# rules/rule_engine.py
from dataclasses import dataclass

from rules.piece_rules import rule_for

# Stable, machine-readable validation reasons (asserted by unit tests, not by the DSL).
REASON_OK = "ok"
REASON_OUTSIDE_BOARD = "outside_board"
REASON_EMPTY_SOURCE = "empty_source"
REASON_FRIENDLY_DESTINATION = "friendly_destination"
REASON_ILLEGAL_PIECE_MOVE = "illegal_piece_move"


@dataclass(frozen=True)
class MoveValidation:
    """Result of a rule-level check. `reason` is always present ("ok" when valid)."""
    is_valid: bool
    reason: str

    @classmethod
    def ok(cls):
        return cls(True, REASON_OK)

    @classmethod
    def rejected(cls, reason):
        return cls(False, reason)


class RuleEngine:
    """Read-only rule validator: given a source and destination cell, is the move legal now?

    It inspects board state and returns a MoveValidation; it never moves pieces, removes
    captures, starts motions, or updates game state. Game-over is handled by GameEngine, not here.
    """

    def validate_move(self, board, source, destination):
        """Validate a move from source to destination against the board and piece movement rules."""
        if not board.is_within_bounds(source) or not board.is_within_bounds(destination):
            return MoveValidation.rejected(REASON_OUTSIDE_BOARD)

        piece = board.piece_at(source)
        if piece is None:
            return MoveValidation.rejected(REASON_EMPTY_SOURCE)

        target = board.piece_at(destination)
        if target is not None and target.color == piece.color:
            return MoveValidation.rejected(REASON_FRIENDLY_DESTINATION)

        if destination not in rule_for(piece.kind).legal_destinations(board, piece):
            return MoveValidation.rejected(REASON_ILLEGAL_PIECE_MOVE)

        return MoveValidation.ok()
