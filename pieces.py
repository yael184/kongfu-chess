# pieces.py

class Piece:
    def __init__(self, color: str, symbol: str):
        self.color = color      # "WHITE", "BLACK" או None לתא ריק
        self.symbol = symbol    # "K", "R", "B", "Q", "N" או "." לתא ריק

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        raise NotImplementedError

    def __str__(self):
        if self.color is None:
            return self.symbol
        prefix = "w" if self.color == "WHITE" else "b"
        return f"{prefix}{self.symbol}"


# מחלקת ה-Null Object החדשה לתא ריק
class EmptyCell(Piece):
    def __init__(self):
        super().__init__(color=None, symbol=".")

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        # אי אפשר להזיז תא ריק
        return False

class King(Piece):
    def __init__(self, color: str):
        super().__init__(color, "K")

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        return max(abs(to_row - from_row), abs(to_col - from_col)) == 1


class Rook(Piece):
    def __init__(self, color: str):
        super().__init__(color, "R")

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        return from_row == to_row or from_col == to_col


class Bishop(Piece):
    def __init__(self, color: str):
        super().__init__(color, "B")

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        return abs(to_row - from_row) == abs(to_col - from_col)


class Queen(Piece):
    def __init__(self, color: str):
        super().__init__(color, "Q")

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        is_diagonal = abs(to_row - from_row) == abs(to_col - from_col)
        is_straight = (from_row == to_row or from_col == to_col)
        return is_diagonal or is_straight


class Knight(Piece):
    def __init__(self, color: str):
        super().__init__(color, "N")

    def is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        return (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2)