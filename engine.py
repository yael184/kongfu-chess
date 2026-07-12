# engine.py
from board import Board
from pieces import Piece, King
import config


class PendingMove:
    """A move that is underway and still 'in flight'. The piece stays in its origin cell until arrival_ms."""
    def __init__(self, from_row, from_col, to_row, to_col, arrival_ms):
        self.from_row = from_row
        self.from_col = from_col
        self.to_row = to_row
        self.to_col = to_col
        self.arrival_ms = arrival_ms


class GameEngine:
    """Dispatches commands and mutates the board: click/jump/wait/print board."""

    def __init__(self, board: Board):
        self.board = board
        self.game_clock_ms = 0
        self.pending_moves = []  # Moves in transit, waiting for their arrival time.
        self.airborne = {}       # (row, col) -> land_ms: pieces jumping in place, protected until they land.
        self.game_over = False   # Set once a king is captured; from then on moves are ignored.

    def execute_command(self, command_str: str):
        """Parse a single command string and route it to the matching handler."""
        parts = command_str.strip().split()
        if not parts:
            return

        command_type = parts[0]

        if command_type == "click" and len(parts) == 3:
            self._handle_click(int(parts[1]), int(parts[2]))
        elif command_type == "jump" and len(parts) == 3:
            self._handle_jump(int(parts[1]), int(parts[2]))
        elif command_type == "wait" and len(parts) == 2:
            self._handle_wait(int(parts[1]))
        elif command_str.strip() == "print board":
            self._handle_print_board()
        else:
            print(f"ERROR: Unknown command '{command_str}'")

    def _handle_click(self, x: int, y: int):
        """Select a piece, launch a move/capture, or clear the selection based on the clicked cell."""
        # Game over (a king was captured): every move command is ignored from here on.
        if self.game_over:
            return

        # Input lock during travel: while a move is in progress the board is locked and clicks
        # are ignored. This means two pieces never move concurrently (including opposite colors),
        # and an in-flight piece cannot be redirected. The lock lifts when the move arrives.
        if self.pending_moves:
            return

        row = y // config.CELL_SIZE
        col = x // config.CELL_SIZE

        if not self.board.is_within_bounds(row, col):
            return

        # Case A: nothing is currently selected.
        if self.board.selected_piece is None:
            if not self.board.is_empty(row, col):
                self.board.select_piece(row, col)
            return

        # Case B: a piece is selected; evaluate the destination.
        sel_row, sel_col = self.board.selected_piece

        # 1. Color check: clicking another piece of the same color switches the selection.
        current_color = self.board.get_piece_color(sel_row, sel_col)
        target_color = self.board.get_piece_color(row, col)

        if current_color is not None and current_color == target_color:
            self.board.select_piece(row, col)
            return

        # 2. Legality check (including blockers along the route).
        moving_piece = self.board.get_cell(sel_row, sel_col)
        if isinstance(moving_piece, Piece):
            if not moving_piece.is_valid_move(sel_row, sel_col, row, col, self.board):
                self.board.selected_piece = None
                return

        # 3. Launch: the move is not instant but takes physical time proportional to the route
        #    length. The piece stays in its origin cell and only moves on arrival (as the clock
        #    advances). From now on the board is locked (see the check at the top) until it arrives.
        arrival_ms = self.game_clock_ms + self._travel_time(sel_row, sel_col, row, col)
        self.pending_moves.append(PendingMove(sel_row, sel_col, row, col, arrival_ms))
        self.board.selected_piece = None

    def _handle_jump(self, x: int, y: int):
        """Make the piece on the given cell jump in place, protected until JUMP_DURATION_MS elapses.

        A jump is not subject to the move board-lock, so it can happen while an enemy is in flight.
        """
        if self.game_over:
            return

        row = y // config.CELL_SIZE
        col = x // config.CELL_SIZE

        if not self.board.is_within_bounds(row, col):
            return
        if self.board.is_empty(row, col):
            return                                   # No piece to jump (a captured piece cannot jump either).
        if self._is_in_flight(row, col):
            return                                   # A piece in transit cannot jump.
        if (row, col) in self.airborne:
            return                                   # Already airborne.

        self.airborne[(row, col)] = self.game_clock_ms + config.JUMP_DURATION_MS

    def _is_in_flight(self, row, col) -> bool:
        """Whether a pending move originates from this cell (i.e. the piece is in transit)."""
        return any(m.from_row == row and m.from_col == col for m in self.pending_moves)

    def _travel_time(self, from_row, from_col, to_row, to_col) -> int:
        """Arrival time derived from the route length (Chebyshev distance) times MS_PER_CELL."""
        cells = max(abs(to_row - from_row), abs(to_col - from_col))
        return cells * config.MS_PER_CELL

    def _resolve_arrived_moves(self):
        """Apply every move whose arrival time has already passed on the current clock."""
        still_pending = []
        for move in self.pending_moves:
            if move.arrival_ms <= self.game_clock_ms:
                self._resolve_move(move)
            else:
                still_pending.append(move)
        self.pending_moves = still_pending

    def _resolve_move(self, move):
        """Apply a single arrived move, handling the jump collision case before a normal capture."""
        # Jump collision: if an enemy piece at the destination is still airborne on arrival
        # (arrival_ms <= its land time), the jumper "lands on" the arriving piece and eats it:
        # the jumper stays put and the arriving attacker is removed from the board.
        land_ms = self.airborne.get((move.to_row, move.to_col))
        arriving_color = self.board.get_piece_color(move.from_row, move.from_col)
        defender_color = self.board.get_piece_color(move.to_row, move.to_col)
        if (land_ms is not None and move.arrival_ms <= land_ms
                and defender_color is not None and arriving_color is not None
                and defender_color != arriving_color):
            arriving = self.board.get_cell(move.from_row, move.from_col)
            self.board.clear_cell(move.from_row, move.from_col)
            if isinstance(arriving, King):
                self.game_over = True
            return

        # Normal resolution (including when the jumper had already landed before the attacker arrived):
        # read the destination before overwriting it - if a king sat there, the game is decided.
        captured = self.board.get_cell(move.to_row, move.to_col)
        self.board.move_piece(move.from_row, move.from_col,
                              move.to_row, move.to_col)
        self._apply_promotion(move.to_row, move.to_col)
        if isinstance(captured, King):
            self.game_over = True

    def _expire_airborne(self):
        """Drop pieces that have already landed (their land time has passed) from the airborne set."""
        self.airborne = {cell: land for cell, land in self.airborne.items()
                         if land >= self.game_clock_ms}

    def _apply_promotion(self, row, col):
        """Replace an arrived piece with its promoted form (pawn -> queen), if any."""
        piece = self.board.get_cell(row, col)
        promoted = piece.promoted_piece(row, self.board)
        if promoted is not None:
            self.board.set_cell(row, col, promoted)

    def _handle_wait(self, ms: int):
        """Advance the clock, resolve any moves that have arrived, then expire landed jumps."""
        self.game_clock_ms += ms
        self._resolve_arrived_moves()
        self._expire_airborne()

    def _handle_print_board(self):
        """Print the current board state."""
        print(self.board)
