# board.py

class Board:
    def __init__(self, grid):
        self.grid = grid
        self.selected_piece = None  # יישמר כ-tuple: (row, col)

    def is_within_bounds(self, row, col):
        return 0 <= row < len(self.grid) and 0 <= col < len(self.grid[0])

    def get_cell(self, row, col):
        if self.is_within_bounds(row, col):
            return self.grid[row][col]
        return None

    def is_empty(self, row, col):
        cell = self.get_cell(row, col)
        return cell == "." or cell is None

    def get_piece_color(self, row, col):
        """מחזירה את צבע הכלי לפי האות הראשונה (w או b)."""
        cell = self.get_cell(row, col)
        if not cell or cell == ".":
            return None
        
        if cell.startswith("w"):
            return "WHITE"
        elif cell.startswith("b"):
            return "BLACK"
        return None

    def select_piece(self, row, col):
        self.selected_piece = (row, col)

    def move_piece(self, from_row, from_col, to_row, to_col):
        """מבצעת תנועה חלקה (או אכילה) בתוך המטריצה."""
        moving_piece = self.grid[from_row][from_col]
        self.grid[to_row][to_col] = moving_piece
        self.grid[from_row][from_col] = "."
        self.selected_piece = None

    def __str__(self):
        return "\n".join(" ".join(row) for row in self.grid)