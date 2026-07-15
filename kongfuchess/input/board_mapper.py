# input/board_mapper.py
from kongfuchess.model.position import Position


class BoardMapper:
    """Maps pixel coordinates to board cells.

    In the common route there is no scrolling camera: pixels map directly to cells,
    col = x // cell_size and row = y // cell_size. Any viewport/scroll support belongs here,
    never in the model. Whether a mapped cell is inside the board is a Board concern.
    """

    def __init__(self, cell_size: int):
        self._cell_size = cell_size

    def to_cell(self, x: int, y: int) -> Position:
        """Convert pixel (x, y) to a board Position (x -> col, y -> row)."""
        return Position(y // self._cell_size, x // self._cell_size)
