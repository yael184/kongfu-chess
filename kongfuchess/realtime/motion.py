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
