# model/board.py
from model.piece import Piece
from model.position import Position


class DuplicateOccupancyError(Exception):
    """Raised when a piece would be placed on an already-occupied cell."""


class OutOfBoundsError(Exception):
    """Raised when a cell lies outside the board."""


class PieceNotFoundError(Exception):
    """Raised when an expected piece is not on the board."""


class _GridBoard:
    """The single place that knows a board is a rectangular grid of cells.

    It implements the read-only BoardView port over a Position -> Piece mapping. Both the live
    Board and the immutable BoardSnapshot inherit it, so the bounds check and the row layout are
    written once. Swapping the internal representation (a bitboard, a packed byte array) means
    rewriting this class and nothing above it.
    """

    def __init__(self, width: int, height: int, pieces_by_cell):
        self._width = width
        self._height = height
        self._pieces_by_cell = pieces_by_cell  # Position -> Piece

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def is_within_bounds(self, position: Position) -> bool:
        return 0 <= position.row < self._height and 0 <= position.col < self._width

    def piece_at(self, position: Position):
        """Return the piece on the given cell, or None if the cell is empty."""
        return self._pieces_by_cell.get(position)

    def pieces(self):
        """Every piece on the board — no geometry assumed, so callers need not walk the grid."""
        return tuple(self._pieces_by_cell.values())

    def rows(self):
        """The cells row by row, left to right, with None for an empty cell."""
        return tuple(
            tuple(self.piece_at(Position(row, col)) for col in range(self._width))
            for row in range(self._height)
        )


class BoardSnapshot(_GridBoard):
    """An immutable point-in-time copy of a board, safe to hand to a renderer or printer.

    Later board mutations do not change which cells it reports as occupied, and it offers no
    mutation of its own.
    """


class Board(_GridBoard):
    """Owns the logical arrangement of pieces: what exists and where.

    It adds/removes/queries pieces, checks bounds, and moves a piece once a move has already been
    validated elsewhere. It contains no chess movement rules and never decides which moves are
    legal — that is the rules/ layer's job. move_piece assumes validation has already happened;
    it only preserves the structural invariant of at most one piece per cell.
    """

    def __init__(self, width: int, height: int):
        super().__init__(width, height, {})

    def snapshot(self) -> BoardSnapshot:
        """An immutable copy of the current placements, decoupled from later mutations."""
        return BoardSnapshot(self._width, self._height, dict(self._pieces_by_cell))

    def add_piece(self, piece: Piece):
        """Place a piece on its own cell, rejecting out-of-bounds cells and duplicate occupancy."""
        self._require_within_bounds(piece.cell)
        if piece.cell in self._pieces_by_cell:
            raise DuplicateOccupancyError(piece.cell)
        self._pieces_by_cell[piece.cell] = piece

    def remove_piece(self, piece: Piece):
        """Remove a piece from the board, clearing its cell."""
        if self._pieces_by_cell.get(piece.cell) is not piece:
            raise PieceNotFoundError(piece)
        del self._pieces_by_cell[piece.cell]

    def move_piece(self, source: Position, destination: Position):
        """Move the piece at source to an empty destination (validation assumed to have happened)."""
        self._require_within_bounds(destination)
        piece = self._pieces_by_cell.get(source)
        if piece is None:
            raise PieceNotFoundError(source)
        if destination in self._pieces_by_cell:
            raise DuplicateOccupancyError(destination)
        del self._pieces_by_cell[source]
        piece.cell = destination
        self._pieces_by_cell[destination] = piece

    def _require_within_bounds(self, position: Position):
        if not self.is_within_bounds(position):
            raise OutOfBoundsError(position)
