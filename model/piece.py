# model/piece.py
import enum
from dataclasses import dataclass

from model.position import Position


class Color(enum.Enum):
    """A piece's side."""
    WHITE = "white"
    BLACK = "black"


class PieceKind(enum.Enum):
    """The type of chess piece. Movement rules for each kind live in the rules/ layer, not here."""
    KING = "king"
    QUEEN = "queen"
    ROOK = "rook"
    BISHOP = "bishop"
    KNIGHT = "knight"
    PAWN = "pawn"


class PieceState(enum.Enum):
    """A piece's lifecycle flag — nothing more.

    It does not store path, destination, elapsed time, speed, interpolation, or arrival logic;
    those belong to Motion and RealTimeArbiter.
    """
    IDLE = "idle"
    MOVING = "moving"
    CAPTURED = "captured"


@dataclass
class Piece:
    """A chess piece identified by a stable, unique id.

    `cell` and `state` are the only mutable aspects: the board updates `cell` when the piece
    moves, and the real-time layer flips `state` between idle/moving/captured. A piece never
    knows about the renderer, mouse clicks, pixels, or text-test syntax.

    Ids are assigned consistently at creation time (by BoardParser or a dedicated PieceFactory);
    when identity is used for motion tracking or snapshots, duplicate ids are invalid.
    """
    id: object
    color: Color
    kind: PieceKind
    cell: Position
    state: PieceState = PieceState.IDLE
