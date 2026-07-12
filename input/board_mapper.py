# input/board_mapper.py
import config

from model.position import Position


class BoardMapper:
    """Maps pixel coordinates to board cells.

    In the common route there is no scrolling camera: pixels map directly to cells,
    col = x // CELL_SIZE and row = y // CELL_SIZE. Any viewport/scroll support belongs here,
    never in the model. Whether a mapped cell is inside the board is a Board concern.
    """

    def __init__(self, cell_size=None):
        self._cell_size = cell_size if cell_size is not None else config.CELL_SIZE

    def to_cell(self, x: int, y: int) -> Position:
        """Convert pixel (x, y) to a board Position (x -> col, y -> row)."""
        return Position(y // self._cell_size, x // self._cell_size)
