# model/effects.py
from dataclasses import dataclass

from kongfuchess.model.piece import Piece, PieceKind, PieceState
from kongfuchess.model.position import Position


class Effect:
    """One atomic change to the game, described rather than performed.

    Effects are the vocabulary the rules layer answers in: a rule decides *what should happen*
    and returns effects; whoever holds the board applies them. That is the seam that keeps the
    rules pure (they never mutate) and keeps the layers that own timing and board state ignorant
    of chess (they never decide). Adding a new kind of consequence means adding an Effect
    subclass — never an `if` in a caller.
    """

    def apply(self, board) -> bool:
        """Apply this effect to a MutableBoard. Returns True if it ended the game."""
        raise NotImplementedError


@dataclass(frozen=True)
class RemovePiece(Effect):
    """Take a piece off the board (a capture)."""
    piece: Piece

    def apply(self, board) -> bool:
        board.remove_piece(self.piece)
        self.piece.state = PieceState.CAPTURED
        return False


@dataclass(frozen=True)
class MovePiece(Effect):
    """Relocate a piece to a cell that is empty by the time this is applied."""
    piece: Piece
    destination: Position

    def apply(self, board) -> bool:
        board.move_piece(self.piece.cell, self.destination)
        self.piece.state = PieceState.IDLE
        return False


@dataclass(frozen=True)
class TransformPiece(Effect):
    """Change a piece's kind in place (a promotion, or any variant's equivalent)."""
    piece: Piece
    kind: PieceKind

    def apply(self, board) -> bool:
        self.piece.kind = self.kind
        return False


@dataclass(frozen=True)
class EndGame(Effect):
    """The game is decided. Which capture (if any) decides it is a rules question, not this one."""

    def apply(self, board) -> bool:
        return True


class EffectApplier:
    """Applies a rule's effects to a board, in order, and reports whether the game ended.

    It is deliberately dumb: it dispatches to the effects themselves and holds no knowledge of
    what any of them mean.
    """

    def apply(self, board, effects) -> bool:
        """Apply every effect; returns True if any of them ended the game."""
        game_over = False
        for effect in effects:
            if effect.apply(board):
                game_over = True
        return game_over
