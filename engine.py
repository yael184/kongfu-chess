# engine.py
from board import Board
from pieces import Piece

CELL_SIZE = 100

class GameEngine:
    def __init__(self, board: Board):
        self.board = board
        self.game_clock_ms = 0

    def execute_command(self, command_str: str):
        parts = command_str.strip().split()
        if not parts:
            return

        command_type = parts[0]

        if command_type == "click" and len(parts) == 3:
            self._handle_click(int(parts[1]), int(parts[2]))
        elif command_type == "wait" and len(parts) == 2:
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

        if self.board.selected_piece is None:
            if not self.board.is_empty(row, col):
                self.board.select_piece(row, col)
            return

        sel_row, sel_col = self.board.selected_piece
        
        current_color = self.board.get_piece_color(sel_row, sel_col)
        target_color = self.board.get_piece_color(row, col)
        
        if current_color is not None and current_color == target_color:
            self.board.select_piece(row, col)
            return

        moving_piece = self.board.get_cell(sel_row, sel_col)
        if isinstance(moving_piece, Piece):
            if not moving_piece.is_valid_move(sel_row, sel_col, row, col):
                self.board.selected_piece = None
                return

        self.board.move_piece(sel_row, sel_col, row, col)


    def _handle_wait(self, ms: int):
        self.game_clock_ms += ms

    def _handle_print_board(self):
        print(self.board)