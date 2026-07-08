# engine.py
from board import Board

CELL_SIZE = 100

class GameEngine:
    def __init__(self, board: Board):
        self.board = board
        self.game_clock_ms = 0

    def execute_command(self, command_str: str):
        """מפענח ומריץ פקודה בודדת."""
        parts = command_str.strip().split()
        if not parts:
            return

        command_type = parts[0]

        if command_type == "click":
            if len(parts) == 3:
                self._handle_click(int(parts[1]), int(parts[2]))
        elif command_type == "wait":
            if len(parts) == 2:
                self._handle_wait(int(parts[1]))
        elif command_str.strip() == "print board":
            self._handle_print_board()
        else:
            print(f"ERROR: Unknown command '{command_str}'")

    def _handle_click(self, x: int, y: int):
        row = y // CELL_SIZE
        col = x // CELL_SIZE

        if not self.board.is_within_bounds(row, col):
            return

        # מקרה א': אין כלי נבחר כרגע
        if self.board.selected_piece is None:
            if not self.board.is_empty(row, col):
                self.board.select_piece(row, col)
            return

        # מקרה ב': יש כבר כלי נבחר
        sel_row, sel_col = self.board.selected_piece
        
        if self.board.is_empty(row, col):
            self.board.move_piece(sel_row, sel_col, row, col)
        else:
            current_color = self.board.get_piece_color(sel_row, sel_col)
            target_color = self.board.get_piece_color(row, col)
            
            if current_color == target_color:
                self.board.select_piece(row, col)
            else:
                self.board.move_piece(sel_row, sel_col, row, col)

    def _handle_wait(self, ms: int):
        self.game_clock_ms += ms

    def _handle_print_board(self):
        print(self.board)