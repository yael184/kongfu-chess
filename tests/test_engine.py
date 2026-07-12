# tests/test_engine.py
# Tests for the GameEngine class and command parsing.
from board import Board
from engine import GameEngine
from pieces import King


# --- command routing (execute_command) ---
def test_empty_command_is_noop(sample_engine):
    # An empty / whitespace-only string should not raise or change state.
    sample_engine.execute_command("   ")
    assert sample_engine.board.selected_piece is None


def test_unknown_command_prints_error(sample_engine, capsys):
    sample_engine.execute_command("teleport 10 20")
    assert "ERROR: Unknown command" in capsys.readouterr().out


def test_click_wrong_arg_count_is_unknown(sample_engine, capsys):
    # click with the wrong number of arguments falls through to else (unknown command).
    sample_engine.execute_command("click 50")
    assert "ERROR: Unknown command" in capsys.readouterr().out


# --- clicks (_handle_click) ---
def test_click_outside_bounds_does_nothing(sample_engine):
    sample_engine.execute_command("click 500 500")
    assert sample_engine.board.selected_piece is None


def test_click_empty_cell_no_selection(sample_engine):
    sample_engine.execute_command("click 150 50")  # (0,1) is empty
    assert sample_engine.board.selected_piece is None


def test_click_selects_piece(sample_engine):
    sample_engine.execute_command("click 50 50")  # (0,0) = wK
    assert sample_engine.board.selected_piece == (0, 0)


def test_select_and_legal_move(sample_engine):
    sample_engine.execute_command("click 50 50")   # select (0,0)
    sample_engine.execute_command("click 50 150")  # legal move to (1,0)
    sample_engine.execute_command("wait 1000")     # wait until the move arrives (one cell)
    assert str(sample_engine.board.grid[1][0]) == "wK"
    assert sample_engine.board.selected_piece is None


def test_switch_selection_same_color(sample_engine):
    sample_engine.execute_command("click 50 50")    # select (0,0) wK
    sample_engine.execute_command("click 150 250")  # (2,1) wK - switch selection
    assert sample_engine.board.selected_piece == (2, 1)


def test_illegal_move_deselects(sample_engine):
    sample_engine.execute_command("click 50 50")    # select (0,0)
    sample_engine.execute_command("click 250 150")  # far/illegal destination for a king
    # No move was made, and the selection was cleared.
    assert str(sample_engine.board.grid[0][0]) == "wK"
    assert sample_engine.board.selected_piece is None


def test_capture_enemy_piece(sample_engine):
    # Place an enemy one step away and capture it.
    sample_engine.board.grid[0][1] = King("BLACK")
    sample_engine.execute_command("click 50 50")   # select (0,0)
    sample_engine.execute_command("click 150 50")  # capture (0,1)
    sample_engine.execute_command("wait 1000")     # wait until the move arrives (one cell)
    assert str(sample_engine.board.grid[0][1]) == "wK"
    assert sample_engine.board.selected_piece is None


# --- wait ---
def test_wait_accumulates_clock(sample_engine):
    sample_engine.execute_command("wait 500")
    assert sample_engine.game_clock_ms == 500
    sample_engine.execute_command("wait 250")
    assert sample_engine.game_clock_ms == 750


# --- movement over time ---
def test_move_stays_at_origin_before_any_wait(sample_engine):
    # Right after launching the move, before the clock advances, the piece is still at the origin and the destination is empty.
    sample_engine.execute_command("click 50 50")   # select (0,0)
    sample_engine.execute_command("click 50 150")  # destination (1,0), arrival 1000
    assert str(sample_engine.board.grid[0][0]) == "wK"
    assert sample_engine.board.is_empty(1, 0)
    assert len(sample_engine.pending_moves) == 1


def test_move_still_in_flight_after_partial_wait(sample_engine):
    # A wait shorter than the arrival time does not complete the move.
    sample_engine.execute_command("click 50 50")
    sample_engine.execute_command("click 50 150")
    sample_engine.execute_command("wait 500")      # less than 1000
    assert str(sample_engine.board.grid[0][0]) == "wK"
    assert sample_engine.board.is_empty(1, 0)


def test_move_completes_after_enough_wait(sample_engine):
    # Once the clock reaches the arrival time, the piece actually moves to the destination and the origin is emptied.
    sample_engine.execute_command("click 50 50")
    sample_engine.execute_command("click 50 150")
    sample_engine.execute_command("wait 1000")     # exactly the arrival time
    assert sample_engine.board.is_empty(0, 0)
    assert str(sample_engine.board.grid[1][0]) == "wK"
    assert sample_engine.pending_moves == []


def test_longer_move_takes_proportionally_more_time(make_board):
    # Arrival time grows with route length: a two-cell move takes 2000ms.
    board = make_board([
        ["wR", ".", "."],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("click 50 50")    # select the rook (0,0)
    engine.execute_command("click 50 250")   # destination (2,0), distance 2 -> 2000ms
    engine.execute_command("wait 1000")      # only halfway
    assert str(engine.board.grid[0][0]) == "wR"
    engine.execute_command("wait 1000")      # 2000 total -> arrived
    assert str(engine.board.grid[2][0]) == "wR"
    assert engine.board.is_empty(0, 0)


# --- redirection during travel + absence of cooldown ---
def test_moving_piece_cannot_be_redirected(make_board):
    # A piece that has set off cannot be redirected until it reaches its original destination.
    board = make_board([
        ["wR", ".", "."],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("click 50 50")    # select the rook (0,0)
    engine.execute_command("click 50 250")   # launch a move to (2,0) [in transit]
    # Attempt to redirect while the piece is still traveling:
    engine.execute_command("click 50 50")    # reselect the moving piece
    engine.execute_command("click 150 50")   # attempt to redirect to (0,1) - should be blocked
    assert len(engine.pending_moves) == 1    # only the original move remains
    engine.execute_command("wait 2000")
    assert str(engine.board.grid[2][0]) == "wR"  # reached the original destination
    assert engine.board.is_empty(0, 1)           # was not redirected elsewhere


def test_board_is_locked_while_a_move_is_pending(make_board):
    # While a move is in progress, clicks on the board are ignored (no concurrent movement).
    board = make_board([
        ["wR", ".", "."],
        [".", ".", "."],
        ["bR", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("click 50 50")    # select the white rook (0,0)
    engine.execute_command("click 250 50")   # launch a move to (0,2) - the board locks
    engine.execute_command("click 50 250")   # attempt to select the black rook - ignored
    assert engine.board.selected_piece is None
    engine.execute_command("click 250 250")  # attempt to move it - ignored
    assert len(engine.pending_moves) == 1     # only the white move exists
    engine.execute_command("wait 2000")
    assert str(engine.board.grid[0][2]) == "wR"   # white reached its destination
    assert str(engine.board.grid[2][0]) == "bR"   # black did not move at all


def test_piece_can_move_again_immediately_after_arrival(make_board):
    # No cooldown: a new move can start the moment the piece arrives.
    board = make_board([
        ["wR", ".", "."],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("click 50 50")    # (0,0)
    engine.execute_command("click 50 250")   # -> (2,0)
    engine.execute_command("wait 2000")      # arrival at destination
    assert str(engine.board.grid[2][0]) == "wR"
    # Right after arrival, with no cooldown delay, launch another move:
    engine.execute_command("click 50 250")   # select the piece at (2,0)
    engine.execute_command("click 250 250")  # move to (2,2)
    assert len(engine.pending_moves) == 1    # the new move is accepted immediately
    engine.execute_command("wait 2000")
    assert str(engine.board.grid[2][2]) == "wR"


# --- game over (capturing a king) ---
def test_capturing_enemy_king_ends_game(make_board):
    # When a piece reaches a cell holding an enemy king, the game ends.
    board = make_board([
        ["wR", ".", "bK"],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("click 50 50")     # select the white rook (0,0)
    engine.execute_command("click 250 50")    # move toward the black king at (0,2)
    assert engine.game_over is False          # still traveling - not decided yet
    engine.execute_command("wait 2000")       # arrival performs the capture
    assert engine.game_over is True
    assert str(engine.board.grid[0][2]) == "wR"   # the rook took the king's cell


def test_moves_are_ignored_after_game_over(make_board):
    # After the game ends, further move commands are ignored and the board does not change.
    board = make_board([
        ["wR", ".", "bK"],
        [".", "bR", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("click 50 50")     # select the white rook
    engine.execute_command("click 250 50")    # move toward the king (0,2)
    engine.execute_command("wait 2000")       # king captured -> game over
    assert engine.game_over is True

    # Attempt to move the black rook after the game ended - should be ignored:
    engine.execute_command("click 150 150")   # select bR at (1,1)
    assert engine.board.selected_piece is None
    engine.execute_command("click 50 150")    # attempt a move to (1,0)
    assert engine.pending_moves == []
    engine.execute_command("wait 2000")
    assert str(engine.board.grid[1][1]) == "bR"   # the black rook did not move


# --- advanced pawn rules (two-cell move + promotion) ---
def test_pawn_two_square_move_resolves_over_time(make_board):
    # 6x6 board: a white pawn on its start row (5) moves two cells to (3,1).
    grid = [["." for _ in range(6)] for _ in range(6)]
    grid[5][1] = "wP"
    engine = GameEngine(make_board(grid))
    engine.execute_command("click 150 550")   # select the pawn (row 5, col 1)
    engine.execute_command("click 150 350")   # destination (row 3, col 1), distance 2 -> 2000ms
    engine.execute_command("wait 2000")
    assert str(engine.board.grid[3][1]) == "wP"
    assert engine.board.is_empty(5, 1)


def test_pawn_promotes_to_queen_on_last_row(make_board):
    # White pawn one step before the last row; on reaching row 0 it becomes a queen.
    grid = [["." for _ in range(6)] for _ in range(6)]
    grid[1][3] = "wP"
    engine = GameEngine(make_board(grid))
    engine.execute_command("click 350 150")   # select the pawn (row 1, col 3)
    engine.execute_command("click 350 50")    # destination row 0 (row 0, col 3)
    engine.execute_command("wait 1000")
    assert str(engine.board.grid[0][3]) == "wQ"   # promoted to a queen
    assert engine.board.is_empty(1, 3)


# --- jump in place (Dodge / Jump) ---
def test_jumper_eats_attacker_that_arrives_during_jump(make_board):
    # An adjacent attacker arrives exactly during the jump (arrival == land) -> the jumper eats it.
    board = make_board([
        ["wP", "bR", "."],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("jump 50 50")     # white pawn (0,0) jumps, lands at 1000
    engine.execute_command("click 150 50")   # select the black rook (0,1)
    engine.execute_command("click 50 50")    # attack toward (0,0), distance 1 -> arrival 1000
    engine.execute_command("wait 1000")
    assert str(engine.board.grid[0][0]) == "wP"   # the jumper survived and stayed put
    assert engine.board.is_empty(0, 1)            # the arriving attacker was removed
    assert engine.pending_moves == []


def test_attacker_eats_jumper_that_already_landed(make_board):
    # The attacker is far and arrives (2000) after the jumper landed (1000) -> the attacker eats the jumper.
    board = make_board([
        ["wP", ".", "bR"],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("jump 50 50")     # (0,0) jumps, lands at 1000
    engine.execute_command("click 250 50")   # select the black rook (0,2)
    engine.execute_command("click 50 50")    # attack toward (0,0), distance 2 -> arrival 2000
    engine.execute_command("wait 2000")
    assert str(engine.board.grid[0][0]) == "bR"   # the attacker captured and took the cell
    assert engine.board.is_empty(0, 2)


def test_moving_piece_cannot_jump(make_board):
    board = make_board([
        ["wR", ".", "."],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("click 50 50")    # select the rook
    engine.execute_command("click 50 250")   # move to (2,0) - the rook is in transit
    engine.execute_command("jump 50 50")     # attempt to jump while moving - rejected
    assert (0, 0) not in engine.airborne


def test_empty_cell_cannot_jump(make_board):
    board = make_board([
        ["wP", ".", "."],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("jump 150 50")    # (0,1) is empty - no piece to jump
    assert engine.airborne == {}


def test_jump_lands_normally_when_no_attacker(make_board):
    # No attacker: the jumper simply lands in place and the 'air' clears after the jump window.
    board = make_board([
        ["wP", ".", "."],
        [".", ".", "."],
        [".", ".", "."],
    ])
    engine = GameEngine(board)
    engine.execute_command("jump 50 50")
    engine.execute_command("wait 2000")      # the jump window (1000) has passed
    assert str(engine.board.grid[0][0]) == "wP"   # did not move
    assert engine.airborne == {}


# --- print board ---
def test_print_board(sample_engine, capsys):
    sample_engine.execute_command("print board")
    out = capsys.readouterr().out
    assert "wK . bK" in out
