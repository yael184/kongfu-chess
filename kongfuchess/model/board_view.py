# model/board_view.py
from typing import Iterable, Optional, Protocol, Sequence

from kongfuchess.model.piece import Piece
from kongfuchess.model.position import Position


class BoardView(Protocol):
    """Read-only access to a board — the abstraction every layer above the model depends on.

    Nothing outside model/ may touch a board's internal data structure, and nothing outside
    model/ may rebuild the grid itself (the `range(height) x range(width)` loop): `pieces()`
    and `rows()` exist so callers never have to. That is what keeps a future switch to a binary
    representation contained inside model/ — an implementation only has to keep answering these
    questions, however it stores things internally.
    """

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...

    def is_within_bounds(self, position: Position) -> bool:
        """Whether the cell lies on this board."""

    def piece_at(self, position: Position) -> Optional[Piece]:
        """The piece on the cell, or None if the cell is empty."""

    def pieces(self) -> Iterable[Piece]:
        """Every piece on the board, in no guaranteed order and assuming no geometry."""

    def rows(self) -> Iterable[Sequence[Optional[Piece]]]:
        """The cells row by row (each row left to right), empty cells as None.

        The only shape-aware view; it exists for renderers and the text format, which have to
        lay the board out in two dimensions.
        """


class MutableBoard(BoardView, Protocol):
    """A board that can also be changed. Mutation is only ever performed on already-validated
    commands: the board preserves its structural invariants (bounds, one piece per cell) but
    decides no movement legality — that is the rules/ layer's job.
    """

    def add_piece(self, piece: Piece) -> None: ...

    def remove_piece(self, piece: Piece) -> None: ...

    def move_piece(self, source: Position, destination: Position) -> None: ...
