# board.py
from pieces import Piece, EmptyCell

class Board:
    def __init__(self, grid):
        self.grid = grid  # מטריצה שמכילה אך ורק אובייקטים מסוג Piece (כולל EmptyCell)
        self.selected_piece = None

    def is_within_bounds(self, row, col):
        return 0 <= row < len(self.grid) and 0 <= col < len(self.grid[0])

    def get_cell(self, row, col):
        if self.is_within_bounds(row, col):
            return self.grid[row][col]
        return EmptyCell()  # הגנה מפני חריגה: מחזיר אובייקט תא ריק

    def is_empty(self, row, col):
        return isinstance(self.get_cell(row, col), EmptyCell)

    def get_piece_color(self, row, col):
        cell = self.get_cell(row, col)
        if isinstance(cell, Piece):
            return cell.color
        return None

    def set_cell(self, row, col, piece):
        self.grid[row][col] = piece

    def select_piece(self, row, col):
        self.selected_piece = (row, col)

    def move_piece(self, from_row, from_col, to_row, to_col):
        moving_piece = self.grid[from_row][from_col]
        self.grid[to_row][to_col] = moving_piece
        self.grid[from_row][from_col] = EmptyCell()  # השארת אובייקט EmptyCell במקום המחרוזת הישנה
        self.selected_piece = None

    def __str__(self):
        return "\n".join(" ".join(str(cell) for cell in row) for row in self.grid)