# test_game.py
import pytest
from io import StringIO
from board import Board
from engine import GameEngine
import main

# --- פיקסטורות (Fixtures) ---
@pytest.fixture
def valid_grid():
    return [
        ["wK", ".", "bK"],
        [".", ".", "."],
        [".", "wK", "."]
    ]

@pytest.fixture
def sample_board(valid_grid):
    return Board(valid_grid)

@pytest.fixture
def sample_engine(sample_board):
    return GameEngine(sample_board)


# --- בדיקות Board ---
def test_board_bounds(sample_board):
    assert sample_board.is_within_bounds(0, 0) is True
    assert sample_board.is_within_bounds(-1, 0) is False

def test_board_get_cell(sample_board):
    assert sample_board.get_cell(0, 0) == "wK"
    assert sample_board.get_cell(5, 5) is None

def test_board_is_empty(sample_board):
    assert sample_board.is_empty(0, 0) is False
    assert sample_board.is_empty(0, 1) is True

def test_board_get_piece_color(sample_board):
    assert sample_board.get_piece_color(0, 0) == "WHITE"
    assert sample_board.get_piece_color(0, 2) == "BLACK"
    assert sample_board.get_piece_color(0, 1) is None


# --- בדיקות GameEngine ---
def test_engine_click_outside_bounds(sample_engine):
    sample_engine.execute_command("click 500 500")
    assert sample_engine.board.selected_piece is None

def test_engine_click_empty_no_selection(sample_engine):
    sample_engine.execute_command("click 150 50")
    assert sample_engine.board.selected_piece is None

def test_engine_select_and_move(sample_engine):
    sample_engine.execute_command("click 50 50")
    assert sample_engine.board.selected_piece == (0, 0)
    sample_engine.execute_command("click 50 150")
    assert sample_engine.board.grid[1][0] == "wK"
    assert sample_engine.board.selected_piece is None

def test_engine_switch_selection(sample_engine):
    sample_engine.execute_command("click 50 50")
    sample_engine.execute_command("click 150 250")
    assert sample_engine.board.selected_piece == (2, 1)

def test_engine_capture_piece(sample_engine):
    sample_engine.execute_command("click 50 50")
    sample_engine.execute_command("click 250 50")
    assert sample_engine.board.grid[0][2] == "wK"

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


# --- בדיקות מנגנון ה-Parsing ---
def test_parse_input_valid():
    input_text = "Board:\nwK .\n. bK\nCommands:\nprint board"
    board, commands = main.parse_input(input_text)
    assert board.grid == [["wK", "."], [".", "bK"]]

def test_parse_input_row_width_mismatch():
    input_text = "Board:\nwK .\n. bK .\nCommands:\nprint board"
    with pytest.raises(SystemExit):
        main.parse_input(input_text)

def test_parse_input_unknown_token_in_board():
    input_text = "Board:\nwK wQ\n. bK\nCommands:\nprint board"
    with pytest.raises(SystemExit):
        main.parse_input(input_text)


# --- בדיקות אינטגרציה מלאות עם הזרקת תלויות (בלי Monkeypatch!) ---

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
    # יצירת הזרם הווירטואלי מתוך הטקסט
    fake_stream = StringIO(input_data)
    
    # הזרקה ישירה לפונקציה בצורה נקייה והרמונית
    main.main(input_stream=fake_stream)
    
    captured = capsys.readouterr()
    expected_output = ". wK bK\n. . ."
    assert expected_output in captured.out

def test_main_execution_error_flow():
    fake_stream = StringIO("Just random text")
    
    # וידוא שהקוד קורס בצורה מבוקרת עם קלט לא מתאים
    with pytest.raises(SystemExit):
        main.main(input_stream=fake_stream)