# realtime/motion.py
from dataclasses import dataclass

from kongfuchess.model.piece import Piece
from kongfuchess.model.position import Position


def cell_distance(source: Position, destination: Position) -> int:
    """Chebyshev distance in cells. Diagonal steps count as one cell (cell-step duration),
    so a diagonal move costs the same per square as an orthogonal one, not the Euclidean length."""
    return max(abs(destination.row - source.row), abs(destination.col - source.col))


@dataclass
class Motion:
    """A single move in flight. It records where the piece came from, where it is going, and
    when it started/arrives. It does not touch the board — the board changes only on arrival,
    resolved by RealTimeArbiter. The renderer can interpolate a pixel position between the cells.
    """
    piece: Piece
    source: Position
    destination: Position
    start_ms: int
    arrival_ms: int

    @classmethod
    def start(cls, piece: Piece, destination: Position, now_ms: int, ms_per_cell: int) -> "Motion":
        """Create a motion for `piece` toward `destination`, arriving after cells * ms_per_cell."""
        source = piece.cell
        duration = cell_distance(source, destination) * ms_per_cell
        return cls(piece, source, destination, now_ms, now_ms + duration)

    def has_arrived(self, now_ms: int) -> bool:
        return now_ms >= self.arrival_ms

    def progress(self, now_ms: int) -> float:
        """How far along the trip the piece is, in [0, 1] — 0 at the source, 1 at the destination.

        A renderer interpolates the pixel position between the two cells with this. A zero-length
        trip (already there) is fully arrived.
        """
        span = self.arrival_ms - self.start_ms
        if span <= 0:
            return 1.0
        return min(1.0, max(0.0, (now_ms - self.start_ms) / span))


@dataclass(frozen=True)
class MotionView:
    """A read-only view of an in-flight motion for rendering: which piece, from where to where,
    and how far along (0..1). Carries no timing internals — the arbiter has already sampled the
    clock — so a renderer never touches the clock or the live Motion.
    """
    piece: Piece
    source: Position
    destination: Position
    progress: float


@dataclass(frozen=True)
class RestView:
    """A read-only view of a piece's cooldown for rendering: which cell is resting and how much of
    the wait is left (`remaining`, 1.0 the instant it starts and 0.0 as it ends).

    The sibling of MotionView for the *other* thing time does to a piece. A renderer draws a
    countdown from it — a draining square — without touching the clock or the live phase. It is
    pure timing: nothing here knows why the piece is waiting, only that it is.
    """
    cell: Position
    remaining: float
