# pieces.py
import config

class Piece:
    """Base class for every piece type. Subclasses encode only the shape rules of a move."""

    def __init__(self, color: str, symbol: str):
        self.color = color      # config.COLOR_WHITE / config.COLOR_BLACK, or None for an empty cell.
        self.symbol = symbol    # "K", "R", "B", "Q", "N", or "." for an empty cell.

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int, board) -> bool:
        """Return True if the move is legal for this piece's shape and the current board state."""
        raise NotImplementedError

    def promoted_piece(self, to_row: int, board):
        """The piece this one becomes upon reaching to_row, or None if no promotion applies.
        Default: no promotion. Only Pawn overrides this (promotes to a Queen on the last row)."""
        return None

    def _is_path_clear(self, from_row: int, from_col: int, to_row: int, to_col: int, board) -> bool:
        """Helper that scans the route and verifies there are no blocking pieces in between."""
        row_step = 0 if from_row == to_row else (1 if to_row > from_row else -1)
        col_step = 0 if from_col == to_col else (1 if to_col > from_col else -1)

        current_row = from_row + row_step
        current_col = from_col + col_step

        while current_row != to_row or current_col != to_col:
            if not board.is_empty(current_row, current_col):
                return False  # A blocking piece was found on the route.
            current_row += row_step
            current_col += col_step
        return True

    def __str__(self):
        if self.color is None:
            return self.symbol
        prefix = "w" if self.color == config.COLOR_WHITE else "b"
        return f"{prefix}{self.symbol}"


class EmptyCell(Piece):
    """Null Object for an empty cell, so the grid is never None and callers never special-case empties."""

    def __init__(self):
        super().__init__(color=None, symbol=".")

    def is_valid_move(self, from_row, from_col, to_row, to_col, board) -> bool:
        return False


class King(Piece):
    def __init__(self, color: str):
        super().__init__(color, "K")

    def is_valid_move(self, from_row, from_col, to_row, to_col, board) -> bool:
        return max(abs(to_row - from_row), abs(to_col - from_col)) == 1


class Rook(Piece):
    def __init__(self, color: str):
        super().__init__(color, "R")

    def is_valid_move(self, from_row, from_col, to_row, to_col, board) -> bool:
        if from_row != to_row and from_col != to_col:
            return False
        return self._is_path_clear(from_row, from_col, to_row, to_col, board)


class Bishop(Piece):
    def __init__(self, color: str):
        super().__init__(color, "B")

    def is_valid_move(self, from_row, from_col, to_row, to_col, board) -> bool:
        if abs(to_row - from_row) != abs(to_col - from_col):
            return False
        return self._is_path_clear(from_row, from_col, to_row, to_col, board)


class Queen(Piece):
    def __init__(self, color: str):
        super().__init__(color, "Q")

    def is_valid_move(self, from_row, from_col, to_row, to_col, board) -> bool:
        is_diagonal = abs(to_row - from_row) == abs(to_col - from_col)
        is_straight = (from_row == to_row or from_col == to_col)
        if not (is_diagonal or is_straight):
            return False
        return self._is_path_clear(from_row, from_col, to_row, to_col, board)


class Knight(Piece):
    def __init__(self, color: str):
        super().__init__(color, "N")

    def is_valid_move(self, from_row, from_col, to_row, to_col, board) -> bool:
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        return (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)

class Pawn(Piece):
    def __init__(self, color: str):
        super().__init__(color, "P")

    def _forward(self) -> int:
        # White moves up (row - 1), black moves down (row + 1).
        return -1 if self.color == config.COLOR_WHITE else 1

    def _start_row(self, board) -> int:
        # The start row is each color's home edge (the edge it advances from):
        # white moves up, so it starts on the last row; black moves down and starts on row 0.
        return len(board.grid) - 1 if self.color == config.COLOR_WHITE else 0

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int, board) -> bool:
        direction = self._forward()
        row_diff = to_row - from_row
        col_diff = abs(to_col - from_col)

        # 1. Straight forward one step; the destination must be empty (no capturing straight ahead).
        if col_diff == 0 and row_diff == direction:
            return board.is_empty(to_row, to_col)

        # 2. Two-cell first move from the start row: both the middle cell and the destination must be empty.
        if col_diff == 0 and row_diff == 2 * direction and from_row == self._start_row(board):
            middle_row = from_row + direction
            return board.is_empty(middle_row, to_col) and board.is_empty(to_row, to_col)

        # 3. Diagonal capture: one step forward and one sideways; the destination must hold a piece.
        if col_diff == 1 and row_diff == direction:
            return not board.is_empty(to_row, to_col)

        # Any other move is illegal.
        return False

    def promoted_piece(self, to_row: int, board):
        # Promotion: a pawn reaching the last row in its direction of travel becomes a Queen.
        last_row = 0 if self.color == config.COLOR_WHITE else len(board.grid) - 1
        if to_row == last_row:
            return Queen(self.color)
        return None