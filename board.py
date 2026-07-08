# board.py
from pieces import Piece

class Board:
    def __init__(self, grid):
        self.grid = grid  # יכיל אובייקטים של Piece או "."
        self.selected_piece = None

    def is_within_bounds(self, row, col):
        return 0 <= row < len(self.grid) and 0 <= col < len(self.grid[0])

    def get_cell(self, row, col):
        if self.is_within_bounds(row, col):
            return self.grid[row][col]
        return None

    def is_empty(self, row, col):
        cell = self.get_cell(row, col)
        return isinstance(cell, Piece) and cell.color is None

    def get_piece_color(self, row, col):
        """מחזירה את צבע הכלי ישירות מתוך האובייקט."""
        cell = self.get_cell(row, col)
        if isinstance(cell, Piece):
            return cell.color
        return None

    def select_piece(self, row, col):
        self.selected_piece = (row, col)

    def move_piece(self, from_row, from_col, to_row, to_col):
        moving_piece = self.grid[from_row][from_col]
        self.grid[to_row][to_col] = moving_piece
        self.grid[from_row][from_col] = "."
        self.selected_piece = None

    def __str__(self):
        # קורא ל-__str__ של כל כלי או משאיר "."
        return "\n".join(" ".join(str(cell) for cell in row) for row in self.grid)