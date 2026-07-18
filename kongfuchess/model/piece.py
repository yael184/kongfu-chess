# model/piece.py
import enum
from dataclasses import dataclass

from kongfuchess.model.position import Position


class Color(enum.Enum):
    """A piece's side."""
    WHITE = "white"
    BLACK = "black"


@dataclass(frozen=True)
class PieceKind:
    """The type of a piece — a value object, deliberately *not* an enum.

    An enum is a closed set, and a closed set here would mean the model gets an edit every time
    someone invents a piece. A kind is just a name: `PieceKind("dragon")` is as valid as the six
    below, and compares and hashes by value like any other. Which kinds actually exist in a game is
    decided by configuration and assembled at the composition root, not fixed here.

    Movement rules for each kind live in the rules/ layer; the model never knows how anything moves.
    """
    name: str

    def __str__(self):
        return self.name


# The standard chess kinds, as a convenience for code and tests that mean the usual game.
# This is emphatically NOT an exhaustive list — it is six well-known values, not the vocabulary.
PieceKind.KING = PieceKind("king")
PieceKind.QUEEN = PieceKind("queen")
PieceKind.ROOK = PieceKind("rook")
PieceKind.BISHOP = PieceKind("bishop")
PieceKind.KNIGHT = PieceKind("knight")
PieceKind.PAWN = PieceKind("pawn")


class PieceState(enum.Enum):
    """A piece's lifecycle flag — nothing more.

    It does not store path, destination, elapsed time, speed, interpolation, or arrival logic;
    those belong to Motion and RealTimeArbiter. The rest/jump states are still pure lifecycle:
    they say *what phase* a piece is in (acting, cooling down), never for how long or along which
    path — the arbiter owns the timers. A piece in JUMPING or SHORT_REST protects its cell; a piece
    in any state other than IDLE is busy and cannot be commanded.
    """
    IDLE = "idle"
    MOVING = "moving"
    JUMPING = "jumping"
    SHORT_REST = "short_rest"
    LONG_REST = "long_rest"
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

    def is_ally_of(self, other) -> bool:
        """Whether `other` is a piece on the same side. An empty cell (None) is never an ally."""
        return other is not None and other.color == self.color

    def is_enemy_of(self, other) -> bool:
        """Whether `other` is a piece on the opposing side. An empty cell (None) is never an enemy."""
        return other is not None and other.color != self.color
