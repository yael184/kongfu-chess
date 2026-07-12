# test_game.py
import pytest
from io import StringIO
from board import Board
from engine import GameEngine
from pieces import King, Rook, Bishop, Queen, Knight,EmptyCell
import main

# --- Fixtures ---
@pytest.fixture
def valid_grid():
    return [
        [King("WHITE"), EmptyCell(), King("BLACK")],
        [EmptyCell(), EmptyCell(), EmptyCell()],
        [EmptyCell(), King("WHITE"), EmptyCell()]
    ]

@pytest.fixture
def sample_board(valid_grid):
    return Board(valid_grid)

@pytest.fixture
def sample_engine(sample_board):
    return GameEngine(sample_board)


# --- Board tests ---
def test_board_bounds(sample_board):
    assert sample_board.is_within_bounds(0, 0) is True
    assert sample_board.is_within_bounds(-1, 0) is False

def test_board_get_cell(sample_board):
    assert str(sample_board.get_cell(0, 0)) == "wK"
    assert isinstance(sample_board.get_cell(0, 1), EmptyCell)

def test_board_is_empty(sample_board):
    assert sample_board.is_empty(0, 0) is False
    assert sample_board.is_empty(0, 1) is True

def test_board_get_piece_color(sample_board):
    assert sample_board.get_piece_color(0, 0) == "WHITE"
    assert sample_board.get_piece_color(0, 2) == "BLACK"
    assert sample_board.get_piece_color(0, 1) is None


# --- GameEngine tests ---
def test_engine_click_outside_bounds(sample_engine):
    sample_engine.execute_command("click 500 500")
    assert sample_engine.board.selected_piece is None

def test_engine_click_empty_no_selection(sample_engine):
    sample_engine.execute_command("click 150 50")
    assert sample_engine.board.selected_piece is None

def test_engine_select_and_move(sample_engine):
    sample_engine.execute_command("click 50 50")  # select wK at (0,0)
    assert sample_engine.board.selected_piece == (0, 0)
    sample_engine.execute_command("click 50 150") # legal move to (1,0)
    assert str(sample_engine.board.grid[1][0]) == "wK"
    assert sample_engine.board.selected_piece is None

def test_engine_switch_selection(sample_engine):
    sample_engine.execute_command("click 50 50")
    sample_engine.execute_command("click 150 250") # click the second wK at (2,1)
    assert sample_engine.board.selected_piece == (2, 1)

def test_engine_capture_piece(sample_engine):
    sample_engine.execute_command("click 50 50")   # select wK at (0,0)
    sample_engine.execute_command("click 250 50")  # capture bK at (0,2) - king legality (distance 2) was allowed here for the old test, or the king moves one step
    # Note: in the previous version the king moved from (0,0) to (0,2), which is 2 steps. The engine now blocks that!
    # To test a legal capture, move the piece to a legal destination that holds an enemy:

    # Place an enemy one step away at (0,1).
    sample_engine.board.grid[0][1] = King("BLACK")
    sample_engine.execute_command("click 50 50")   # select (0,0)
    sample_engine.execute_command("click 150 50")  # capture the enemy at (0,1)
    assert str(sample_engine.board.grid[0][1]) == "wK"

def test_engine_wait_and_print(sample_engine, capsys):
    sample_engine.execute_command("wait 500")
    assert sample_engine.game_clock_ms == 500
    sample_engine.execute_command("print board")
    captured = capsys.readouterr()
    assert "wK . bK" in captured.out

def test_engine_invalid_or_empty_command(sample_engine, capsys):
    sample_engine.execute_command("jump 10 20")
    captured = capsys.readouterr()
    assert "ERROR: Unknown command" in captured.out


# --- Parsing mechanism tests ---
def test_parse_input_valid():
    input_text = "Board:\nwK .\n. bK\nCommands:\nprint board"
    board, commands = main.parse_input(input_text)
    assert str(board.grid[0][0]) == "wK"
    assert isinstance(board.grid[0][1], EmptyCell)

def test_parse_input_row_width_mismatch():
    input_text = "Board:\nwK .\n. bK .\nCommands:\nprint board"
    with pytest.raises(SystemExit):
        main.parse_input(input_text)

def test_parse_input_unknown_token_in_board():
    input_text = "Board:\nwK wQ\n. bK\nCommands:\nprint board"
    # Since VALID_PIECES/PIECE_MAP was updated to include wQ, this test needs a piece that truly does not exist, e.g. wX.
    input_text = "Board:\nwK wX\n. bK\nCommands:\nprint board"
    with pytest.raises(SystemExit):
        main.parse_input(input_text)

def test_main_execution_flow(capsys):
    input_data = (
        "Board:\n"
        "wK . bK\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"
        "click 150 50\n"
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    captured = capsys.readouterr().out
    assert ". wK bK\n. . ." in captured

def test_main_execution_error_flow():
    fake_stream = StringIO("Just random text")

    # Verify the code fails in a controlled way on unsuitable input.
    with pytest.raises(SystemExit):
        main.main(input_stream=fake_stream)


# Direct unit tests for piece move legality (isolated unit tests)
def test_pieces_movement_logic():
    # A truly empty (6x6) board used for the rook/bishop path tests.
    empty_board = Board([[EmptyCell() for _ in range(6)] for _ in range(6)])

    king = King("WHITE")
    assert king.is_valid_move(0, 0, 1, 1, empty_board) is True   # one diagonal step
    assert king.is_valid_move(0, 0, 2, 0, empty_board) is False  # two steps (illegal)

    rook = Rook("WHITE")
    assert rook.is_valid_move(0, 0, 0, 5, empty_board) is True   # horizontal move
    assert rook.is_valid_move(0, 0, 3, 3, empty_board) is False  # diagonal (illegal)

    bishop = Bishop("BLACK")
    assert bishop.is_valid_move(2, 2, 5, 5, empty_board) is True  # perfect diagonal
    assert bishop.is_valid_move(2, 2, 2, 4, empty_board) is False # straight (illegal)

    knight = Knight("WHITE")
    assert knight.is_valid_move(0, 0, 2, 1, empty_board) is True  # L shape
    assert knight.is_valid_move(0, 0, 2, 2, empty_board) is False # not an L


# Integration tests through main and the game board via dependency injection

def test_king_legal_and_illegal_commands(capsys):
    input_data = (
        "Board:\n"
        "wK . .\n"
        ". . .\n"
        "Commands:\n"
        "click 50 50\n"   # select the king at (0,0)
        "click 250 50\n"  # illegal move (distance 2) - ignored
        "print board\n"
        "click 50 50\n"   # reselect
        "click 150 150\n" # legal move (diagonal 1)
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    captured = capsys.readouterr().out
    assert "wK . .\n. . ." in captured
    assert ". . .\n. wK ." in captured


def test_rook_and_bishop_integration(capsys):
    input_data = (
        "Board:\n"
        "wR . .\n"
        ". bB .\n"
        ". . .\n"  # Added a third row (index 2) so the board is 3x3.
        "Commands:\n"
        "click 50 50\n"   # select the rook at (0,0)
        "click 50 250\n"  # move the rook to (2,0) - legal straight line
        "click 150 150\n" # select the bishop at (1,1)
        "click 250 250\n" # move the bishop to (2,2) - legal diagonal
        "print board\n"
    )
    main.main(input_stream=StringIO(input_data))
    captured = capsys.readouterr().out



    expected_output = (
        ". . .\n"
        ". . .\n"
        "wR . bB"
    )
    assert expected_output in captured


def test_empty_cell_behavior():
    empty_board = Board([[EmptyCell() for _ in range(3)] for _ in range(3)])
    empty = EmptyCell()
    assert str(empty) == "."
    assert empty.color is None
    assert empty.is_valid_move(0, 0, 1, 1, empty_board) is False
